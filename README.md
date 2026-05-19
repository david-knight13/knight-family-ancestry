# Knight Family Ancestry — Interactive Fan Chart

An interactive, zoomable fan chart of the ancestry of David Knight, built for
America's 250th anniversary (1776–2026).

**Live page:** see the GitHub Pages link for this repository.

## What it shows

- **4,400+ ancestors** traced from FamilySearch, fanned out by generation.
- **Fan Chart tab** — a colour-coded radial pedigree:
  - Colour by U.S. state / colony, or switch to **Country mode** (American and
    colonial-American ancestors render in a patriotic red/white/blue palette;
    foreign origins span a colour spectrum).
  - **Generation-depth slider** to control how many rings are shown.
  - Click any ancestor to open a detail panel; from there you can re-centre the
    whole chart on that person.
  - Dashed grey wedges mark branches whose ancestry is still undocumented.
- **Summary Report tab** — cumulative pie charts of ancestral origins per
  generation, toggleable between states and countries.
- **Notable American Ancestors** sidebar — ranked list of documented,
  historically notable ancestors with short life stories.

## Repository layout

```
index.html        The complete, self-contained interactive chart (data embedded)
data/             Source genealogy data and crawl intermediates (JSON)
scripts/          Python helpers — merge crawled data and embed it into the page
docs/             Research notes on ancestral historical events
```

## Rebuilding

`index.html` has its dataset embedded directly. To regenerate it after updating
`data/fan-data-clean.json`, run `scripts/embed_data.py`.

## Data source

Genealogical data is drawn from [FamilySearch](https://www.familysearch.org/).
