#!/usr/bin/env python3
"""Hybrid categoriser for the IRD section-88 charity list.

Stage 1: keyword classifier with multi-label detection.
  - exactly 1 category matched  -> confident, keep.
  - 0 matches or >=2 matches     -> ambiguous, defer to LLM (pi CLI).
Stage 2: batch the ambiguous names through `pi` (deepseek-v4-flash) concurrently,
         parse JSON, fall back to the keyword's first match (or OTH) on failure.
"""
import csv, json, re, subprocess, sys, concurrent.futures as cf

SRC = "s88list.csv"

# ---- category taxonomy: code -> (label, keywords) in PRIORITY order ----
CATS = [
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
CODES = [c[0] for c in CATS] + ["OTH"]
LABEL = {c:l for c,l,_ in CATS}; LABEL["OTH"]="Other / Uncategorised 其他"

def matches(text):
    return [code for code,_,kws in CATS if any(kw and kw in text for kw in kws)]

def load():
    with open(SRC, encoding="utf-8-sig", newline="") as f:
        return [r for r in list(csv.reader(f))[1:] if any(c.strip() for c in r)]

PROMPT_HDR = ('Classify each Hong Kong charity into exactly ONE code. '
 'Output ONLY a JSON array [{"i":N,"c":"CODE"}], no prose. Codes: '
 'REL=religious EDU=education MED=medical/health ELD=elderly DIS=disability '
 'YTH=youth/children WOM=women ART=arts/culture SPT=sports ENV=animals/environment '
 'CLN=clan/native-place COM=community/kaifong BIZ=professional/business '
 'WEL=social-welfare FND=foundation/grant-making ASN=general-club/association OTH=other.\nNames:\n')

def call_pi(batch):
    """batch: list of (idx, name). returns dict idx->code."""
    prompt = PROMPT_HDR + "\n".join(f"{i}. {n}" for i,n in batch)
    try:
        out = subprocess.run(["pi","-p","-nt","--thinking","off","--no-session",prompt],
                             capture_output=True, text=True, timeout=180).stdout
    except subprocess.TimeoutExpired:
        return {}
    m = re.search(r'\[.*\]', out, re.S)
    if not m: return {}
    try:
        arr = json.loads(m.group(0))
    except Exception:
        return {}
    res={}
    for o in arr:
        try:
            i=int(o["i"]); c=str(o["c"]).upper().strip()
            if c in CODES: res[i]=c
        except Exception: pass
    return res

def main():
    data = load()
    final = [None]*len(data)
    ambiguous = []                      # (row_index, name, fallback_code)
    for idx,r in enumerate(data):
        t=" ".join(r[1:6]).lower()
        h=matches(t)
        if len(h)==1:
            final[idx]=h[0]
        else:
            fallback = h[0] if h else "OTH"
            ambiguous.append((idx,(r[2] or r[1]).strip(),fallback))
    print(f"confident={sum(x is not None for x in final)} ambiguous={len(ambiguous)}", flush=True)

    BATCH=60
    batches=[ambiguous[i:i+BATCH] for i in range(0,len(ambiguous),BATCH)]
    def work(b):
        return call_pi([(i,name) for (i,name,_) in b]), b
    done=0
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for res,b in ex.map(work,batches):
            for (idx,name,fb) in b:
                # b's positions were numbered by row index idx
                final[idx]=res.get(idx,fb)
            done+=1
            if done%10==0: print(f"  batches {done}/{len(batches)}", flush=True)

    # write out
    with open("s88list_categorised.csv","w",encoding="utf-8-sig",newline="") as f:
        w=csv.writer(f); w.writerow(["code","category","english_name","chinese_name","effective_date"])
        for idx,r in enumerate(data):
            code=final[idx] or "OTH"
            w.writerow([code,LABEL[code],r[1],r[2],r[6]])
    from collections import Counter
    cnt=Counter(final[idx] or "OTH" for idx in range(len(data)))
    json.dump({"total":len(data),"counts":cnt,"labels":LABEL},
              open("category_counts.json","w"),ensure_ascii=False,indent=2)
    print("DONE", dict(cnt))

if __name__=="__main__":
    main()
