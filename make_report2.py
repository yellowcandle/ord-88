#!/usr/bin/env python3
"""Enhanced report: main categories + religion sub-breakdown + community socio-political."""
import csv, json
from collections import Counter, defaultdict
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

for cand in ["PingFang HK","PingFang SC","Heiti TC","Arial Unicode MS","STHeiti"]:
    try: font_manager.findfont(cand,fallback_to_default=False); plt.rcParams["font.family"]=cand; break
    except Exception: pass

# ---------- religion ----------
relrows=list(csv.DictReader(open("sub_religion.csv",encoding="utf-8-sig")))
relig=Counter(); denom=Counter(); relex=defaultdict(list)
RELNAME={"BUD":"Buddhism 佛教","TAO":"Taoism 道教","FOLK":"Chinese folk religion 民間信仰",
 "PROT":"Protestant Christian 基督新教","CATH":"Roman Catholic 天主教","CHRX":"Other Christian 其他基督宗教",
 "ISL":"Islam 伊斯蘭教","CONF":"Confucianism 孔教","HIN":"Hindu 印度教","SIK":"Sikh 錫克教",
 "JEW":"Jewish 猶太教","BAHAI":"Baha'i 巴哈伊","OTH":"Unclear / other 不明"}
for r in relrows:
    code=r["result"].split("/")[0].upper()
    relig[code]+=1
    if len(relex[code])<4: relex[code].append((r["chinese_name"] or r["english_name"])[:22])
    if code=="PROT":
        d=r["result"].split("/",1)[1].strip() if "/" in r["result"] else ""
        denom[d if d not in ("","-") else "Unstated"]+=1

# ---------- community ----------
comrows=list(csv.DictReader(open("sub_community.csv",encoding="utf-8-sig")))
com=Counter(r["result"] for r in comrows); comex=defaultdict(list)
for r in comrows:
    if len(comex[r["result"]])<3: comex[r["result"]].append((r["chinese_name"] or r["english_name"])[:22])
COMNAME={"RURAL":"Rural / indigenous 鄉事原居民","KAIFONG":"Kaifong welfare 街坊福利",
 "OWNERS":"Owners / residents 業主居民","PATRIOTIC":"Patriotic / pro-establishment-named 愛國建制",
 "CIVIL":"Civil society / advocacy 公民社會","NATIVE":"Native-place 同鄉","MUTUAL":"General mutual-aid 互助服務",
 "OTH":"Unclear 不明"}

# ---------- charts ----------
def barchart(counts,namemap,title,fn,color):
    order=sorted(counts,key=lambda k:counts[k],reverse=True)
    tot=sum(counts.values())
    fig,ax=plt.subplots(figsize=(9,0.55*len(order)+1.5))
    labels=[namemap.get(k,k) for k in order]; vals=[counts[k] for k in order]
    ax.barh(labels[::-1],vals[::-1],color=color)
    ax.set_title(title); ax.set_xlabel("Organisations")
    for i,v in enumerate(vals[::-1]):
        ax.text(v+max(vals)*0.01,i,f"{v:,} ({100*v/tot:.1f}%)",va="center",fontsize=8)
    plt.tight_layout(); plt.savefig(fn,dpi=150); plt.close()
    print("wrote",fn)

barchart(relig,RELNAME,f"Religious charities by religion (n={sum(relig.values()):,})","s88_religion.png","#8a5a44")
barchart(com,COMNAME,f"Community charities by inferred socio-political character (n={sum(com.values()):,})","s88_community.png","#44708a")

# ---------- markdown ----------
def table(counts,namemap,ex):
    tot=sum(counts.values()); L=["| Category | Count | % | Examples |","|---|---:|---:|---|"]
    for k in sorted(counts,key=lambda k:counts[k],reverse=True):
        L.append(f"| {namemap.get(k,k)} | {counts[k]:,} | {100*counts[k]/tot:.1f}% | "+" · ".join(ex.get(k,[])[:3])+" |")
    return "\n".join(L)

L=["# HK Section-88 Charities — Religious & Community Sub-Breakdowns","",
 "*LLM sub-classification via `qwen/qwen3.7-plus`. Religion/denomination and socio-political",
 "character are **inferred from organisation names** and are indicative, not authoritative.*","",
 "## Religious groups by religion","",f"![religion](s88_religion.png)","",
 table(relig,RELNAME,relex),"","### Protestant denominations","",
 "| Denomination | Count |","|---|---:|"]
for d,n in denom.most_common():
    L.append(f"| {d} | {n:,} |")
L+=["","## Community groups by inferred socio-political character","",
 "![community](s88_community.png)","",table(com,COMNAME,comex),"",
 "> **Caveat:** affiliation is inferred from naming patterns (e.g. 鄉事委員會 → rural-indigenous,",
 "> 街坊福利會 → kaifong-grassroots, 各界聯會/社團聯會 → pro-establishment umbrella). It is a lean for",
 "> the group as a *type*, not a verified political stance of any individual organisation.",
 "","**Outputs:** `sub_religion.csv`, `sub_community.csv`, `s88_religion.png`, `s88_community.png`"]
open("s88_subreport.md","w").write("\n".join(L))
print("wrote s88_subreport.md")
print("RELIGION",dict(relig.most_common()))
print("PROT_DENOM",dict(denom.most_common()))
