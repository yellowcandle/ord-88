#!/usr/bin/env python3
"""Hybrid categoriser: keyword pre-filter + qwen/qwen3.7-plus (via OpenRouter) tie-break.

Confident single-keyword-match names are kept as-is. The 0-match ("Other") and
2+-match (ambiguous) names are sent to qwen/qwen3.7-plus in concurrent batches.
Per batch: validate the JSON array length == batch size; retry with backoff; count
rows that still fall back to a keyword guess and exit non-zero so a partial run is
visible instead of looking complete.

Usage:  classify_or.py [LIMIT]   # LIMIT optional: only process first N ambiguous (for testing)
"""
import concurrent.futures as cf
import csv
import hashlib
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter

from provenance import write_meta
from taxonomy import CATEGORY_KEYWORDS, CATEGORY_LABELS, MAIN_CODES

SRC = "s88list.csv"
MODEL = "qwen/qwen3.7-plus"
BATCH = 15
WORKERS = 16
URL = "https://openrouter.ai/api/v1/chat/completions"
RETRY_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}

CATS = [(code, CATEGORY_LABELS[code], keywords) for code, keywords in CATEGORY_KEYWORDS]
CODES = MAIN_CODES
LABEL = CATEGORY_LABELS

PROMPT_HDR = ("You are an expert classifier of Hong Kong charities. For each numbered name output "
 "exactly ONE category code. Output ONLY a JSON array of EXACTLY {N} uppercase code strings in order, no prose.\n"
 "Codes: REL=religious/temple/church EDU=education/school MED=medical/health/hospital "
 "ELD=elderly/nursing-home DIS=disability/rehab YTH=youth/children WOM=women ART=arts/culture/music/opera "
 "SPT=sports/recreation ENV=animals/environment CLN=clan/native-place-association COM=community/kaifong/residents "
 "BIZ=professional/trade/business WEL=social-welfare/charity-services FND=foundation/grant-making-fund "
 "ASN=generic-club/association OTH=other.\nNames:\n")
PROMPT_VERSION = hashlib.sha256(PROMPT_HDR.encode()).hexdigest()[:12]

KEY = os.environ.get("OPENROUTER_API_KEY")


def api_key() -> str:
    """Prefer the environment, then the local agent credential store."""
    global KEY
    if KEY:
        return KEY
    try:
        auth = json.loads((pathlib.Path.home() / ".pi/agent/auth.json").read_text(encoding="utf-8"))
        KEY = auth["openrouter"]["key"]
    except (OSError, KeyError, ValueError):
        raise SystemExit("set OPENROUTER_API_KEY (or configure ~/.pi/agent/auth.json)") from None
    return KEY


def matches(text):
    return [code for code, _, kws in CATS if any(kw and kw in text for kw in kws)]


def _request(body):
    req = urllib.request.Request(URL, data=body, headers={
        "Authorization": f"Bearer {api_key()}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.load(r)
        return data["choices"][0]["message"].get("content") or ""
    except urllib.error.HTTPError:
        raise
    except (OSError, ValueError, KeyError, IndexError) as error:
        raise RuntimeError(f"unusable OpenRouter reply: {error}") from None


def _parse(txt, n):
    if not txt:
        return None
    match = re.search(r"\[.*\]", txt, re.S)
    if not match:
        return None
    try:
        arr = json.loads(match.group(0))
    except ValueError:
        return None
    if not isinstance(arr, list) or len(arr) != n:
        return None
    codes = [str(value).upper().strip() for value in arr]
    return [code if code in CODES else "OTH" for code in codes]


def call(names, attempts=4):
    """Return a validated list of codes, or None after bounded retries."""
    body = json.dumps({"model": MODEL, "temperature": 0,
        "messages": [{"role": "user", "content": PROMPT_HDR.replace("{N}", str(len(names))) +
            "\n".join(f"{i+1}. {n}" for i, n in enumerate(names)) + "\nJSON:"}]}).encode()
    for attempt in range(attempts):
        try:
            txt = _request(body)
        except urllib.error.HTTPError as error:
            if error.code not in RETRY_STATUS:
                return None
            txt = None
        except Exception:
            txt = None
        codes = _parse(txt, len(names))
        if codes is not None:
            return codes
        if attempt < attempts - 1:
            time.sleep(1.5 * (2 ** attempt))
    return None


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) > 1 or (args and not args[0].isdigit()):
        raise SystemExit("usage: classify_or.py [LIMIT]")
    limit = int(args[0]) if args else None
    try:
        with open(SRC, encoding="utf-8-sig", newline="") as f:
            data = [r for r in list(csv.reader(f))[1:] if any(c.strip() for c in r)]
    except OSError as error:
        raise SystemExit(f"cannot read {SRC}: {error}") from None
    final: list[str | None] = [None] * len(data)
    ambiguous = []
    for idx, row in enumerate(data):
        hits = matches(" ".join(row[1:6]).lower())
        if len(hits) == 1:
            final[idx] = hits[0]
        else:
            ambiguous.append((idx, (row[2] or row[1]).strip(), hits[0] if hits else "OTH"))
    if limit:
        ambiguous = ambiguous[:limit]
    print(f"confident={sum(x is not None for x in final)} ambiguous_to_LLM={len(ambiguous)}", flush=True)

    batches = [ambiguous[i:i + BATCH] for i in range(0, len(ambiguous), BATCH)]
    done = 0
    failed_rows = 0
    with cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = {ex.submit(call, [name for _, name, _ in batch]): batch for batch in batches}
        for future in cf.as_completed(futures):
            batch = futures[future]
            try:
                codes = future.result()
            except Exception:
                codes = None
            if codes is None:
                failed_rows += len(batch)
                for idx, _, fallback in batch:
                    final[idx] = fallback
            else:
                for (idx, _, _), code in zip(batch, codes, strict=True):
                    final[idx] = code
            done += 1
            if done % 10 == 0 or done == len(batches):
                print(f"  batches {done}/{len(batches)} ({failed_rows} rows fell back)", flush=True)

    if limit:                              # test mode: just print sample, don't overwrite full output
        for idx, name, fallback in ambiguous[:20]:
            print(f"  {final[idx]:<4} {name[:30]}  (kw_fallback={fallback})")
        return 0
    try:
        with open("s88list_categorised.csv", "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["code", "category", "english_name", "chinese_name", "effective_date"])
            for idx, row in enumerate(data):
                code = final[idx] or "OTH"
                writer.writerow([code, LABEL[code], row[1], row[2], row[6]])
    except OSError as error:
        raise SystemExit(f"cannot write s88list_categorised.csv: {error}") from None
    counts = Counter(final[idx] or "OTH" for idx in range(len(data)))
    try:
        with open("category_counts.json", "w", encoding="utf-8") as f:
            json.dump({"total": len(data), "counts": dict(counts), "labels": LABEL}, f,
                      ensure_ascii=False, indent=2)
    except OSError as error:
        raise SystemExit(f"cannot write category_counts.json: {error}") from None
    write_meta(model=MODEL, prompt_version=PROMPT_VERSION, fallback_rows=failed_rows,
               updated_by=["classify_or.py"], stage="main", source_changed=True)
    print("DONE", dict(counts), flush=True)
    if failed_rows:
        print(f"WARNING: {failed_rows} rows fell back to keyword guesses; re-run before shipping",
              file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
