#!/usr/bin/env python3
"""Hybrid categoriser: keyword pre-filter + qwen3.7-plus (via OpenRouter) tie-break.

Confident single-keyword-match names are kept as-is. The 0-match ("Other") and
2+-match (ambiguous) names are sent to qwen/qwen3.7-plus in concurrent batches.
Per batch: validate the JSON array length == batch size; on any failure retry once,
then fall back to the keyword's first match (or OTH).

Usage:  classify_or.py [LIMIT]   # LIMIT optional: only process first N ambiguous (for testing)
"""
import csv, json, os, re, sys, urllib.request, urllib.error
import concurrent.futures as cf
from collections import Counter

SRC="s88list.csv"
MODEL="qwen/qwen3.7-plus"
BATCH=15
WORKERS=16
URL="https://openrouter.ai/api/v1/chat/completions"
KEY=json.load(open(os.path.expanduser("~/.pi/agent/auth.json")))["openrouter"]["key"]

CATS=[
 ("REL","Religious 宗教",["教會","教堂","廟","寺","庵","佛教","菩薩","道教","道堂","基督","天主","耶穌","福音","宣道","浸信","信義","循道","聖公","靈糧","神召","救世軍","清真","回教","孔教","黃大仙","關帝","天后宮","church","christ","gospel","ministr","catholic","buddhis","temple","islam","muslim","mosque","evangel","baptist"]),
 ("EDU","Education 教育",["學校","中學","小學","幼稚園","幼兒園","書院","學院","教育","助學","獎學","校友","家長教師","補習","school","colleg","education","academ","scholarship","alumni","kindergarten","university"]),
 ("MED","Medical & Health 醫療衞生",["醫院","醫療","醫學","健康","護理院","保健","病人","癌","紓緩","善終","hospital","medical","health","clinic","cancer","hospice","nursing","patient"]),
 ("ELD","Elderly 長者",["長者","耆英","安老","老人","老年","銀齡","頤養","松柏","elderly","aged","old age","senior"]),
 ("DIS","Disability & Rehab 復康傷健",["殘疾","傷健","弱能","失明","視障","聾","聽障","智障","自閉","唐氏","康復","展能","復康","disab","blind","deaf","handicap","autis","rehab"]),
 ("YTH","Youth & Children 青少年兒童",["青年","青少年","少年","兒童","幼童","學童","童軍","youth","children","child ","scout","teen","juvenile"]),
 ("WOM","Women 婦女",["婦女","婦聯","女性","母親","women","woman","ladies","female"]),
 ("ART","Arts & Culture 文化藝術",["藝術","文化","音樂","戲","曲藝","粵劇","京劇","國畫","書法","舞蹈","劇團","合唱","文藝","美術","攝影","文學","art","culture","music","opera","choir","danc","drama","theatre","calligraph","heritage"]),
 ("SPT","Sports & Recreation 體育康樂",["體育","運動","武術","太極","龍舟","足球","籃球","康樂","康體","sport","athletic","martial","tai chi","football","recreation","fitness"]),
 ("ENV","Animals & Environment 動物環保",["動物","護生","流浪","環保","環境","綠色","保育","生態","animal","spca","environment","green","conserv","ecolog","wildlife","nature"]),
 ("CLN","Clan & Native-place 宗親同鄉",["宗親","同鄉","聯誼","世家","clan","native","clansmen"]),
 ("COM","Community & Kaifong 社區街坊",["街坊","居民","業主","社區","鄉事","坊眾","互助","neighbourhood","community","resident","village","kaifong","owners"]),
 ("BIZ","Professional & Business 專業商會",["商會","工會","公會","實業","行業","僱員","職工","專業","chamber","trade","profession","commerc","industr","business"]),
 ("WEL","Social Welfare & Services 社會福利服務",["福利","社會服務","關懷","關愛","扶輪","獅子會","明愛","樂施","慈善","救濟","扶貧","賑災","welfare","caritas","rotary","lions","oxfam","relief","charit","caring"]),
 ("FND","Foundation & Trust 基金信託",["基金","信託","foundation","trust","endowment"]),
 ("ASN","Clubs & Associations 會社協會",["協會","學會","聯會","總會","會所","俱樂部","association","society","club","federation","council","league","union","institute"]),
]
CODES=[c[0] for c in CATS]+["OTH"]
LABEL={c:l for c,l,_ in CATS}; LABEL["OTH"]="Other / Uncategorised 其他"

