"""Build the Section 88 plate from the IRD charity register.

The plate is a build artefact: aggregate the CSVs once, render one static page.
Run ``python3 build_site.py`` to write ``dist/index.html`` and ``dist/data.json``.
"""
from __future__ import annotations

import csv
import json
import pathlib
import re
import shutil
import sys
from collections import Counter
from html import escape
from typing import Iterable

from taxonomy import COMMUNITY_LABELS as COMMUNITY
from taxonomy import RELIGION_LABELS as RELIGIONS

CJK = re.compile(r"[\u3400-\u9fff]")

STAGE1_FILLS = ["r1", "r2", "r3", "r4", "r5", "r6", "r7"]
TRADITION_FILLS = ["r1", "n2", "n3", "n4", "n5"]
DENOMINATION_FILLS = ["r2", "r3", "r4", "r5", "r6", "r7", "n5"]

def split_label(label: str) -> tuple[str, str]:
    """Split a bilingual CSV label such as ``Education 教育`` into en/zh."""
    match = CJK.search(label)
    if not match:
        return label.strip(), ""
    return label[: match.start()].strip(" ·-"), label[match.start() :].strip()


def read_register_date(path: pathlib.Path) -> tuple[str, str]:
    """Read the register's own "Position as at" stamp and format both languages."""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.reader(handle):
            if row and row[0].strip() and row[0].strip().lower().startswith("position"):
                continue
            stamp = row[0].strip() if row else ""
            if stamp:
                day, month, year = stamp.split("/")
                months = ["January", "February", "March", "April", "May", "June",
                          "July", "August", "September", "October", "November", "December"]
                en = f"{int(day)} {months[int(month) - 1]} {year}"
                zh = f"{year}年{int(month)}月{int(day)}日"
                return en, zh
    raise ValueError(f"no register date in {path}")


def read_counts(path: pathlib.Path, column: str) -> Counter:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return Counter(row[column] for row in csv.DictReader(handle))


def allocate(counts: Iterable[int], total_px: int, quantum: int = 4, minimum: int = 8) -> list[int]:
    """Split exactly ``total_px`` between ``counts`` in whole ``quantum`` steps."""
    counts = list(counts)
    if not counts:
        return []
    if total_px % quantum:
        raise ValueError(f"total_px={total_px} is not a multiple of quantum={quantum}")
    total = sum(counts)
    if total == 0:
        counts = [1] * len(counts)
        total = len(counts)
    units = total_px // quantum
    floor_units = minimum // quantum
    if floor_units * len(counts) > units:
        raise ValueError(f"{len(counts)} bands need more than {total_px}px")
    spare = units - floor_units * len(counts)
    exact = [count / total * spare for count in counts]
    whole = [floor_units + int(value) for value in exact]
    shortfall = units - sum(whole)
    order = sorted(range(len(counts)), key=lambda i: exact[i] - int(exact[i]), reverse=True)
    for index in order[:shortfall]:
        whole[index] += 1
    return [value * quantum for value in whole]


def share(count: int, total: int) -> float:
    return 0.0 if total == 0 else round(count / total * 100, 1)


