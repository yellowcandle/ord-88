# Shipped plate — visual system

The shipped page is a 1600 px print-style plate built by `build_site.py`. It is
not the amber/indigo interactive explorer described in `DESIGN.md`.

## Type

| Role | Family | Where |
| --- | --- | --- |
| Display | Bricolage Grotesque | hero total, page title |
| Body | DM Sans (PingFang HK / Noto Sans TC fallback) | labels, prose, tables |
| Mono | Geist Mono | counts, shares, metadata, captions |

Fonts are self-hosted in `assets/fonts/` and copied to `dist/fonts/` by the
build. There is no network font request.

## Colour

| Token | Value | Use |
| --- | --- | --- |
| `--ink` | `#17171A` | text, rules, source bar |
| `--ink2` | `#5C5A56` | secondary text |
| `--line` | `#E4E1DE` | dividers |
| `--bg` | `#FFFFFF` | page |
| `--r1` … `--r7` | `#8C3A1E` → `#DDA986` | purpose and tradition bands (dark → light) |
| `--n1` … `--n5` | `#23211E` → `#C2BDB6` | neutral bands and legend swatches |

Bands are solid fills; no gradients, side stripes or shadows. Counts and shares
sit in a right-aligned ledger column.

## Layout

The plate is a fixed 1600 px canvas (`<meta name="viewport" content="width=1600">`)
for print and screenshot review. Stage 1 shows six purposes plus a merged tail;
Stage 2 shows four traditions plus a merged tail; Stage 3 lists every Protestant
grouping. The ranked schedule lists every purpose in two columns.

## Verification

`.omp/skills/verify-plate/` drives the built page over HTTP in a real browser and
records screenshots plus assertions against `dist/data.json`. Use it when a change
touches `build_site.py`, the classification CSVs or `dist/`.
