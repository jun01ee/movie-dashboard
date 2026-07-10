from __future__ import annotations

import pandas as pd

from .paths import (
    PROCESSED_DIR,
    STG_MOVIE_SEED,
    STG_TMDB_MOVIE_CAST,
    STG_TMDB_MOVIE_CREW,
    STG_TMDB_MOVIE_DETAILS,
)
from .load_tmdb_seed import MIN_BUDGET_USD


def read_csv(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}. Run the pipeline first.")
    return pd.read_csv(path)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def present(series: pd.Series) -> pd.Series:
    values = series.fillna("").astype(str).str.strip()
    return values.ne("") & values.str.lower().ne("nan")


def optional_csv(path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def main() -> None:
    seed = pd.read_csv(STG_MOVIE_SEED)
    dim_movie = read_csv("dim_movie.csv")
    fact = read_csv("fact_movie_performance.csv")
    dim_genre = read_csv("dim_genre.csv")
    bridge_genre = read_csv("bridge_movie_genre.csv")
    dim_person = read_csv("dim_person.csv")
    bridge_credit = read_csv("bridge_movie_credit.csv")
    dim_date = read_csv("dim_date.csv")
    identity = read_csv("movie_identity_map.csv")

    require(len(seed) > 0, "seed is empty")
    require(dim_movie["movie_key"].is_unique, "dim_movie.movie_key has duplicates")
    require(identity["movie_key"].is_unique, "movie_identity_map.movie_key has duplicates")
    require(fact["movie_key"].is_unique, "fact_movie_performance.movie_key has duplicates")
    if "tmdb_id" in seed.columns:
        require(seed["tmdb_id"].notna().all(), "seed tmdb_id has missing values")
        require(seed["tmdb_id"].is_unique, "seed tmdb_id has duplicates")

    movie_keys = set(dim_movie["movie_key"])
    genre_keys = set(dim_genre["genre_key"])
    person_keys = set(dim_person["person_key"])
    date_keys = set(dim_date["date_key"].astype(str))

    require(set(fact["movie_key"]).issubset(movie_keys), "fact has unknown movie_key")
    require(set(bridge_genre["movie_key"]).issubset(movie_keys), "genre bridge has unknown movie_key")
    require(set(bridge_genre["genre_key"]).issubset(genre_keys), "genre bridge has unknown genre_key")
    require(set(bridge_credit["movie_key"]).issubset(movie_keys), "credit bridge has unknown movie_key")
    require(set(bridge_credit["person_key"]).issubset(person_keys), "credit bridge has unknown person_key")
    require(set(fact["release_date_key"].astype(str)).issubset(date_keys), "fact has unknown release_date_key")

    require((fact["budget_usd"] >= MIN_BUDGET_USD).all(), "budget_usd is below clean sample threshold")
    require((fact["box_office_revenue_usd"] > 0).all(), "box_office_revenue_usd must be positive")
    release_dates = pd.to_datetime(dim_movie["release_date"], errors="coerce")
    require(release_dates.notna().all(), "invalid release dates")
    require(
        release_dates.dt.year.between(2010, 2025).all(),
        "release years must be between 2010 and 2025",
    )

    allowed_statuses = {"seed_only", "matched", "needs_review", "unmatched", "manual"}
    require(
        set(identity["match_status"].dropna()).issubset(allowed_statuses),
        "movie_identity_map has invalid match_status",
    )

    tmdb_movie_ids = dim_movie.loc[present(dim_movie["tmdb_id"]), "tmdb_id"]
    require(tmdb_movie_ids.is_unique, "dim_movie.tmdb_id has duplicates")

    runtime = pd.to_numeric(dim_movie["runtime_minutes"], errors="coerce")
    require(
        (runtime[present(dim_movie["runtime_minutes"])] > 0).all(),
        "runtime_minutes must be positive where present",
    )

    poster_path = dim_movie.loc[present(dim_movie["poster_path"]), "poster_path"].astype(str)
    require(poster_path.str.startswith("/").all(), "poster_path must start with / where present")

    for path in [STG_TMDB_MOVIE_DETAILS, STG_TMDB_MOVIE_CAST, STG_TMDB_MOVIE_CREW]:
        stage = optional_csv(path)
        if stage.empty:
            continue
        require(set(stage["movie_key"]).issubset(movie_keys), f"{path.name} has unknown movie_key")

    print("Validation passed")


if __name__ == "__main__":
    main()
