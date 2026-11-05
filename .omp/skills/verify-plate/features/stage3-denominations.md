# Stage 3 denominations

Stage 3 splits the Protestant branch once more: a proportional strip shows the six largest groupings plus a collapsed remainder, and the full list prints every grouping with its count.

## Sub-features

- `stage3-heading` states the grouping count and the Protestant total.
- `stage3-strip` draws proportional segments for the top six plus a collapsed remainder.
- `stage3-list` prints every grouping with its count.

## How to get to it (user POV)

- Open the site; Stage 3 sits under Stage 2 in the right column, headed "Stage 3 · N Protestant groupings within …".

## Driving it with omp browser

Preconditions: doctor passes; `dist/data.json` copied to evidence.

- Read the heading: `await tab.text("#cap-stage3")` → contains `denomination_count`, `fmt(denomination_total)`, and `基督新教分組`.
- Read the list: `await tab.run` over `.denom-list li` collecting the label span text and `.n` → `len` equals `len(denominations)`, and each `.n` equals `fmt(denominations[i].count)`.
- Count strip segments: `await tab.count(".denom-strip span")` → `min(6, len(denominations)) + 1` when a remainder exists.
- Check segment proportionality: `await tab.run` over `.denom-strip span` reading `style.width` → each segment's percentage equals `count / denomination_total * 100` to two decimals, and the widths sum to 100%.
- Read the collapsed segment: `await tab.attr(".denom-strip span:last-child", "title")` → `"<n> smaller denominations: <sum>"` matching the tail of `denominations`.
- Screenshot the Stage 3 block as `plate-stage3.png`.

## Gotchas

- The strip has `aria-hidden="true"` and each segment's only text is a `title` attribute; visible text assertions fail here, use `title` and `style.width`.
- The collapsed segment is always appended, even when the tail is empty — in that case its label reads `0 smaller denominations` and its count is `0`.
- `denomination_total` is the Protestant total, not the sum of the printed list; assert the list against `denominations`, and the strip widths against `denomination_total`.
- The heading count is `denomination_count` (groupings), while the heading total is a society count; reading them as the same number is the usual false failure.