def aggregate(root: pathlib.Path) -> dict:
    as_at, as_at_zh = read_register_date(root / "s88list.csv")
    categories = read_counts(root / "s88list_categorised.csv", "category")
    codes = read_counts(root / "s88list_categorised.csv", "code")
    total = sum(categories.values())
    if total == 0:
        raise ValueError("s88list_categorised.csv has no rows — classify the register first")
    purposes = []
    for label, count in categories.most_common():
        en, zh = split_label(label)
        purposes.append({"en": en, "zh": zh, "count": count, "share": share(count, total)})

    head, tail = purposes[:6], purposes[6:]
    stage1 = [dict(row) for row in head]
    stage1.append(
        {
            "en": f"{len(tail)} further purposes",
            "zh": f"其餘{len(tail)}項用途",
            "count": sum(row["count"] for row in tail),
            "share": share(sum(row["count"] for row in tail), total),
        }
    )
    heights = allocate([row["count"] for row in stage1], 560)
    for row, height in zip(stage1, heights):
        row["height"] = height

    religion_counts = Counter()
    denominations = Counter()
    with (root / "sub_religion.csv").open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            code, _, detail = row["result"].partition("/")
            code = code.upper()
            if code not in RELIGIONS:
                code = "OTH"
            religion_counts[code] += 1
            if code == "PROT":
                denominations[detail if detail not in ("", "-") else "Unstated"] += 1

    religious_total = sum(religion_counts.values())
    religious_band = codes.get("REL", 0)
    if religious_band and not religious_total:
        raise ValueError("REL societies exist but sub_religion.csv is empty — run `classify_sub.py religion`")
    traditions = [
        {"en": RELIGIONS[code][0], "zh": RELIGIONS[code][1], "count": count, "share": share(count, religious_total)}
        for code, count in religion_counts.most_common()
    ]
    stage2 = []
    if traditions:
        head, tail = traditions[:4], traditions[4:]
        stage2 = [dict(row) for row in head]
        stage2.append(
            {
                "en": f"{len(tail)} other traditions",
                "zh": f"其餘{len(tail)}個傳統",
                "count": sum(row["count"] for row in tail),
                "share": share(sum(row["count"] for row in tail), religious_total),
            }
        )
        heights = allocate([row["count"] for row in stage2], 300)
        for row, height in zip(stage2, heights):
            row["height"] = height

    protestant_total = religion_counts["PROT"]
    denomination_rows = [
        {"en": label.replace("-", " "), "count": count, "share": share(count, protestant_total)}
        for label, count in denominations.most_common()
    ] if protestant_total else []

    community_counts = read_counts(root / "sub_community.csv", "result")
    community_total = sum(community_counts.values())
    if codes.get("COM", 0) and not community_total:
        raise ValueError("COM societies exist but sub_community.csv is empty — run `classify_sub.py community`")
    community = []
    for code, count in community_counts.most_common():
        key = code.split("/")[0].upper()
        en, zh = COMMUNITY.get(key, (key.title(), ""))
        community.append({"en": en, "zh": zh, "count": count, "share": share(count, community_total)})

    return {
        "total": total,
        "as_at": as_at,
        "as_at_zh": as_at_zh,
        "religious_band": religious_band,
        "religious_total": religious_total,
        "religious_unclassified": max(0, religious_band - religious_total),
        "tradition_count": len(religion_counts),
        "denomination_count": len(denomination_rows),
        "denomination_total": protestant_total,
        "community_total": community_total,
        "community_unclassified": max(0, codes.get("COM", 0) - community_total),
        "purposes": purposes,
        "stage1": stage1,
        "traditions": stage2,
        "stage2_full": traditions,
        "denominations": denomination_rows,
        "community": community,
    }


