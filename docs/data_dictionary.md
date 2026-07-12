# Data Dictionary

## `stg_movie_seed.csv`

Grain: one row per source movie.

Current primary source is TMDb. `src.load_tmdb_seed` writes a clean 2010-2025
sample with one row per `tmdb_id`, positive budget and revenue, and enough
movie metadata for dashboarding. The starter workbook loader can still produce
the same staging table for comparison/backfill work.

## `dim_movie.csv`

Grain: one row per movie.

- `movie_key`: stable project movie key. TMDb-sourced rows use `mov_tmdb_<id>`.
- `movie_title`: source title.
- `original_title`: reserved for API enrichment.
- `release_date`: movie release date.
- `release_year`: release year.
- `wikipedia_url`: source workbook URL.
- `tmdb_id`, `imdb_id`, `wikidata_qid`: external IDs.
- `runtime_minutes`, `original_language`, `overview`, `poster_path`, `homepage`: TMDb enrichment fields.
- `tagline`, `status`, `tmdb_popularity`, `tmdb_vote_average`, `tmdb_vote_count`: TMDb enrichment fields.

## `fact_movie_performance.csv`

Grain: one row per movie.

- `movie_key`: joins to `dim_movie`.
- `release_date_key`: joins to `dim_date`.
- `budget_usd`: source budget. Expanded TMDb seed keeps only positive values.
- `box_office_revenue_usd`: source box office revenue. Expanded TMDb seed keeps only positive values.
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
- `genre_order`: source genre order.
- `is_primary`: true for the first source genre.

## `dim_person.csv`

Grain: one row per person.

- `person_key`: stable person key.
- `person_name`: display name.
- `tmdb_person_id`, `imdb_name_id`: external person IDs.
- `tmdb_person_url`: TMDb person page URL.
- `profile_path`: TMDb profile image path, blank when no image is available.
- `profile_url`: full TMDb profile image URL for Power BI image visuals.
- `profile_image_available`: boolean flag for profile image fallback handling.

## `bridge_movie_credit.csv`

Grain: one row per movie/person credit.

- `movie_key`: joins to `dim_movie`.
- `person_key`: joins to `dim_person`.
- `department`: broad credit group, such as `Acting` or `Directing`.
- `job`: credit job, such as `Actor` or `Director`.
- `character_name`: reserved for cast enrichment.
- `billing_order`: source order within the director or cast columns.
- `tmdb_credit_id`, `tmdb_person_id`, `credit_order`: TMDb enrichment fields.

## `dim_person_detail.csv`

Grain: zero or one enrichment row per person in `dim_person`.

- `person_key`: joins to `dim_person` in a one-to-zero-or-one relationship.
- `tmdb_person_id`: TMDb person identifier used to fetch the details.
- `biography`, `biography_available`: biography text and missing-value flag.
- `birthday`, `deathday`, `place_of_birth`: biographical attributes.
- `gender_code`, `gender_label`: TMDb gender code and report-friendly label.
- `profile_path`, `profile_url`, `profile_image_available`: profile image fields and fallback flag.

## `dim_date.csv`

Grain: one row per release date.

- `date_key`: `YYYYMMDD`.
- `date`, `year`, `quarter`, `month`, `month_name`, `day`: date attributes.

## `movie_identity_map.csv`

Grain: one row per movie.

Tracks matching between the seed data and future external source IDs.

- `match_status`: `seed_only`, `matched`, `needs_review`, `unmatched`, or `manual`.
- `match_confidence`: matching confidence or review reason.

## `stg_tmdb_movie_details.csv`

Grain: one row per matched movie.

TMDb detail, image, rating, runtime, language, and external-ID fields used to enrich `dim_movie`.

## `stg_tmdb_movie_cast.csv`

Grain: one row per TMDb cast credit.

Used to fill actor character names, TMDb person IDs, and credit order.
Also carries TMDb profile image paths for `dim_person`.

## `stg_tmdb_movie_crew.csv`

Grain: one row per TMDb director credit.

Used to fill director TMDb person IDs and credit IDs.
Also carries TMDb profile image paths for `dim_person`.