PROMPT_HDR=("You are an expert classifier of Hong Kong charities. For each numbered name output "
 "exactly ONE category code. Output ONLY a JSON array of EXACTLY {N} uppercase code strings in order, no prose.\n"
 "Codes: REL=religious/temple/church EDU=education/school MED=medical/health/hospital "
 "ELD=elderly/nursing-home DIS=disability/rehab YTH=youth/children WOM=women ART=arts/culture/music/opera "
 "SPT=sports/recreation ENV=animals/environment CLN=clan/native-place-association COM=community/kaifong/residents "
 "BIZ=professional/trade/business WEL=social-welfare/charity-services FND=foundation/grant-making-fund "
 "ASN=generic-club/association OTH=other.\nNames:\n")

def matches(text):
    return [code for code,_,kws in CATS if any(kw and kw in text for kw in kws)]

def call(names):
    """names: list[str]. returns list[str] codes of same length, or None on failure."""
    body=json.dumps({"model":MODEL,"temperature":0,
        "messages":[{"role":"user","content":PROMPT_HDR.replace("{N}",str(len(names)))+
            "\n".join(f"{i+1}. {n}" for i,n in enumerate(names))+"\nJSON:"}]}).encode()
    req=urllib.request.Request(URL,data=body,headers={
        "Authorization":f"Bearer {KEY}","Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=120) as r:
            d=json.load(r)
        txt=d["choices"][0]["message"].get("content") or ""
    except Exception as e:
        return None
    if not txt: return None
    m=re.search(r'\[.*\]',txt,re.S)
    if not m: return None
    try: arr=json.loads(m.group(0))
    except Exception: return None
    arr=[str(x).upper().strip() for x in arr]
    arr=[x if x in CODES else "OTH" for x in arr]
    if len(arr)!=len(names): return None
    return arr

def classify_batch(batch):
    names=[n for _,n,_ in batch]
    res=call(names)
    if res is None:                       # retry once
        res=call(names)
    if res is None:                       # fallback to keyword guess
        res=[fb for _,_,fb in batch]
    return [(idx,code) for (idx,_,_),code in zip(batch,res)]

def main():
    limit=int(sys.argv[1]) if len(sys.argv)>1 else None
    with open(SRC,encoding="utf-8-sig",newline="") as f:
        data=[r for r in list(csv.reader(f))[1:] if any(c.strip() for c in r)]
    final=[None]*len(data); ambiguous=[]
    for idx,r in enumerate(data):
        h=matches(" ".join(r[1:6]).lower())
        if len(h)==1: final[idx]=h[0]
        else: ambiguous.append((idx,(r[2] or r[1]).strip(), h[0] if h else "OTH"))
    if limit: ambiguous=ambiguous[:limit]
    print(f"confident={sum(x is not None for x in final)} ambiguous_to_LLM={len(ambiguous)}",flush=True)

    batches=[ambiguous[i:i+BATCH] for i in range(0,len(ambiguous),BATCH)]
    done=0
    with cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs=[ex.submit(classify_batch,b) for b in batches]
        for fut in cf.as_completed(futs):
            for idx,code in fut.result(): final[idx]=code
            done+=1
            if done%10==0 or done==len(batches):
                print(f"  batches {done}/{len(batches)}",flush=True)

    if limit:                              # test mode: just print sample, don't overwrite full output
        for idx,name,fb in ambiguous[:20]:
            print(f"  {final[idx]:<4} {name[:30]}  (kw_fallback={fb})")
        return
    with open("s88list_categorised.csv","w",encoding="utf-8-sig",newline="") as f:
        w=csv.writer(f); w.writerow(["code","category","english_name","chinese_name","effective_date"])
        for idx,r in enumerate(data):
            code=final[idx] or "OTH"
            w.writerow([code,LABEL[code],r[1],r[2],r[6]])
    cnt=Counter(final[idx] or "OTH" for idx in range(len(data)))
    json.dump({"total":len(data),"counts":dict(cnt),"labels":LABEL},
              open("category_counts.json","w"),ensure_ascii=False,indent=2)
    print("DONE",dict(cnt),flush=True)

if __name__=="__main__":
    main()
