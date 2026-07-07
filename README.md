# Movie Dashboard

Personal, non-commercial movie dashboard project.

This repo builds a simple semantic movie dataset for Power BI from a starter Excel workbook. The data pipeline reads the raw workbook, normalizes the movie data into star-schema CSV tables, and leaves space for later TMDb enrichment.

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

Place the starter workbook here:

```text
data/raw/Movie Data Starter Project.xlsx
```

Then run:

```bash
python -m src.load_seed
python -m src.build_model
python -m src.validate
```

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

TMDb is the planned first enrichment source for recent movies, credits, genres, release dates, images, and external IDs. IMDb and Wikidata can be added as crosswalk/support sources. Raw API responses should stay in `data/raw/api_cache/` and should not be committed.

## Dashboard

Power BI dashboard link: _to be added_

Dashboard screenshot: _to be added at `docs/dashboard.png`_
