#!/usr/bin/env python3
"""Second-pass + sub-classification using qwen/qwen3.7-plus via OpenRouter.

Modes:
  rescue     -- re-examine code==OTH names; assign best main category, OTH only if truly generic.
  religion   -- sub-classify code==REL names into religion/denomination.
  community  -- sub-classify code==COM names by inferred socio-political character.

Reads s88list_categorised.csv; writes sub_<mode>.csv, one row per matching input row
in input order. Transient HTTP failures and malformed replies are retried with
backoff; rows that still fail are reported and make the run exit non-zero instead of
silently writing a placeholder. Run this again whenever s88list_categorised.csv is
regenerated -- the output is positional, so a stale file silently mislabels the
register.
"""
import csv, json, os, re, sys, time, urllib.error, urllib.request
import concurrent.futures as cf
from collections import Counter

MODEL="qwen/qwen3.7-plus"; BATCH=15; WORKERS=16
URL="https://openrouter.ai/api/v1/chat/completions"
KEY=json.load(open(os.path.expanduser("~/.pi/agent/auth.json")))["openrouter"]["key"]

MAIN_CODES=["REL","EDU","MED","ELD","DIS","YTH","WOM","ART","SPT","ENV","CLN","COM","BIZ","WEL","FND","ASN","OTH"]

RELIGION_CODES={"BUD","TAO","FOLK","PROT","CATH","CHRX","ISL","CONF","HIN","SIK","JEW","BAHAI","OTH"}

