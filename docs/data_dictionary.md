# Data Dictionary

## `stg_movie_seed.csv`

Grain: one row per source workbook movie.

Cleaned copy of the starter workbook `Movie Data` sheet. Column names are normalized to snake case.

## `dim_movie.csv`

Grain: one row per movie.

- `movie_key`: stable project movie key.
- `movie_title`: source title.
- `original_title`: reserved for API enrichment.
- `release_date`: movie release date.
- `release_year`: release year.
- `wikipedia_url`: source workbook URL.
- `tmdb_id`, `imdb_id`, `wikidata_qid`: reserved external IDs.
- `runtime_minutes`, `original_language`, `overview`, `poster_path`, `homepage`: reserved API enrichment fields.

## `fact_movie_performance.csv`

Grain: one row per movie.

- `movie_key`: joins to `dim_movie`.
- `release_date_key`: joins to `dim_date`.
- `budget_usd`: source budget.
- `box_office_revenue_usd`: source box office revenue.
- `profit_usd`: revenue minus budget.
- `roi`: profit divided by budget.
- `revenue_budget_multiple`: revenue divided by budget.

## `dim_genre.csv`

Grain: one row per genre.

- `genre_key`: stable genre key.
- `genre_name`: display genre.

## `bridge_movie_genre.csv`

Grain: one row per movie/genre assignment.

- `movie_key`: joins to `dim_movie`.
- `genre_key`: joins to `dim_genre`.
- `genre_order`: source order from the workbook.
- `is_primary`: true for `Genre (1)`.

## `dim_person.csv`

Grain: one row per person.

- `person_key`: stable person key.
- `person_name`: display name.
- `tmdb_person_id`, `imdb_name_id`: reserved API enrichment IDs.

## `bridge_movie_credit.csv`

Grain: one row per movie/person credit.

- `movie_key`: joins to `dim_movie`.
- `person_key`: joins to `dim_person`.
- `department`: broad credit group, such as `Acting` or `Directing`.
- `job`: credit job, such as `Actor` or `Director`.
- `character_name`: reserved for cast enrichment.
- `billing_order`: source order within the director or cast columns.

## `dim_date.csv`

Grain: one row per release date.

- `date_key`: `YYYYMMDD`.
- `date`, `year`, `quarter`, `month`, `month_name`, `day`: date attributes.

## `movie_identity_map.csv`

Grain: one row per movie.

Tracks matching between the seed data and future external source IDs.
