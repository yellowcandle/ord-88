#!/usr/bin/env python3
"""Second-pass + sub-classification using qwen/qwen3.7-plus via OpenRouter.

Modes:
  rescue     -- re-examine code==OTH names; assign best main category, OTH only if truly generic.
  religion   -- sub-classify code==REL names into religion/denomination.
  community  -- sub-classify code==COM names by inferred socio-political character.

Reads s88list_categorised.csv; writes sub_<mode>.csv.
"""
import csv, json, os, re, sys, urllib.request
import concurrent.futures as cf
from collections import Counter

MODEL="qwen/qwen3.7-plus"; BATCH=15; WORKERS=16
URL="https://openrouter.ai/api/v1/chat/completions"
KEY=json.load(open(os.path.expanduser("~/.pi/agent/auth.json")))["openrouter"]["key"]

MAIN_CODES=["REL","EDU","MED","ELD","DIS","YTH","WOM","ART","SPT","ENV","CLN","COM","BIZ","WEL","FND","ASN","OTH"]

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

def call(names, hdr, valid):
    body=json.dumps({"model":MODEL,"temperature":0,
        "messages":[{"role":"user","content":hdr.replace("{N}",str(len(names)))+
            "\n".join(f"{i+1}. {n}" for i,n in enumerate(names))+"\nJSON:"}]}).encode()
    req=urllib.request.Request(URL,data=body,headers={"Authorization":f"Bearer {KEY}","Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=120) as r: d=json.load(r)
        txt=d["choices"][0]["message"].get("content") or ""
    except Exception: return None
    if not txt: return None
    m=re.search(r'\[.*\]',txt,re.S)
    if not m: return None
    try: arr=json.loads(m.group(0))
    except Exception: return None
    arr=[str(x).strip() for x in arr]
    if len(arr)!=len(names): return None
    if valid: arr=[(x.upper() if x.upper() in valid else "OTH") for x in arr]
    return arr

def main():
    mode=sys.argv[1]; hdr,valid=PROMPTS[mode]
    want={"rescue":"OTH","religion":"REL","community":"COM"}[mode]
    with open("s88list_categorised.csv",encoding="utf-8-sig") as f:
        rows=[r for r in csv.DictReader(f) if r["code"]==want]
    names=[(r["chinese_name"] or r["english_name"]).strip() for r in rows]
    print(f"mode={mode} n={len(names)}",flush=True)
    idxs=list(range(len(names)))
    batches=[idxs[i:i+BATCH] for i in range(0,len(idxs),BATCH)]
    out=[None]*len(names)
    def work(b):
        try:
            sub=[names[i] for i in b]
            res=call(sub,hdr,valid) or call(sub,hdr,valid)
        except Exception:
            res=None
        if res is None: res=["OTH/-" if mode=="religion" else "OTH"]*len(b)
        return list(zip(b,res))
    done=0
    with cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for fut in cf.as_completed([ex.submit(work,b) for b in batches]):
            for i,v in fut.result(): out[i]=v
            done+=1
            if done%10==0 or done==len(batches): print(f"  {done}/{len(batches)}",flush=True)
    with open(f"sub_{mode}.csv","w",encoding="utf-8-sig",newline="") as f:
        w=csv.writer(f); w.writerow(["result","english_name","chinese_name"])
        for r,row in zip(out,rows): w.writerow([r,row["english_name"],row["chinese_name"]])
    if mode=="religion":
        rel=Counter(x.split("/")[0] for x in out); den=Counter(x for x in out if x.split("/")[0]=="PROT")
        print("RELIGION",dict(rel.most_common()))
        print("PROT_DENOM",dict(den.most_common()))
    else:
        print("COUNTS",dict(Counter(out).most_common()))

if __name__=="__main__": main()