CSS = """
:root{--ink:#17171A;--ink2:#5C5A56;--line:#E4E1DE;--bg:#fff;
--r1:#8C3A1E;--r2:#A8482A;--r3:#B4552F;--r4:#C26A42;--r5:#CC8158;--r6:#D5966F;--r7:#DDA986;
--n1:#23211E;--n2:#6E6A65;--n3:#85807A;--n4:#A39E97;--n5:#C2BDB6;
--display:"Bricolage Grotesque",Georgia,serif;--body:"DM Sans",-apple-system,"PingFang HK","Noto Sans TC",sans-serif;
--mono:"Geist Mono",ui-monospace,monospace}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--body);font-size:12px}
::selection{background:var(--ink);color:var(--bg)}
.plate{width:1600px;margin:0 auto;padding:32px 56px 24px}
a{color:inherit}
.plate-head{display:grid;grid-template-columns:1fr auto;align-items:start;gap:24px}
.title h1{font-family:var(--display);font-size:22px;font-weight:500;margin:0;line-height:1.1}
.title .zh{margin:6px 0 0;color:var(--ink2);font-size:12px}
.meta{text-align:right;color:var(--ink2);font-family:var(--mono);font-size:11px;line-height:1.7}
.rule{border:0;border-top:1px solid var(--ink);margin:16px 0 0}
.statement{display:grid;grid-template-columns:380px 420px 1fr;gap:40px;align-items:start;margin:20px 0 24px}
.hero{font-family:var(--display);font-size:92px;font-weight:500;line-height:1;letter-spacing:-.02em}
.deck{color:var(--ink2);line-height:1.55;font-size:12px;margin:0}
.deck.zh{line-height:1.75;font-family:var(--body)}
.caption{font-family:var(--mono);font-size:11px;font-weight:400;color:var(--ink2);margin:0 0 12px}
.charts{display:grid;grid-template-columns:1fr 464px;gap:80px;align-items:start}
.stage1-chart{display:grid;grid-template-columns:8px 240px 1fr 64px 56px;column-gap:8px}
.source{background:var(--ink);grid-row:1 / span 7}
.band-row{display:contents}
.band{height:var(--band-h);background:var(--fill)}
.band-label{display:flex;flex-direction:column;justify-content:center;gap:2px;position:relative;padding-left:36px}
.band-label::before{content:"";position:absolute;left:0;top:50%;width:28px;height:1px;background:var(--line)}
.band-label .en{font-size:13.5px;font-weight:500}
.band-label .zh{font-size:11px;color:var(--ink2)}
.band-count,.band-share{align-self:center;text-align:right;font-family:var(--mono)}
.band-count{font-size:12px}
.band-share{font-size:11px;color:var(--ink2)}
.trad-chart{position:relative;height:320px;display:grid;grid-template-columns:8px 150px 1fr;column-gap:8px}
.trad-source{background:var(--ink);height:300px}
.trad-bands{position:relative;height:300px}
.trad-band{position:absolute;left:0;width:150px;background:var(--fill);height:var(--trad-h);box-shadow:inset 0 0 0 1px rgba(23,23,26,.16)}
.trad-labels{position:relative}
.trad-label{display:flex;align-items:center;gap:8px;white-space:nowrap}
.trad-label .swatch{width:8px;height:8px;background:var(--fill);flex:none;box-shadow:inset 0 0 0 1px rgba(23,23,26,.16)}
.trad-label .name{font-size:12px}
.trad-label .n{font-family:var(--mono);font-size:12px;color:var(--ink);margin-left:auto}
.trad-label.lead{position:absolute;left:0;display:block;white-space:normal;transform:translateY(-50%)}
.trad-label.lead .name{font-size:13.5px;font-weight:500;display:block}
.trad-label.lead .sub{font-size:11px;color:var(--ink2);display:block;margin-top:2px}
.trad-legend{position:absolute;left:0;width:100%;display:flex;flex-direction:column;align-items:flex-start;gap:4px}
.trad-legend .trad-label{width:100%}
.trad-legend-head{font-family:var(--mono);font-size:11px;color:var(--ink2);margin-bottom:2px}
.trad-note{font-size:12px;color:var(--ink2);margin:8px 0 0;line-height:1.5}
.stage3{margin-top:22px;border-top:1px solid var(--ink);padding-top:12px}
.denom-strip{display:flex;height:24px;margin:6px 0 12px}
.denom-strip span{display:block;height:24px;background:var(--fill)}
.denom-list{display:grid;grid-template-rows:repeat(7,auto);grid-auto-flow:column;column-gap:24px;row-gap:3px;margin:0;padding:0;list-style:none}
.denom-list li{display:grid;grid-template-columns:1fr 52px;gap:8px;font-size:11px}
.denom-list .n{font-family:var(--mono);text-align:right}
.schedule-wrap{display:grid;grid-template-columns:1fr 1fr;column-gap:48px;margin-top:28px;border-top:1px solid var(--ink);padding-top:10px}
table.schedule{width:100%;border-collapse:collapse;font-size:12px;table-layout:fixed}
table.schedule caption{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
table.schedule th{font-family:var(--mono);font-size:11px;font-weight:400;color:var(--ink2);text-align:left;padding:0 0 6px;border-bottom:1px solid var(--ink)}
table.schedule th.num{text-align:right}
table.schedule th .zh{display:block;font-family:var(--body);font-size:11px}
table.schedule td{padding:5px 0;border-bottom:1px solid var(--line)}
td.rank,td.count,td.share{font-family:var(--mono);text-align:right;color:var(--ink2);font-size:11px}
td.name{color:var(--ink)}
td.count{color:var(--ink);font-size:12px;width:64px}
td.rank{width:24px;text-align:left}
td.share{width:48px}
.foot{margin-top:18px;border-top:1px solid var(--ink);padding-top:10px;display:grid;grid-template-columns:1fr auto;gap:24px}
.foot .source-line,.foot .imprint{font-family:var(--mono);font-size:11px;color:var(--ink2)}
.foot .note{font-size:12px;color:var(--ink2);line-height:1.5;margin:6px 0 0;max-width:1100px}
.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0}
.imprint{text-align:right;align-self:end}
@media print{body{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
"""


