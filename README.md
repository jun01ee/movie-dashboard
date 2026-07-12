# Movie Dashboard

Personal, non-commercial movie analytics project for Power BI. The work started
from a [Kaggle starter Excel workbook](https://www.kaggle.com/datasets/derrickmallison/movie-data-starter-project-pivot-table-and-chart),
used it to design the semantic model, then expanded and enriched the dataset
with the TMDb API.

## Results

Power BI report link: _to be added_

Dashboard screenshot: _to be added at `docs/dashboard.png`_

## Current Dataset

The current generated dataset contains a clean TMDb movie sample for release
years `2010-2025`.

- Movies: `2,371`
- Target depth: `150` clean, revenue-sorted movies per year
- Current exception: `2020` has `121` movies after cleaning filters
- Deduplication: one movie per `tmdb_id`
- Minimum budget: `$1M`
- Required fields: title, release date, runtime, revenue, budget, genre,
  director, and cast

## Data Model

Power BI should load these CSVs from `data/processed/`:

- `dim_movie.csv`
- `fact_movie_performance.csv`
- `dim_genre.csv`
- `bridge_movie_genre.csv`
- `dim_person.csv`
- `dim_person_detail.csv`
- `bridge_movie_credit.csv`
- `dim_date.csv`

Optional QA/reference table:

- `movie_identity_map.csv`

The model is a simple star schema centered on `movie_key`, with bridge tables
for movie/genre and movie/person relationships.

## Approach

The primary pipeline uses TMDb as the source for movie discovery, details,
credits, external IDs, posters, person profile images, runtime, ratings, budget,
and revenue. It pulls revenue-sorted discover results for each year, keeps rows
that pass the cleaning rules above, caches raw API JSON locally, and writes
normalized CSVs for Power BI.

The original starter Excel workbook loader is still available for comparison or
backfill work, but the dashboard dataset is now TMDb-first.

Detailed source notes and table definitions live in:

- `docs/source_notes.md`
- `docs/data_dictionary.md`

## Run Pipeline

Use a dedicated Conda/Mamba environment instead of base Python.

```bash
mamba env create -f environment.yml
conda activate movie-dashboard
```

Add your TMDb bearer token to a local `.env` file:

```text
TMDB_BEARER_TOKEN=your_token_here
```

Generate the TMDb dataset and model CSVs:

```bash
python -m src.load_tmdb_seed
python -m src.build_model
python -m src.enrich_tmdb
python -m src.build_model
python -m src.enrich_tmdb_people
python -m src.validate
```

Optional starter workbook path:

```text
data/raw/Movie Data Starter Project.xlsx
```

Optional starter workbook commands:

```bash
python -m src.load_seed
python -m src.build_model
python -m src.validate
```

## Project Layout

```text
data/raw/        local-only source workbook and API cache
data/processed/  generated CSV tables for Power BI and possible Kaggle publishing
docs/            data dictionary, source notes, dashboard screenshot, report link
notebooks/       optional exploration
src/             reproducible pipeline scripts
```

## Reproducibility Notes

- `.env` is required locally and must contain `TMDB_BEARER_TOKEN`.
- `data/raw/` and the TMDb API cache are ignored by git.
- Generated publishable CSVs are written to `data/processed/`.
- The raw starter workbook is not committed because redistribution rights are
  unclear.
