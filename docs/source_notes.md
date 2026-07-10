# Source Notes

## Starter Workbook

The starter workbook is local-only at:

```text
data/raw/Movie Data Starter Project.xlsx
```

It is not committed because redistribution rights have not been confirmed.

Manual corrections in `data/manual/movie_seed_corrections.csv` are applied when
building `stg_movie_seed.csv`. They fix source release dates and remove
re-release rows that should not be modeled as separate movies.

## TMDb

TMDb is the primary source for the expanded 2010-2025 dataset. The loader uses
revenue-sorted discover results per release year and filters to released movies
with title, release date, runtime, revenue, budget of at least `$1M`, genre,
director, and cast. This is a clean dashboard sample, not a complete catalog.

Store TMDb API responses under `data/raw/api_cache/tmdb/`, which is ignored by git.

Local API token setup:

```text
TMDB_BEARER_TOKEN=your_token_here
```

The pipeline writes publishable normalized CSVs under `data/processed/`.

## IMDb and Wikidata

IMDb non-commercial datasets and Wikidata can be used later as crosswalk/support sources for IDs, ratings, and metadata. Confirm license and attribution requirements before publishing derived datasets to Kaggle.

## Publishing Notes

The public repo should commit code, documentation, and processed CSVs. Do not commit `.env`, API tokens, raw API cache, or the raw workbook unless redistribution rights are clear.
