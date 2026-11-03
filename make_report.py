#!/usr/bin/env python3
"""Build the markdown report + bar chart from the categorised output."""
import os

os.environ.setdefault("MPLBACKEND", "Agg")

import csv
import datetime
import json
from collections import Counter, defaultdict

import matplotlib.pyplot as plt
from matplotlib import font_manager

cnt=json.load(open("category_counts.json"))
counts=cnt["counts"]; LABEL=cnt["labels"]; total=cnt["total"]

# "as at" date straight from the source CSV so the report can never go stale
AS_AT="unknown"
try:
    with open("s88list.csv",encoding="utf-8-sig",newline="") as f:
        _rows=[r for r in csv.reader(f) if any(c.strip() for c in r)]
    _dmy=_rows[1][0].strip() if len(_rows)>1 else ""
    if _dmy:
        AS_AT=datetime.datetime.strptime(_dmy,"%d/%m/%Y").strftime("%-d %B %Y")
except (OSError, ValueError, IndexError):
    pass

# pick a CJK-capable font if available so Chinese labels render
for cand in ["PingFang HK","PingFang SC","Heiti TC","Arial Unicode MS","STHeiti"]:
    try:
        font_manager.findfont(cand,fallback_to_default=False); plt.rcParams["font.family"]=cand; break
    except Exception: pass

order=sorted(counts,key=lambda k:counts[k],reverse=True)
en={ "REL":"Religious","EDU":"Education","WEL":"Social Welfare","MED":"Medical & Health",
 "FND":"Foundation & Trust","ASN":"Clubs & Associations","ART":"Arts & Culture","YTH":"Youth & Children",
 "COM":"Community & Kaifong","ENV":"Animals & Environment","BIZ":"Professional & Business","ELD":"Elderly",
 "DIS":"Disability & Rehab","WOM":"Women","CLN":"Clan & Native-place","SPT":"Sports & Recreation","OTH":"Other"}

# examples per category
ex=defaultdict(list)
with open("s88list_categorised.csv",encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        c=row["code"]
        if len(ex[c])<4:
            ex[c].append((row["chinese_name"] or row["english_name"]).strip()[:24])

# ---- chart ----
fig,ax=plt.subplots(figsize=(10,7))
labels=[str(en.get(k,k)) for k in order]
vals=[counts[k] for k in order]
bars=ax.barh(labels[::-1],vals[::-1],color="#3b6ea5")
ax.set_title(f"HK Section-88 Tax-Exempt Charities by Category (n={total:,}, as at {AS_AT})")
ax.set_xlabel("Number of organisations")
for b,v in zip(bars,vals[::-1]):
    ax.text(b.get_width()+max(vals)*0.005,b.get_y()+b.get_height()/2,
            f"{v:,} ({100*v/total:.1f}%)",va="center",fontsize=8)
plt.tight_layout(); plt.savefig("s88_categories.png",dpi=150)
print("wrote s88_categories.png")

# ---- markdown ----
L=["# Hong Kong Section-88 Tax-Exempt Charities — Categorisation",
 "",f"**Source:** IRD `s88list.csv` · **As at:** {AS_AT} · **Total organisations:** {total:,}",
 "","**Method:** hybrid classifier — deterministic bilingual keyword matching for confident",
 "single-match names, with `qwen/qwen3.7-plus` (via OpenRouter) as the LLM tie-breaker for",
 "ambiguous (multi-keyword) and unmatched names.","",
 "![category distribution](s88_categories.png)","",
 "| # | Category | Count | % | Examples |","|---|---|---:|---:|---|"]
for i,k in enumerate(order,1):
    L.append(f"| {i} | {LABEL[k]} | {counts[k]:,} | {100*counts[k]/total:.1f}% | "
             + " · ".join(ex[k][:3]) + " |")
L+=["",f"**Outputs:** `s88list_categorised.csv` (per-org labels), `category_counts.json`, `s88_categories.png`"]
open("s88_report.md","w").write("\n".join(L))
print("wrote s88_report.md")