PROMPTS={
"rescue":("Each name is a Hong Kong tax-exempt charity that a first pass could not categorise. "
  "Assign the single best main category code; use OTH ONLY if the name is a generic company/holding "
  "name with no charitable hint at all. Output ONLY a JSON array of EXACTLY {N} uppercase codes in order.\n"
  "Codes: REL EDU MED ELD DIS YTH WOM ART SPT ENV CLN COM BIZ WEL FND ASN OTH.\nNames:\n",
  set(MAIN_CODES)),

"religion":("Each name is a Hong Kong religious charity. For each, output 'RELIGION/denomination'. "
  "RELIGION codes: BUD=Buddhism TAO=Taoism FOLK=Chinese-folk-religion(temples to folk deities, 盂蘭勝會, "
  "天后/觀音/關帝/譚公/洪聖/黃大仙 territorial cults, ancestral) PROT=Protestant-Christian CATH=Roman-Catholic "
  "CHRX=other-Christian(Orthodox, Mormon/LDS, Jehovah's-Witnesses, non-denominational) ISL=Islam "
  "CONF=Confucianism HIN=Hindu SIK=Sikh JEW=Jewish BAHAI=Bahai OTH=unclear. "
  "For PROT give a denomination from: Baptist Lutheran Methodist Anglican Pentecostal Alliance Evangelical "
  "Adventist Presbyterian Brethren Salvation-Army Independent. For non-PROT use '-' unless an obvious sect. "
  "Output ONLY a JSON array of EXACTLY {N} strings 'CODE/denom' in order.\nNames:\n", None),

"community":("Each name is a Hong Kong community/neighbourhood charity. Infer its socio-political CHARACTER "
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
COMMUNITY_CODES={"RURAL","KAIFONG","OWNERS","PATRIOTIC","CIVIL","NATIVE","MUTUAL","OTH"}

RETRY_STATUS={408,409,425,429,500,502,503,504}
RELIGION_RE=re.compile(r"^[A-Z]{2,6}/[A-Za-z-]+$")

def _request(body):
    req=urllib.request.Request(URL,data=body,
        headers={"Authorization":f"Bearer {KEY}","Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=120) as r: d=json.load(r)
    return d["choices"][0]["message"].get("content") or ""

def _normalise_religion(value):
    code,_,denom=value.partition("/")
    code=code.strip().upper(); denom=denom.strip() or "-"
    return f"{code}/{denom}"

def _parse(txt, n, mode, valid):
    """Return a validated list of exactly n labels, or None if the reply is unusable."""
    if not txt: return None
    m=re.search(r'\[.*\]',txt,re.S)
    if not m: return None
    try: arr=json.loads(m.group(0))
    except Exception: return None
    if not isinstance(arr,list): return None
    arr=[str(x).strip() for x in arr]
    if len(arr)!=n: return None
    if mode=="religion":
        arr=[_normalise_religion(x) for x in arr]
        if not all(RELIGION_RE.match(x) for x in arr): return None
        if not all(x.split("/")[0] in RELIGION_CODES for x in arr): return None
        return arr
    arr=[x.upper() for x in arr]
    if mode=="community":
        return [x if x in COMMUNITY_CODES else "OTH" for x in arr]
    return [x if x in valid else "OTH" for x in arr]

def call(names, hdr, mode, valid, attempts=4):
    body=json.dumps({"model":MODEL,"temperature":0,
        "messages":[{"role":"user","content":hdr.replace("{N}",str(len(names)))+
            "\n".join(f"{i+1}. {n}" for i,n in enumerate(names))+"\nJSON:"}]}).encode()
    for attempt in range(attempts):
        try:
            txt=_request(body)
        except urllib.error.HTTPError as e:
            if e.code not in RETRY_STATUS: return None
            txt=None
        except Exception:
            txt=None
        labels=_parse(txt,len(names),mode,valid)
        if labels is not None: return labels
        time.sleep(1.5*(2**attempt))
    return None

def main():
    mode=sys.argv[1]; hdr,valid=PROMPTS[mode]
    want={"rescue":"OTH","religion":"REL","community":"COM"}[mode]
    with open("s88list_categorised.csv",encoding="utf-8-sig") as f:
        rows=[r for r in csv.DictReader(f) if r["code"]==want]
    names=[(r["chinese_name"] or r["english_name"]).strip() for r in rows]
    print(f"mode={mode} n={len(names)}",flush=True)
    idxs=list(range(len(names)))
    out=[None]*len(names)

    def run(group):
        batches=[group[i:i+BATCH] for i in range(0,len(group),BATCH)]
        failed=[]
        with cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
            futs={ex.submit(call,[names[i] for i in b],hdr,mode,valid):b for b in batches}
            done=0
            for fut in cf.as_completed(futs):
                b=futs[fut]
                try: res=fut.result()
                except Exception: res=None
                if res is None: failed.extend(b)
                else:
                    for i,v in zip(b,res): out[i]=v
                done+=1
                if done%25==0 or done==len(batches):
                    print(f"  {done}/{len(batches)} batches ({len(failed)} rows retrying)",flush=True)
        return failed

    failed=run(idxs)
    if failed:                       # one slower second pass, smaller batches
        print(f"second pass: {len(failed)} rows",flush=True)
        global BATCH; BATCH=6
        failed=run(sorted(failed))
    fallback="OTH/-" if mode=="religion" else "OTH"
    for i in failed: out[i]=fallback

    with open(f"sub_{mode}.csv","w",encoding="utf-8-sig",newline="") as f:
        w=csv.writer(f); w.writerow(["result","english_name","chinese_name"])
        for r,row in zip(out,rows): w.writerow([r,row["english_name"],row["chinese_name"]])
    if mode=="religion":
        rel=Counter(x.split("/")[0] for x in out); den=Counter(x.split("/",1)[1] for x in out if x.split("/")[0]=="PROT")
        print("RELIGION",dict(rel.most_common()))
        print("PROT_DENOM",dict(den.most_common()))
    else:
        print("COUNTS",dict(Counter(out).most_common()))
    print(f"DONE {len(out)-len(failed)}/{len(out)} classified")
    if failed:
        print(f"WARNING: {len(failed)} rows fell back to {fallback}; re-run before shipping",flush=True)
        return 1
    return 0

if __name__=="__main__": sys.exit(main())