FONT_FACE = """
@font-face{font-family:"Bricolage Grotesque";src:url(fonts/bricolage-grotesque.woff2) format("woff2");font-weight:400 500;font-display:swap}
@font-face{font-family:"DM Sans";src:url(fonts/dm-sans.woff2) format("woff2");font-weight:400 500;font-display:swap}
@font-face{font-family:"Geist Mono";src:url(fonts/geist-mono.woff2) format("woff2");font-weight:400 500;font-display:swap}
"""


def fmt(number: int) -> str:
    return f"{number:,}"


def render(data: dict) -> str:
    def band_rows() -> str:
        rows = []
        for row, fill in zip(data["stage1"], STAGE1_FILLS):
            rows.append(
                f'<div class="band-row">'
                f'<div class="band" style="--band-h:{row["height"]}px;--fill:var(--{fill})"></div>'
                f'<div class="band-label"><span class="en">{escape(row["en"])}</span>'
                f'<span class="zh" lang="zh-Hant">{escape(row["zh"])}</span></div>'
                f'<div class="band-count">{fmt(row["count"])}</div>'
                f'<div class="band-share">{row["share"]:.1f}%</div>'
                f"</div>"
            )
        return "".join(rows)

    def trad_offsets() -> list[int]:
        tops, top = [], 0
        for row in data["traditions"]:
            tops.append(top)
            top += row["height"]
        return tops

    def trad_bands() -> str:
        return "".join(
            f'<div class="trad-band" style="top:{top}px;--trad-h:{row["height"]}px;--fill:var(--{fill})"></div>'
            for row, top, fill in zip(data["traditions"], trad_offsets(), TRADITION_FILLS)
        )

    def trad_labels() -> str:
        fills = TRADITION_FILLS
        tops = trad_offsets()
        lead, rest = data["traditions"][0], data["traditions"][1:]
        out = [
            f'<div class="trad-label lead" style="top:{tops[0] + lead["height"] // 2}px;--fill:var(--{fills[0]})">'
            f'<span class="name">{escape(lead["en"])}</span>'
            f'<span class="sub" lang="zh-Hant">{escape(lead["zh"])} · {fmt(lead["count"])}</span></div>'
        ]
        out.append(
            f'<div class="trad-legend" style="top:{tops[0] + lead["height"] + 12}px">'
            '<div class="trad-legend-head">Other traditions · 其餘傳統</div>'
        )
        for index, row in enumerate(rest):
            out.append(
                f'<div class="trad-label" style="--fill:var(--{fills[index + 1]})">'
                f'<span class="swatch"></span><span class="name">{escape(row["en"])} · '
                f'<span lang="zh-Hant">{escape(row["zh"])}</span></span>'
                f'<span class="n">{fmt(row["count"])}</span></div>'
            )
        out.append("</div>")
        return "".join(out)

    def denom_strip() -> str:
        rows = data["denominations"]
        top, tail = rows[:6], rows[6:]
        segments = [(row, fill) for row, fill in zip(top, DENOMINATION_FILLS)]
        if tail:
            segments.append(
                (
                    {"en": f"{len(tail)} smaller denominations", "count": sum(row["count"] for row in tail)},
                    DENOMINATION_FILLS[len(top)],
                )
            )
        total = data["denomination_total"]
        return "".join(
            f'<span style="width:{row["count"] / total * 100:.2f}%;--fill:var(--{fill})" '
            f'title="{escape(row["en"])}: {fmt(row["count"])}"></span>'
            for row, fill in segments
        )

    def denom_rows() -> str:
        return "".join(
            f'<li><span>{escape(row["en"])}</span><span class="n">{fmt(row["count"])}</span></li>'
            for row in data["denominations"]
        )

    def schedule(rows, start: int, total_rows: int) -> str:
        body = "".join(
            f'<tr class="sched-row"><td class="rank">{start + index:02d}</td>'
            f'<td class="name">{escape(row["en"])} · <span lang="zh-Hant">{escape(row["zh"])}</span></td>'
            f'<td class="count">{fmt(row["count"])}</td><td class="share">{row["share"]:.1f}%</td></tr>'
            for index, row in enumerate(rows)
        )
        return (
            f'<table class="schedule"><caption>{total_rows} purposes, ranked</caption>'
            '<colgroup><col style="width:24px"><col><col style="width:68px"><col style="width:64px"></colgroup>'
            '<thead><tr><th scope="col"><span aria-hidden="true">#</span><span class="sr-only">Rank</span></th><th scope="col">Purpose 用途</th>'
            '<th class="num" scope="col">Count<span class="zh">數目</span></th>'
            '<th class="num" scope="col">Share<span class="zh">比例</span></th></tr></thead>'
            f"<tbody>{body}</tbody></table>"
        )

    purposes = data["purposes"]
    band = fmt(data["religious_band"])
    if data["religious_unclassified"]:
        en_relig = (
            f"Of the {band} religious societies, {fmt(data['religious_total'])} carry a faith "
            f"classification; those resolve again into {data['tradition_count']} traditions and "
            f"{data['denomination_count']} Protestant groupings."
        )
        zh_relig = (
            f"{band} 間宗教社團中，{fmt(data['religious_total'])} 間有信仰分類，"
            f"再分為 {data['tradition_count']} 個傳統，其中基督新教再分為 {data['denomination_count']} 個教派。"
        )
    else:
        en_relig = (
            f"Those {band} religious societies resolve again into {data['tradition_count']} "
            f"traditions and {data['denomination_count']} Protestant groupings."
        )
        zh_relig = (
            f"其中{band}間宗教社團，再分為 {data['tradition_count']} 個傳統，"
            f"其中基督新教再分為 {data['denomination_count']} 個教派。"
        )

    stage2_block = ""
    if data["traditions"]:
        lead = data["traditions"][0]
        stage2_block = f'''<section aria-labelledby="cap-stage2">
<h2 class="caption" id="cap-stage2">Stage 2 · Traditions within {fmt(data["religious_total"])} · 信仰傳統</h2>
<div class="trad-chart" aria-hidden="true">
<div class="trad-source"></div>
<div class="trad-bands">{trad_bands()}</div>
<div class="trad-labels">{trad_labels()}</div>
</div>
<ul class="sr-only">{"".join(f"<li>{escape(row['en'])}: {fmt(row['count'])}</li>" for row in data["stage2_full"])}</ul>
<p class="trad-note">{lead["en"]} holds {lead["share"]:.1f}% of the {fmt(data["religious_total"])} classified religious societies — and {lead["count"] / data["total"] * 100:.1f}% of the register.</p>
</section>'''

    stage3_block = ""
    if data["denominations"]:
        stage3_block = f'''<section class="stage3" aria-labelledby="cap-stage3">
<h2 class="caption" id="cap-stage3">Stage 3 · {data["denomination_count"]} Protestant groupings within {fmt(data["denomination_total"])} · 基督新教分組</h2>
<div class="denom-strip" aria-hidden="true">{denom_strip()}</div>
<ul class="denom-list">{denom_rows()}</ul>
</section>'''
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=1600">
<title>The register, resolved · Section 88</title>
<style>{FONT_FACE}{CSS}</style>
</head>
<body>
<main class="plate">
<header class="plate-head">
<div class="title"><h1>The register, resolved</h1><p class="zh" lang="zh-Hant">登記冊，分流</p></div>
<div class="meta">As at {data["as_at"]} · 截至{data["as_at_zh"]}<br>IRD s88list.csv · 稅務局登記冊</div>
</header>
<hr class="rule">
<section class="statement">
<div class="hero">{fmt(data["total"])}</div>
<p class="deck">Every society on the register resolves into one of {len(data["purposes"])} purposes. {en_relig} Band height is the number of societies — never a share of a share.</p>
<p class="deck zh" lang="zh-Hant">登記冊上的每一間社團，最終都歸入 {len(data["purposes"])} 個用途之一。{zh_relig}色帶的高度就是社團數目，不是比例。</p>
</section>
<div class="charts">
<section aria-labelledby="cap-stage1">
<h2 class="caption" id="cap-stage1">Stage 1 · Purposes · 用途</h2>
<div class="stage1-chart" aria-hidden="true">
<div class="source"></div>
{band_rows()}
</div>
</section>
<div class="stage-col">
{stage2_block}
{stage3_block}
</div>
</div>
<section class="schedule-wrap">
{schedule(purposes[:9], 1, len(purposes))}
{schedule(purposes[9:], 10, len(purposes))}
</section>
<footer class="foot">
<div>
<div class="source-line">Source · IRD s88list.csv · as at {data["as_at"]} · {fmt(data["total"])} entries · 資料來源：稅務局 s88list.csv，截至{data["as_at_zh"]}，共{fmt(data["total"])}間機構</div>
<p class="note">Band height = number of societies. Stage 2 shows the religious branch only. Purposes are machine-assigned by keyword rules with an LLM tie-break; faith and community labels are inferred from organisation names. Treat every classification as a lead, not a finding.</p>
<p class="note" lang="zh-Hant">色帶高度即社團數目；第二層僅繪宗教一支。用途由關鍵詞規則及語言模型自動分類，信仰與社群標籤由機構名稱推斷，只宜視作線索。</p>
</div>
<div class="imprint">Curious Gold · Plate 05</div>
</footer>
</main>
</body>
</html>
"""


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    allow_incomplete = "--allow-incomplete" in args
    root = pathlib.Path(__file__).resolve().parent
    try:
        data = aggregate(root)
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    problems = []
    if data["religious_unclassified"]:
        problems.append(
            f"{data['religious_unclassified']} religious societies have no faith label — "
            "regenerate sub_religion.csv with `classify_sub.py religion`"
        )
    if data["community_unclassified"]:
        problems.append(
            f"{data['community_unclassified']} community societies have no community label — "
            "regenerate sub_community.csv with `classify_sub.py community`"
        )
    if problems and not allow_incomplete:
        for problem in problems:
            print(f"ERROR: {problem}", file=sys.stderr)
        print("Refusing to write dist/. Fix the inputs or pass --allow-incomplete.", file=sys.stderr)
        return 2
    for problem in problems:
        print(f"WARNING: {problem}", file=sys.stderr)

    out = root / "dist"
    out.mkdir(exist_ok=True)
    (out / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "index.html").write_text(render(data), encoding="utf-8")
    shutil.copytree(root / "assets" / "fonts", out / "fonts", dirs_exist_ok=True)
    print(f"wrote {out/'index.html'} and {out/'data.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
