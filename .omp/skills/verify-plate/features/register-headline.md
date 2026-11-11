# Register headline and provenance

A reader opening the plate sees one number for the whole register, the date the register is stamped, and a source line naming the file and the entry count. This is the claim every other section sits under, so it is verified first.

## Sub-features

- `headline-total` shows the register size as the hero number.
- `headline-as-at` shows the register's own stamp date in both languages.
- `headline-source` names the source file, the date, and the count in the footer.
- `headline-identity` shows the plate title and imprint, so a screenshot proves which page it is.

## How to get to it (user POV)

- Open the site root; the headline is above the fold, under the title "The register, resolved".
- Scroll to the footer for the source line.

## Driving it with omp browser

Preconditions: doctor passes on `http://127.0.0.1:8811`, and `dist/data.json` is copied into the evidence directory.

- Read the hero: `await tab.text(".plate .hero")` → equals `total` from `data.json`, formatted with thousands separators.
- Read the stamp: `await tab.text(".plate-head .meta")` → contains `as_at` and `as_at_zh` from `data.json`.
- Read the title: `await tab.text(".plate-head h1")` → `The register, resolved`.
- Read the source line: `await tab.text(".source-line")` → contains `IRD s88list.csv`, `as_at`, and the formatted `total`, and ends with the Chinese entry count.
- Read the imprint: `await tab.text(".imprint")` → `Curious Gold · Plate 05`.
- Capture `plate-full.png` here; it shows every later section too.

## Gotchas

- The hero number and the footer count are the same value rendered twice; a mismatch between them means the build is inconsistent, and both must be reported.
- The stamp comes from the CSV header (`Position as at`), not from the file mtime; re-running the pipeline does not move the date.
- `as_at` is English long form (`30 September 2026`) while `as_at_zh` is `2026年9月30日`; comparing the wrong field is the usual false failure.
- A build with unclassified societies exits 2 unless `--allow-incomplete` is passed; with the flag it renders, and the warning on stderr is the signal to capture with the proof.
