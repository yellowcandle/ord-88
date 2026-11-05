# Stage 2 traditions

Stage 2 re-splits the religious branch only: one leading tradition gets a labelled band, every other tradition appears in a legend with its own count, and a note states the leader's share of the classified religious societies and of the whole register.

## Sub-features

- `stage2-heading` names the classified religious total.
- `stage2-leader` labels the leading tradition with its count.
- `stage2-legend` lists every other tradition with its count.
- `stage2-note` states the leader's two shares.

## How to get to it (user POV)

- Open the site; Stage 2 is the right column of the chart block, headed "Stage 2 · Traditions within …".

## Driving it with omp browser

Preconditions: doctor passes; `dist/data.json` copied to evidence.

- Read the heading: `await tab.text("#cap-stage2")` → starts `Stage 2 · Traditions within` and contains `fmt(religious_total)`.
- Read the leader: `await tab.text(".trad-labels .trad-label.lead .name")` → equals `traditions[0].en`; `await tab.text(".trad-labels .trad-label.lead .sub")` contains `traditions[0].zh` and `fmt(traditions[0].count)`.
- Count legend rows: `await tab.count(".trad-legend .trad-label")` → equals `len(traditions) - 1`.
- Read legend counts: `await tab.run` over `.trad-legend .trad-label` collecting `.name` and `.n` → each `.n` equals `fmt(traditions[i+1].count)` in order.
- Read the note: `await tab.text(".trad-note")` → contains `traditions[0].en`, `traditions[0].share.toFixed(1) + "%"`, `fmt(religious_total)`, and the register-wide percentage `traditions[0].count / total * 100` to one decimal.
- Screenshot the Stage 2 column as `plate-stage2.png`; the band stack and legend positions are the visual claim.

## Gotchas

- The `.trad-label.lead` selector matters: plain `.trad-label` also matches legend rows, and the lead has `.sub` while legend rows have `.n`.
- The legend is nested inside `.trad-labels` under `.trad-legend`; a bare `.trad-label` count is `len(traditions)`, one more than the legend rows.
- Stage 2's total is `religious_total`, not `religious_band`; they are equal only when no religious society lacks a faith label. When `religious_unclassified > 0` the deck text changes shape, so read the heading for the number instead of the prose.
- Band geometry uses absolute `top` and `--trad-h` inline styles; legend rows carry no geometry, so do not compare positions across the two groups.
- The `.sr-only` list after the chart also holds every tradition count; a body-text search can pass on that list while the visible labels are wrong.
