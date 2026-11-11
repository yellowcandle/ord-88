# Plate verification map

This directory is the maintained source for verifying the user-facing behavior of the Section 88 plate ("The register, resolved"). Read this index before driving, then use the matching feature file as the recipe.

The page is a static build artifact: `python3 build_site.py` turns the repo's CSVs into `dist/index.html` + `dist/data.json`. There is no JavaScript, so "driving" means serving the build, loading the real page, and checking the rendered DOM against the data the build wrote.

## Baseline preconditions

- `python3 build_site.py` has run in this checkout and its stdout/stderr are captured.
- The build is served over HTTP at `http://127.0.0.1:8811` from `dist/`, as a named service `plate-verify`.
- `.omp/skills/verify-plate/scripts/doctor.sh 8811` exits 0.
- `dist/data.json` is the file the assertions compare against; copy it into the run's evidence directory first.
- Never drive an instance another run started, and never drive `file://` — serve over HTTP so the doctor's byte-identity check and the browser proof exercise the same document.

## Driving conventions

- Start every recipe from a freshly served `dist/`; a rebuild needs a restarted server only if the file changed on disk after start (the doctor catches this).
- Use CSS selectors from the table in `SKILL.md`; class names are stable template output, not hashed.
- Read values with `tab.text(sel)` and counts with `tab.count(sel)`. Do not use whole-body text search: `.sr-only` lists repeat every number and make substring checks pass for the wrong reason.
- Charts carry `aria-hidden="true"`, so `ariaSnapshot` will not show band counts. Assert on DOM text, not accessibility output.
- Treat every command as literal.
- Every number on the page is formatted with thousands separators (`17,623`), and shares are one decimal place (`4.6%`). Format expected values the same way before comparing.

## Proof and skip reporting

- Capture the rendered state and the data it came from, not only the final screen.
- UI proof includes a full-page screenshot, a viewport screenshot of the section in question, and a selector/expected/observed line per assertion.
- Include the build stdout/stderr. If `--allow-incomplete` was used, include the warning lines about unclassified societies.
- Record the feature ID and entry point used with every artifact.
- Report an unreachable path with the attempted selector and the unmet precondition.
- Do not report a section as verified because the page loaded; each section's own numbers must be checked.

## Feature entry contract

Each feature file starts with an H1 title and one paragraph describing the user-visible behavior. It then uses exactly four H2 sections in this order.

1. `Sub-features` lists short IDs with one line for each behavior.
2. `How to get to it (user POV)` lists every user entry point.
3. `Driving it with omp browser` starts with `Preconditions:` and uses labeled bullets that pair each observation with an exact call and observable result.
4. `Gotchas` lists traps that can waste or invalidate a verification run.

## Features

- [Register headline and provenance](./register-headline.md) covers the hero total, the as-at stamp, and the source line.
- [Stage 1 purposes](./stage1-purposes.md) covers the seven purpose bands, their counts, and their shares.
- [Stage 2 traditions](./stage2-traditions.md) covers the religious branch: leader band, other-tradition legend, and the share note.
- [Stage 3 denominations](./stage3-denominations.md) covers the Protestant grouping strip and its list.
- [Ranked schedule](./schedule-table.md) covers the full ranked purpose table.
