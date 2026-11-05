# Ranked schedule

The schedule is the full claim the charts summarise: every purpose, ranked, with its count and share, split across two tables so the page keeps its plate proportions.

## Sub-features

- `schedule-caption` states how many purposes are ranked.
- `schedule-rows` prints one row per purpose, rank-prefixed and in descending count order.
- `schedule-ranks` continues numbering across the two tables.
- `schedule-values` prints each purpose's count and share.

## How to get to it (user POV)

- Open the site and scroll below the charts to the ranked table block.

## Driving it with omp browser

Preconditions: doctor passes; `dist/data.json` copied to evidence.

- Count tables: `await tab.count(".schedule-wrap table.schedule")` → 2.
- Read both captions: `await tab.run` over `.schedule-wrap caption` → both read `<len(purposes)> purposes, ranked`.
- Count rows across tables: `await tab.count(".schedule-wrap .sched-row")` → equals `len(purposes)`.
- Check ranks: `await tab.run` over `.schedule-wrap .sched-row .rank` → the sequence is `01, 02, …` continuing into the second table, with no restart.
- Check values: `await tab.run` over `.schedule-wrap .sched-row` collecting `.name`, `.count`, `.share` → for row i, `.count` equals `fmt(purposes[i].count)` and `.share` equals `purposes[i].share.toFixed(1) + "%"`, in the same order as `data["purposes"]`.
- Check the boundary: the last row of the first table has rank `09` and the first row of the second has rank `10`.
- Screenshot the table block as `plate-schedule.png`.

## Gotchas

- The page renders two tables with the same caption; asserting a single caption or a single table fails.
- Ranks are zero-padded two-digit strings, so a numeric comparison of `"01"` fails.
- Row names are `English · <span lang="zh-Hant">Chinese</span>`; compare the English part, or read `.name span` separately, rather than comparing the concatenation.
- Shares come from the same rounded values as the bands; they will not sum to 100%.
- When the purpose count is at most 9 the second table is empty; then `len(purposes)` rows still hold, but the rank-boundary check has nothing to assert and must be reported as not applicable.
