# Source Notes

## Starter Workbook

The starter workbook is local-only at:

```text
data/raw/Movie Data Starter Project.xlsx
```

It is not committed because redistribution rights have not been confirmed.

## TMDb

TMDb is the planned first enrichment source for recent movie discovery, details, credits, genres, release dates, images, and external IDs.

Store TMDb API responses under `data/raw/api_cache/`, which is ignored by git.

## IMDb and Wikidata

IMDb non-commercial datasets and Wikidata can be used later as crosswalk/support sources for IDs, ratings, and metadata. Confirm license and attribution requirements before publishing derived datasets to Kaggle.

## Publishing Notes

The public repo should commit code, documentation, and processed CSVs. Do not commit `.env`, API tokens, raw API cache, or the raw workbook unless redistribution rights are clear.
