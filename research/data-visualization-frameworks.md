# Data visualisation frameworks — selection research

*2026-11-03 · scope: the Interactive Charity Explorer in `DESIGN.md` — 17,591 HK Section-88 charities, bilingual EN/繁中, amber/indigo OKLCH design system, static hosting assumed.*

## Verdict

Aggregate in Python at build time, render client-side, and pick the chart library by how much interaction the explorer actually needs:

| If the explorer is… | Use | Why |
|---|---|---|
| One static page, three charts, cards, search (current DESIGN.md scope) | **ECharts 6.1** (~200 kB gz) | Tooltip/dataZoom/brush built in, ARIA description + decal patterns, SVG SSR, Apache-2.0 |
| Simple marks, hand-built interaction, minimal payload | **D3 7 subset** (~21 kB gz) | Smallest total JS; you build axes polish, tooltips, a11y |
| A multi-route React app with component reuse | **Recharts 3** (~110 kB gz) | Ergonomic composition, SVG-only, a11y layer default in v3, MIT |
| Chart definitions must stay in Python | **Altair → Vega-Lite + vega-embed** (~285 kB gz) | Spec export, `vl-convert` static export; JSON theming, no CSS vars |
| Maintainers are Python-first, pages are report-like | **Observable Framework + Plot** (~205 kB gz page) | Native `.py` data loaders, static build, `Inputs` search/table; Markdown cells instead of components, no i18n/`lang` support |

Rejected for this dataset: **Plotly** (1.46 MB gz before any figure code), **Python servers** (Streamlit/Dash cannot be statically hosted; Bokeh/Panel drag a 389 kB gz runtime plus a process), **WASM query engines** (Perspective 623 kB, DuckDB 8 MB gz cold start for a 2 MB dataset), **deck.gl** (no 17.5k-mark view except a future map).

## What actually decides it

Measured on this repo: `s88list_categorised.csv` is 1,971,148 B / 17,592 lines; `s88list.csv` 2.5 MB (324 kB gz). But the charts are **17 categories, 13 religions, 8 community labels** — 17–20 marks each. The three pre-aggregated payloads are **510 B, 112 B, 102 B gzipped**; all 17,591 rows with `code/en/zh/date` are 320,986 B gzipped. Nothing here needs a query engine, windowing, downsampling or WebGL.

The real constraints are fidelity to `DESIGN.md` (OKLCH amber `#DCA043` / indigo `#4E5A99`, Playfair+Inter, flat cards), CJK text, keyboard/screen-reader access, `prefers-reduced-motion`, and staying statically hostable.

## Rendering engines and grammars

