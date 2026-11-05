# Stage 1 purposes

Stage 1 is the first claim on the page: the register splits into purpose bands, each band's height being the number of societies in it, with the count and share printed beside the label. Six purposes get their own band and the remainder collapses into one "other" band.

## Sub-features

- `stage1-bands` draws one band per row in `data["stage1"]`.
- `stage1-counts` prints each band's society count.
- `stage1-shares` prints each band's share of the register to one decimal.
- `stage1-order` keeps bands in descending count order, with the collapsed band last.

## How to get to it (user POV)

- Open the site; Stage 1 is the left column of the chart block, headed "Stage 1 · Purposes · 用途".

## Driving it with omp browser

Preconditions: doctor passes; `dist/data.json` copied to evidence.

- Read the heading: `await tab.text("#cap-stage1")` → `Stage 1 · Purposes · 用途`.
- Count bands: `await tab.count(".stage1-chart .band-row")` → equals `len(stage1)` in `data.json` (7 today: six purposes plus the collapsed band).
- Read each pair: `await tab.run` over `.stage1-chart .band-row` collecting `.band-label .en`, `.band-count`, `.band-share` → the i-th `.band-count` equals `fmt(stage1[i].count)` and `.band-share` equals `stage1[i].share.toFixed(1) + "%"`.
- Check the collapsed band: the last `.band-row .band-label .en` starts with `Other` and its count equals the sum of the remaining purposes the build collapsed.
- Check band geometry: `await tab.styles(".stage1-chart .band-row:nth-child(3) .band", ["--band-h"])` → the inline `--band-h` is a positive px value proportional to that band's count.
- Screenshot the whole chart column as `plate-stage1.png`.

## Gotchas

- `.band-row` sits inside `.stage1-chart`, which is `aria-hidden="true"`; `ariaSnapshot` will not list these rows.
- Band heights are inline `--band-h` px values computed from the data, not percentages of the largest band — comparing them to shares fails.
- The "other" band aggregates several purposes; its count is not a single entry in `purposes` but the sum of everything past the top six, so assert the sum, not a lookup.
- Shares are rounded to one decimal and do not sum to exactly 100%; assert individual shares, never the total.
- The band fill colours come from `STAGE1_FILLS`; a colour change is not a data regression, so never assert colour as proof of correctness.
