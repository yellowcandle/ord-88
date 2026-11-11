#!/usr/bin/env python3
"""Second-pass + sub-classification using qwen/qwen3.7-plus via OpenRouter.

Modes:
  rescue     -- re-examine code==OTH names; assign best main category, OTH only if truly generic.
  religion   -- sub-classify code==REL names into religion/denomination.
  community  -- sub-classify code==COM names by inferred socio-political character.

Reads s88list_categorised.csv; writes sub_<mode>.csv, one row per matching input row
in input order. Transient HTTP failures and malformed replies are retried with
backoff. Rows that still fail are written with the fallback label to preserve the
positional contract, listed in sub_<mode>.failures.csv, reported, and make the run
exit non-zero.

Run this again whenever s88list_categorised.csv is regenerated. Pass ``--since REF``
to reuse the labels recorded at git revision REF and classify only rows that are new
since then; this keeps a rescue merge cheap and leaves existing labels untouched.
"""
import concurrent.futures as cf
import csv
import hashlib
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import Counter

from provenance import check_source, write_meta
from taxonomy import COMMUNITY_CODES, MAIN_CODES, RELIGION_CODES

MODEL = "qwen/qwen3.7-plus"
BATCH = 15
WORKERS = 16
URL = "https://openrouter.ai/api/v1/chat/completions"
RETRY_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}

PROMPTS = {
    "rescue": ("Each name is a Hong Kong tax-exempt charity that a first pass could not categorise. "
      "Assign the single best main category code; use OTH ONLY if the name is a generic company/holding "
      "name with no charitable hint at all. Output ONLY a JSON array of EXACTLY {N} uppercase codes in order.\n"
      "Codes: REL EDU MED ELD DIS YTH WOM ART SPT ENV CLN COM BIZ WEL FND ASN OTH.\nNames:\n",
      set(MAIN_CODES)),

    "religion": ("Each name is a Hong Kong religious charity. For each, output 'RELIGION/denomination'. "
      "RELIGION codes: BUD=Buddhism TAO=Taoism FOLK=Chinese-folk-religion(temples to folk deities, 盂蘭勝會, "
      "天后/觀音/關帝/譚公/洪聖/黃大仙 territorial cults, ancestral) PROT=Protestant-Christian CATH=Roman-Catholic "
      "CHRX=other-Christian(Orthodox, Mormon/LDS, Jehovah's-Witnesses, non-denominational) ISL=Islam "
      "CONF=Confucianism HIN=Hindu SIK=Sikh JEW=Jewish BAHAI=Bahai OTH=unclear. "
      "For PROT give a denomination from: Baptist Lutheran Methodist Anglican Pentecostal Alliance Evangelical "
      "Adventist Presbyterian Brethren Salvation-Army Independent. For non-PROT use '-' unless an obvious sect. "
      "Output ONLY a JSON array of EXACTLY {N} strings 'CODE/denom' in order.\nNames:\n", None),

    "community": ("Each name is a Hong Kong community/neighbourhood charity. Infer its socio-political CHARACTER "
      "from the name (this is an inference, not a verified affiliation). Codes: "
      "RURAL=rural/indigenous-village body(鄉事委員會, 村公所, 原居民, 宗族/祖堂) "
      "KAIFONG=kaifong/neighbourhood-welfare association(街坊福利會, 坊眾, 街坊會) "
      "OWNERS=owners/residents/estate body(業主, 居民協會, 屋苑/邨) "
      "PATRIOTIC=explicitly patriotic / pro-establishment-named(愛國, 同心, 建設, 關注, 聯誼 with establishment tone) "
      "CIVIL=civil-society / advocacy / rights / development "
      "NATIVE=native-place / 同鄉 grouping "
      "MUTUAL=general mutual-aid / community-service, no clear lean "
      "OTH=unclear. Output ONLY a JSON array of EXACTLY {N} uppercase codes in order.\nNames:\n", None),
}

PROMPT_VERSIONS = {
    mode: hashlib.sha256(header.encode()).hexdigest()[:12]
    for mode, (header, _) in PROMPTS.items()
}

RELIGION_RE = re.compile(r"^[A-Z]{2,6}/[A-Za-z-]+$")
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


