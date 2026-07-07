from __future__ import annotations

import pandas as pd

from .paths import PROCESSED_DIR, STG_MOVIE_SEED


def read_csv(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}. Run the pipeline first.")
    return pd.read_csv(path)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


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

    require(len(seed) == 508, f"Expected 508 seed rows, found {len(seed)}")
    require(dim_movie["movie_key"].is_unique, "dim_movie.movie_key has duplicates")
    require(identity["movie_key"].is_unique, "movie_identity_map.movie_key has duplicates")
    require(fact["movie_key"].is_unique, "fact_movie_performance.movie_key has duplicates")

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

    require((fact["budget_usd"] >= 0).all(), "budget_usd has negative values")
    require((fact["box_office_revenue_usd"] >= 0).all(), "box_office_revenue_usd has negative values")
    require(pd.to_datetime(dim_movie["release_date"], errors="coerce").notna().all(), "invalid release dates")

    print("Validation passed")


if __name__ == "__main__":
    main()
