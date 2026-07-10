# Movie Dashboard

Personal, non-commercial movie dashboard project.

This repo builds a simple semantic movie dataset for Power BI. The current
pipeline uses TMDb as the primary source, keeps a clean movie sample from 2010
through 2025, normalizes it into star-schema CSV tables, and avoids internal
duplicate movies by using TMDb IDs.

## Project Layout

```text
data/raw/        local-only source workbook and API cache
data/processed/  generated CSV tables for Power BI and possible Kaggle publishing
docs/            data dictionary, source notes, dashboard screenshot, report link
notebooks/       optional exploration
src/             reproducible pipeline scripts
```

## Environment

Use a dedicated Conda/Mamba environment instead of base Python.

```bash
mamba env create -f environment.yml
conda activate movie-dashboard
```

Conda works too:

```bash
conda env create -f environment.yml
conda activate movie-dashboard
```

## Run Pipeline

Add your TMDb bearer token to a local `.env` file:

```text
TMDB_BEARER_TOKEN=your_token_here
```

Then run:

```bash
python -m src.load_tmdb_seed
python -m src.build_model
python -m src.validate
```

`src.load_tmdb_seed` pulls a revenue-sorted sample for each release year from
2010 through 2025. It does not claim completeness. It keeps rows only when the
movie has enough clean dashboard fields: title, release date, runtime, positive
revenue, budget of at least `$1M`, genre, director, and cast.

## Starter Workbook Loader

The original starter workbook loader is still available for comparison or
backfill work. Place the workbook here:

```text
data/raw/Movie Data Starter Project.xlsx
```

Then run:

```bash
python -m src.load_seed
python -m src.build_model
python -m src.validate
```

## TMDb Enrichment

TMDb API JSON is cached under `data/raw/api_cache/tmdb/`. The primary TMDb
loader writes these staging CSVs directly:

- `stg_tmdb_movie_details.csv`
- `stg_tmdb_movie_cast.csv`
- `stg_tmdb_movie_crew.csv`

Manual TMDb match overrides for workbook-sourced rows live in:

```text
data/manual/tmdb_movie_matches.csv
```

Use that file only when automatic matching marks a movie as `needs_review` or
`unmatched`.

## Data Model

The processed CSVs use a small star schema:

- `dim_movie.csv`
- `fact_movie_performance.csv`
- `dim_genre.csv`
- `bridge_movie_genre.csv`
- `dim_person.csv`
- `bridge_movie_credit.csv`
- `dim_date.csv`
- `movie_identity_map.csv`

Power BI should import `data/processed/*.csv`, relate facts and bridges to the dimensions, and build measures for movie count, budget, revenue, profit, ROI, and revenue multiple.

## Enrichment Roadmap

TMDb is the first enrichment source for movie details, credits, character names,
images, and external IDs. IMDb and Wikidata can be added as crosswalk/support
sources. Raw API responses should stay in `data/raw/api_cache/` and should not
be committed.

## Dashboard

Power BI dashboard link: _to be added_

Dashboard screenshot: _to be added at `docs/dashboard.png`_