def _request(body):
    req = urllib.request.Request(URL, data=body,
        headers={"Authorization": f"Bearer {api_key()}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as response:  # noqa: S310 — fixed https endpoint
            data = json.load(response)
        return data["choices"][0]["message"].get("content") or ""
    except urllib.error.HTTPError:
        raise
    except (OSError, ValueError, KeyError, IndexError) as error:
        raise RuntimeError(f"unusable OpenRouter reply: {error}") from None


def _normalise_religion(value):
    code, _, denom = value.partition("/")
    return f"{code.strip().upper()}/{(denom.strip() or '-')}"


def _parse(txt, n, mode, valid):
    """Return a validated list of exactly n labels, or None if the reply is unusable."""
    if not txt:
        return None
    match = re.search(r"\[.*\]", txt, re.S)
    if not match:
        return None
    try:
        arr = json.loads(match.group(0))
    except ValueError:
        return None
    if not isinstance(arr, list):
        return None
    arr = [str(value).strip() for value in arr]
    if len(arr) != n:
        return None
    if mode == "religion":
        arr = [_normalise_religion(value) for value in arr]
        if not all(RELIGION_RE.match(value) for value in arr):
            return None
        if not all(value.split("/")[0] in RELIGION_CODES for value in arr):
            return None
        return arr
    arr = [value.upper() for value in arr]
    if mode == "community":
        return [value if value in COMMUNITY_CODES else "OTH" for value in arr]
    return [value if value in valid else "OTH" for value in arr]


def call(names, hdr, mode, valid, attempts=4):
    body = json.dumps({"model": MODEL, "temperature": 0,
        "messages": [{"role": "user", "content": hdr.replace("{N}", str(len(names))) +
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
        labels = _parse(txt, len(names), mode, valid)
        if labels is not None:
            return labels
        if attempt < attempts - 1:
            time.sleep(1.5 * (2 ** attempt))
    return None


def parse_args(argv: list[str]) -> tuple[str, str | None]:
    mode = None
    since = None
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--since":
            index += 1
            if index >= len(argv):
                raise SystemExit("--since needs a git revision")
            since = argv[index]
        elif mode is None:
            mode = arg
        else:
            raise SystemExit(f"unexpected argument: {arg}")
        index += 1
    if mode not in PROMPTS:
        raise SystemExit("usage: classify_sub.py {rescue|religion|community} [--since REF]")
    return mode, since


def row_key(row):
    """Identity within a categorised row, used to align a previous run."""
    return (row["english_name"].strip(), row["chinese_name"].strip(), row["effective_date"].strip())


def keyed(rows):
    """Keys with an occurrence index so duplicate names stay distinguishable."""
    seen = Counter()
    keys = []
    for row in rows:
        key = row_key(row)
        keys.append((key, seen[key]))
        seen[key] += 1
    return keys


def load_previous(ref: str, mode: str, want: str):
    def show(path):
        try:
            result = subprocess.run(["git", "show", f"{ref}:{path}"], check=True,
                                    capture_output=True, text=True)
        except (OSError, subprocess.CalledProcessError) as error:
            raise SystemExit(f"cannot read {path} at {ref}: {error}") from None
        return result.stdout.lstrip("\ufeff")

    old_rows = [row for row in csv.DictReader(io.StringIO(show("s88list_categorised.csv")))
                if row["code"] == want]
    old_labels = [row["result"] for row in csv.DictReader(io.StringIO(show(f"sub_{mode}.csv")))]
    if len(old_rows) != len(old_labels):
        raise SystemExit(f"{ref}:{mode} sub file does not match its categorisation; run without --since")
    return old_rows, old_labels


def align_previous(old_rows, old_labels, new_rows):
    """Reuse labels when ``new_rows`` is the old sequence plus inserted rows."""
    old_keys, new_keys = keyed(old_rows), keyed(new_rows)
    reuse: list[str | None] = [None] * len(new_rows)
    old_index = 0
    for new_index, key in enumerate(new_keys):
        if old_index < len(old_keys) and key == old_keys[old_index]:
            reuse[new_index] = old_labels[old_index]
            old_index += 1
    if old_index != len(old_keys):
        raise SystemExit("categorisation removed or reordered previous rows; run without --since for a full refresh")
    return reuse


def write_sub_rows(path: str, labels, rows) -> None:
    try:
        with open(path, "w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["result", "english_name", "chinese_name"])
            for label, row in zip(labels, rows, strict=True):
                writer.writerow([label, row["english_name"], row["chinese_name"]])
    except OSError as error:
        raise SystemExit(f"cannot write {path}: {error}") from None


def main(argv: list[str] | None = None) -> int:
    mode, since = parse_args(list(sys.argv[1:] if argv is None else argv))
    check_source()
    hdr, valid = PROMPTS[mode]
    want = {"rescue": "OTH", "religion": "REL", "community": "COM"}[mode]
    try:
        with open("s88list_categorised.csv", encoding="utf-8-sig") as handle:
            rows = [row for row in csv.DictReader(handle) if row["code"] == want]
    except OSError as error:
        raise SystemExit(f"cannot read s88list_categorised.csv: {error}") from None
    if mode == "rescue" and pathlib.Path("sub_rescue.csv").exists():
        try:
            with open("sub_rescue.csv", encoding="utf-8-sig", newline="") as handle:
                existing = sum(1 for _ in csv.DictReader(handle))
        except OSError as error:
            raise SystemExit(f"cannot read sub_rescue.csv: {error}") from None
        if existing > len(rows):
            raise SystemExit(
                f"sub_rescue.csv holds {existing} labels but only {len(rows)} OTH rows remain; "
                "it is an applied audit file — rename or remove it before regenerating rescue output"
            )
    names = [(row["chinese_name"] or row["english_name"]).strip() for row in rows]
    print(f"mode={mode} n={len(names)}", flush=True)

    out: list[str | None] = [None] * len(names)
    todo = list(range(len(names)))
    if since:
        old_rows, old_labels = load_previous(since, mode, want)
        out = align_previous(old_rows, old_labels, rows)
        todo = [index for index, label in enumerate(out) if label is None]
        print(f"reusing {len(names) - len(todo)} labels from {since}; classifying {len(todo)}", flush=True)

    def run(group, batch_size):
        batches = [group[i:i + batch_size] for i in range(0, len(group), batch_size)]
        failed = []
        if not batches:
            return failed
        with cf.ThreadPoolExecutor(max_workers=WORKERS) as executor:
            futures = {executor.submit(call, [names[i] for i in batch], hdr, mode, valid): batch
                       for batch in batches}
            done = 0
            for future in cf.as_completed(futures):
                batch = futures[future]
                try:
                    result = future.result()
                except Exception:
                    result = None
                if result is None:
                    failed.extend(batch)
                else:
                    for index, value in zip(batch, result, strict=True):
                        out[index] = value
                done += 1
                if done % 25 == 0 or done == len(batches):
                    print(f"  {done}/{len(batches)} batches ({len(failed)} rows retrying)", flush=True)
        return failed

    failed = run(todo, BATCH)
    if failed:                       # one slower second pass, smaller batches
        print(f"second pass: {len(failed)} rows", flush=True)
        failed = run(sorted(failed), 6)
    fallback = "OTH/-" if mode == "religion" else "OTH"
    for index in failed:
        out[index] = fallback
    labels = [value if value is not None else fallback for value in out]

    write_sub_rows(f"sub_{mode}.csv", labels, rows)
    failures_path = pathlib.Path(f"sub_{mode}.failures.csv")
    if failed:
        write_sub_rows(str(failures_path), [fallback] * len(failed), [rows[index] for index in failed])
    elif failures_path.exists():
        failures_path.unlink()

    if mode == "religion":
        religions = Counter(value.split("/")[0] for value in labels)
        denominations = Counter(value.split("/", 1)[1] for value in labels
                                if value.split("/")[0] == "PROT")
        print("RELIGION", dict(religions.most_common()))
        print("PROT_DENOM", dict(denominations.most_common()))
    else:
        print("COUNTS", dict(Counter(labels).most_common()))

    write_meta(model=MODEL, prompt_version=PROMPT_VERSIONS[mode], fallback_rows=len(failed),
               updated_by=[f"classify_sub.py {mode}"], stage=mode)
    print(f"DONE {len(out) - len(failed)}/{len(out)} classified", flush=True)
    if failed:
        print(f"WARNING: {len(failed)} rows fell back to {fallback}; see {failures_path}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
