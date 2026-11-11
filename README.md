# ord-88 — Hong Kong Section 88 register plate

A static, print-style plate of the Inland Revenue Department's Section 88
tax-exempt charity register. The shipped artefact is one page: `dist/index.html`
plus `dist/data.json`, generated from the committed CSVs.

The register date is read from `s88list.csv`; the build never hardcodes it.

## Rebuild

```sh
python3 build_site.py
python3 -m unittest discover -s tests -v
```

`build_site.py` writes `dist/index.html`, `dist/data.json` and refreshes
`dist/fonts/`. The build is deterministic: rebuilding the committed inputs leaves
`git status` clean. It exits 2 if a religious or community row has no sub-label;
pass `--allow-incomplete` only for a deliberate partial build.

## Reclassify (when the register changes)

```sh
python3 classify_or.py                  # keyword + LLM pass -> s88list_categorised.csv
python3 classify_sub.py rescue          # re-examine OTH rows -> sub_rescue.csv
python3 apply_rescue.py                 # merge the rescue output, atomically
python3 classify_sub.py religion --since HEAD
python3 classify_sub.py community --since HEAD
python3 build_site.py
```

`--since REF` reuses the labels recorded at that git revision and classifies only
rows that are new since then. Drop it to re-label every row from scratch. A
failed row is written with the fallback label, listed in
`sub_<mode>.failures.csv`, and makes the command exit non-zero.

`categorisation_meta.json` records the source hash, model, prompt version, fallback
count and per-stage history. `python3 provenance.py` prints it.

## Files

| Path | Kind |
| --- | --- |
| `s88list.csv` | current IRD export (input) |
| `s88list_2026-04-30.csv` | archived earlier export, kept for comparison |
| `s88list_categorised.csv` | generated: one row per register entry, in register order |
| `sub_religion.csv`, `sub_community.csv`, `sub_rescue.csv` | generated: positional sub-labels, aligned to the categorised rows (`sub_rescue.csv` is the rescue pass audit, merged by `apply_rescue.py`) |
| `dist/` | generated: the plate and its data |
| `assets/fonts/` | self-hosted WOFF2 files copied into `dist/` |
| `exports/`, `webui.pen` | design artefacts, not build inputs |

The sub-files are positional. The tests check their names against the categorised
rows; a stale file fails loudly rather than silently mislabelling a register.

## Classification caveats

Purposes are machine-assigned by keyword rules with an LLM tie-break. Faith and
community labels are inferred from organisation names, including the
socio-political character codes in `sub_community.csv`. They are name-pattern
leads, not verified affiliations. The plate shows aggregates; treat every label
as a lead, not a finding.

## Design

`docs/plate.md` documents the shipped plate's type and colour system.
`DESIGN.md` is the historical brief for an interactive explorer that was not
built; it is kept for context, not as a description of `dist/`.