**D3 7.9.0** (2024-03-12, ISC) is primitives plus a data join, not a chart library: `selection.join(enter, update, exit)` ([docs](https://d3js.org/d3-selection/joining)), scales, shape generators, axes. SVG or Canvas is your choice; axes are cheap, legends/tooltips/focus rings/keyboard nav/brush are yours. It generates **no** ARIA. There is no v8 — dist-tags are `latest: 7.9.0`. The scale+axis+shape subset bundles to **21.0 kB gz**; importing all of `d3` is 94.1 kB gz.

**Vega-Lite 6.5.0 → Vega 6.4.0** (BSD-3) is a declarative grammar compiled to Vega ([params](https://vega.github.io/vega-lite/docs/parameter.html)). Interaction is selections/params (`select: "interval", bind: "scales"`) rather than event handlers. Static export is the best in class: `vl-convert` (Rust, embeds official JS, no browser) emits SVG/PNG/PDF ([vl-convert](https://github.com/vega/vl-convert)). Two caveats: `vega-embed` 7.3.0 defaults to the **SVG** renderer, and Vega-Lite's ARIA tree is **SVG-only** ([v6 schema](https://vega.github.io/schema/vega-lite/v6.json)) — choosing canvas at scale silently drops it. Theming is a JSON `config`; runtime cost 285.3 kB gz.

**Observable Plot 0.6.17** (ISC) is a layered grammar over D3 with first-class faceting. It is **SVG-first** (`createElementNS` in [`src/plot.js`](https://github.com/observablehq/plot/blob/main/src/plot.js)); canvas only rasterises `raster`/`contour` marks. 17.5k dots would be 17.5k nodes. Root gets `aria-label`/`aria-description`, marks are real shapes — better than most on a11y. Still 0.x after five years (0.6.18-alpha.2 on 2026-11-02). 88.6 kB gz for the bar/rule subset, 133.7 kB for the namespace.

**ECharts 6.1.0** (Apache-2.0, ASF-governed) is Canvas by default, SVG opt-in, and has the deepest built-in interaction set: tooltip, legend toggle, `dataZoom`, `brush`, `dispatchAction` ([canvas vs svg](https://echarts.apache.org/handbook/en/best-practices/canvas-vs-svg/)). i18n is real: `registerLocale()` with 27 shipped locales, but `langZH` (Simplified) and **no `zh-TW`/`zh-HK`** — Hong Kong labels need a custom locale or no library UI strings ([API](https://echarts.apache.org/en/api.html)). A11y is opt-in but substantive: generated `aria` description plus `aria.decal` pattern fills as a non-colour encoding for 13 religions ([aria](https://echarts.apache.org/handbook/en/best-practices/aria/)). Server rendering is first-class (`ssr: true`, `renderToSVGString()`). Cost: **200.5 kB gz** with bar+line+pie, grid/title/tooltip/legend, canvas+SVG renderers.

**Chart.js 4.6.1** (MIT) is Canvas-only, tree-shaken through `Chart.register(...)`. 53.3 kB gz for bar + category/linear scales + tooltip + legend. Custom *marks* require a `DatasetController` and element class ([docs](https://www.chartjs.org/docs/latest/developers/charts.html)); no faceting, no zoom without a plugin. A11y is entirely user-supplied ([accessibility](https://www.chartjs.org/docs/latest/general/accessibility.html)).

**uPlot 1.6.32** (MIT) is deliberately narrow: numeric/temporal x only, no category layout, no animations, no ARIA, no pan ([non-features](https://github.com/leeoniya/uPlot#non-features)). 22.6 kB gz. Wrong tool for categorical splits; right only if a time dimension appears.

**deck.gl 9.4.1** (MIT) is WebGL2/WebGPU with a picking engine ([interactivity](https://deck.gl/docs/developer-guide/interactivity)); 220.7 kB gz, no SSR, pointer-only picking. Justified only if "show origins" becomes a map or per-org 60 fps points.

## Component libraries and app-scale tooling

**Recharts 3.10.1** (MIT) renders React trees to pure SVG — mark count equals DOM node count. v3 made `accessibilityLayer` default (Tab in, arrow keys) and added portals, but a custom mark "must still be renderable within an SVG" ([v3 release](https://github.com/recharts/recharts/releases/tag/v3.0.0)). Despite "minimal dependencies", it ships 12 runtime deps including Redux Toolkit and `victory-vendor`; measured 109.8 kB gz with React external.

**visx 4.0.0** (MIT) is primitives per package, explicitly "not a charting library". 24.9 kB gz for bar+group+scale+axis; legends, responsive containers, tooltips and a11y are yours. Best fidelity/perf ratio if you accept building the chart.

**Nivo 0.99.0** (MIT) is pre-1.0 and ~17 months stale; `@nivo/core` pulls lodash, react-spring, an auto-sizer and six d3 modules. 101.1 kB gz for a bar chart.

**MUI X Charts 9.17.0** — package MIT, but the tiers are the decision ([licensing](https://mui.com/x/introduction/licensing/)): Community = bar/line/pie/scatter + axes/legends/tooltips; Pro ($299/dev/yr) = funnel/heatmap/sankey/radar, zoom/pan, export; Premium ($599) = WebGL, candlestick, annotations. Everything here is Community; keyboard nav and reduced-motion are on by default ([a11y](https://mui.com/x/react-charts/accessibility/)). 148.3 kB gz, plus MUI's theming stack.

**TanStack Table 9.3.1** (MIT) is headless row models with v9 feature tree-shaking ([docs](https://tanstack.com/table/latest/docs/guide/tables)); 28.5 kB gz. Virtualisation is separate (`@tanstack/react-virtual`). **AG Grid 36.2.0** Community is MIT and virtualises by default, but the licence boundary bites: Set/Multi Filter, aggregation, grouping and Excel/PDF export are **Enterprise**, and the online licence covers internal apps only ([pricing](https://www.ag-grid.com/license-pricing/)). Note `@ag-grid-community/*` scoped packages are frozen at 32.3.9 — stale-tutorial trap.

**App-scale options don't pay off here.** Perspective (WASM, 623 kB cold start) and Mosaic+DuckDB (`duckdb-eh.wasm` 8.05 MB gz; threading needs COOP/COEP, which GitHub Pages cannot set) exist to push filtering into an engine over data too big to ship. This data is 321 kB gz. Observable Framework's build-time data loaders are the right *idea* — precompute snapshots, ship static files — without needing the framework. Plain static JSON plus a JS filter is sub-millisecond at 17.5k rows.

## Python side, and what the repo already does

`make_report.py` draws one `barh` (`#3b6ea5`, dpi 150) from `category_counts.json`; `make_report2.py` factors `barchart(counts, namemap, title, fn, color)` and emits religion (`#8a5a44`) and community (`#44708a`) charts. Three concrete defects: the palette is hardcoded and matches **none** of DESIGN.md's tokens; the font probe is macOS-only (`PingFang HK`, `Heiti TC`…) and swallows failures with `except Exception: pass`, so on Linux/CI the two bilingual charts render 繁體中文 as tofu while the build stays green; and there is no ARIA beyond one image `alt`.

Fix the font probe with Matplotlib's per-glyph fallback list (≥3.6, [docs](https://matplotlib.org/stable/users/explain/text/fonts.html)): `["Playfair Display","Inter","Noto Sans CJK TC","DejaVu Sans"]`, with the CJK face actually installed.

Python beyond matplotlib:
- **Plotly 7.1.0** — `to_html(include_plotlyjs=...)` inline is ~3 MB; the library itself is **1.49 MB gz** ([dist README](https://github.com/plotly/plotly.js/blob/master/dist/README.md)). Fine for one-off analyst HTML, wrong for a public page.
- **Altair 6.3.0** — emits Vega-Lite JSON; PNG/SVG export needs `vl-convert` (`altair_saver` is dead) ([docs](https://altair-viz.github.io/user_guide/saving_charts.html)). Runtime ≈283 kB gz, or compile to Vega at build time and drop vega-lite.
- **Bokeh 3.10.1** — `file_html()` gives portable interactive HTML ([docs](https://docs.bokeh.org/en/latest/docs/user_guide/output/embed.html)) at 389 kB gz, but Python callbacks imply a server.
- **Streamlit / Dash** require a running server ([Streamlit](https://docs.streamlit.io/deploy/concepts), [Dash](https://dash.plotly.com/deployment)). **Shinylive** is the exception — Pyodide in the browser, static-hostable, multi-MB cold start ([py-shinylive](https://github.com/posit-dev/py-shinylive)).

## Measured payloads

Method: npm latest as of 2026-11-03, installed in a scratch project, bundled with esbuild 0.28.2 (`--bundle --minify --format=esm`, React external), gzip level 9. Entry points are the minimal realistic import for one bar chart plus tooltip; `echarts-full` and `chartjs` (`/auto`) are unoptimised baselines.

| Entry | min | gzip |
|---|---:|---:|
| uPlot (full) | 50.8 KiB | 22.6 KiB |
| d3 (select, scaleBand/Linear, axes) | 60.2 KiB | **21.0 KiB** |
| visx (shape, group, scale, axis) | 77.0 KiB | **24.9 KiB** |
| Chart.js (bar + scales + tooltip + legend) | 153.5 KiB | 53.3 KiB |
| Chart.js `/auto` | 200.9 KiB | 69.1 KiB |
| Observable Plot (barY + ruleY) | 260.0 KiB | 88.6 KiB |
| Observable Plot (namespace) | 392.5 KiB | 133.7 KiB |
| Recharts (bar + axes + tooltip + responsive) | 373.9 KiB | 109.8 KiB |
| Nivo bar | 303.0 KiB | 101.1 KiB |
| MUI X Charts bar | 458.8 KiB | 148.3 KiB |
| ECharts (bar/line/pie, grid/title/tooltip/legend, canvas+svg) | 583.3 KiB | **200.5 KiB** |
| ECharts (namespace) | 1113.7 KiB | 373.9 KiB |
| Vega-Lite (compiler) | 756.9 KiB | 261.7 KiB |
| vega-embed (Vega + Vega-Lite + editor glue) | 823.1 KiB | 285.3 KiB |
| plotly.js dist | 4728.0 KiB | 1456.3 KiB |

Reference points: React + ReactDOM add ~45 kB gz on top of any React library; the full 17,591-row dataset is 321 kB gz.

## Theming trap: OKLCH is not parseable by most chart engines

Verified locally against the installed packages:

| Parser | `#DCA043` | `oklch(0.7 0.12 80)` |
|---|---|---|
| `d3.color()` | object | `null` |
| `@kurkle/color` (Chart.js) | `{r:220,g:160,b:67,a:1}` | no `.rgb` |
| `zrender` colour `parse()` (ECharts) | `[220,160,67,1]` | `undefined` |

Consequences: SVG attribute/CSS paths (D3 fills, Plot's `currentColor`, raw SVG) accept `oklch()`; Canvas and WebGL paths (ECharts, Chart.js, deck.gl) need tokens resolved to sRGB before they reach the library, because hover/emphasis colours are derived by parsing. DESIGN.md is written in OKLCH, so the build needs one conversion step (e.g. `culori` in a token script) that emits both `--token-*` CSS vars and a hex palette — never two hand-maintained palettes.

## Recommendation

1. **Build step:** `make_site_data.py` emits `data/{categories,religion,community}.json` (≈1 kB total) plus a sharded org index from `s88list_categorised.csv`. Aggregation is a pure function of an immutable CSV; there is no user-composed query to serve at runtime.
2. **Render step:** static HTML/ESM, no framework, ECharts 6 with a generated hex theme and a `zh-HK` locale. Enable `aria` + `aria.decal`, set `animation: false` under `prefers-reduced-motion`, and render the underlying table for each chart. Adds ~200 kB gz, no server, no build framework.
3. **Alternatives, and when each wins:** D3 subset (21 kB) if the charts stay at "horizontal bar + labels" and you will hand-build tooltips/focus/a11y; React + Recharts (110 kB + ~45 kB React) if the explorer grows routes, reusable cards and shared filter state. Vega-Lite only if Python must own the chart specs.
4. **Keep the PNGs** for `s88_report.md` / PDF / no-JS readers, with the font and palette fixes above.

Before committing, verify: ECharts `zh-HK` locale coverage; the token→hex conversion's gamut mapping (amber is high-chroma); keyboard path on bar selection; and that DESIGN.md's muted/surface tokens survive as chart grid/axis colours at 3:1 contrast.

## Observable Framework, tested

Built a real project against this repo's data (Framework 1.13.4, ISC, Node ≥18; three `.py` data loaders reading the CSVs, ECharts + Plot charts, `Inputs.search` over 17,591 rows). Output is fully static and served correctly from `python3 -m http.server`; no special headers.

Measured:

| Metric | Value |
|---|---|
| Framework runtime + client + stdlib | 26 KiB gz |
| Observable Plot (built-in import) | 67 KiB gz |
| d3 modules pulled transitively | 110 KiB gz |
| ECharts via `npm:echarts@6` | **375 KiB gz** (full bundle, not tree-shaken) |
| Page JS, Plot only | **205 KiB gz** |
| Page JS, Plot + ECharts | **581 KiB gz** |
| Modulepreloads on first load | 41 (the full 580 KiB, including the below-fold chart) |
| `dist/` total | 2.6 MB — 1.95 MB is the org CSV snapshot |
| `index.html` | 9.6 KB, no prerendered content |

What works well: `.py` loaders are first-class (no glue), snapshots cached in `.observablehq/cache`, `Inputs.search` + `Inputs.table` handle 17.5k rows with 24-row pagination, build ≈5 s incremental, and the GitHub Pages workflow is a copy-paste recipe ([deploying](https://observablehq.com/framework/deploying)). CJK rendered correctly in both Plot and ECharts SVG output.

What costs you:
- **No tree-shaking for `npm:` imports.** `npm:echarts@6` ships the full 1.09 MB ESM bundle. Subpath imports (`npm:echarts@6/core`, `/charts`, …) are worse — Framework bundles each entry separately, duplicating core and zrender (5 chunks, 1.39 MB raw). Node imports (`echarts/core` from `node_modules`) also duplicate: 98 chunks, 3.9 MB raw, 1358 KiB gz. ECharts in Framework means accepting ~375 KiB gz.
- **Views vs values is a real sharp edge.** `Inputs.search(rows)` returns a *view*; passing it to `Inputs.table` yields empty rows until you bind `Generators.input(searchInput)`. Program blocks (`;`) do not display — the input never appears. I hit both.
- **No i18n and no `<html lang>`.** There is no `lang` config option, the built `<html>` tag has none, and the client never reads `URLSearchParams` — URL-addressable filter state is manual. A EN/繁中 toggle means separate pages or hand-rolled re-render logic.
- **Only nine `--theme-*` variables, and the default stylesheet loads Source Serif 4 from Google Fonts** ([config](https://observablehq.com/framework/config#globalstylesheets)); overriding `globalStylesheets`/`style` is required to honour DESIGN.md's Playfair+Inter and to avoid a third-party font request.
- **Authoring is Markdown + reactive cells**, not components. A bespoke card layout is `html` templates and CSS, and per-cell reasoning replaces a component tree.

Fit: the cheapest path from this Python repo to an interactive static explorer, and the right choice if the maintainers are data/Python people writing report-like pages. It is not a design system: DESIGN.md fidelity, bilingual switching and OKLCH chart theming remain manual work either way, so a plain Vite + ECharts page (~200 KiB gz, full control) is the better fit if brand fidelity dominates.

## Sources

- npm metadata (`npm view <pkg> version time license dependencies`, `registry.npmjs.org`) for every version above; local bundles measured 2026-11-03.
- D3: https://d3js.org/d3-selection/joining · https://d3js.org/d3-shape · https://d3js.org/d3-axis
- Vega: https://vega.github.io/vega-lite/docs/parameter.html · https://vega.github.io/schema/vega-lite/v6.json · https://github.com/vega/vl-convert · https://github.com/vega/vega-embed#readme
- Plot: https://observablehq.com/plot/ · https://github.com/observablehq/plot/blob/main/src/plot.js
- ECharts: https://echarts.apache.org/en/api.html · https://echarts.apache.org/handbook/en/best-practices/aria/ · https://echarts.apache.org/handbook/en/best-practices/canvas-vs-svg/ · https://echarts.apache.org/handbook/en/how-to/cross-platform/server/
- Chart.js: https://www.chartjs.org/docs/latest/getting-started/integration.html · https://www.chartjs.org/docs/latest/developers/charts.html · https://www.chartjs.org/docs/latest/general/accessibility.html
- uPlot: https://github.com/leeoniya/uPlot#non-features · deck.gl: https://deck.gl/docs/developer-guide/interactivity
- Recharts: https://github.com/recharts/recharts/releases/tag/v3.0.0 · visx: https://visx.airbnb.tech/ · Nivo: https://github.com/plouc/nivo/blob/master/README.md
- MUI X: https://mui.com/x/introduction/licensing/ · https://mui.com/x/react-charts/accessibility/ · https://mui.com/pricing/
- TanStack: https://tanstack.com/table/latest/docs/guide/tables · https://tanstack.com/virtual/latest/docs/introduction · AG Grid: https://www.ag-grid.com/license-pricing/
- Mosaic: https://idl.uw.edu/mosaic/what-is-mosaic/ · DuckDB-WASM: https://duckdb.org/docs/2.0/clients/wasm/instantiation · Framework: https://observablehq.com/framework/data-loaders
- Python: https://matplotlib.org/stable/users/explain/text/fonts.html · https://plotly.com/python-api-reference/generated/plotly.io.to_html.html · https://github.com/plotly/plotly.js/blob/master/dist/README.md · https://altair-viz.github.io/user_guide/saving_charts.html · https://docs.bokeh.org/en/latest/docs/user_guide/output/embed.html · https://docs.streamlit.io/deploy/concepts · https://dash.plotly.com/deployment · https://github.com/posit-dev/py-shinylive
