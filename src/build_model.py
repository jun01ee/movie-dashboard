from __future__ import annotations

import re
import unicodedata
from hashlib import blake2s

import pandas as pd

from .paths import PROCESSED_DIR, STG_MOVIE_SEED


def slug(value: str) -> str:
    value = (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def short_hash(value: str) -> str:
    return blake2s(value.encode("utf-8"), digest_size=3).hexdigest()


def movie_key(title: str, release_date: str) -> str:
    value = f"{title}|{release_date}"
    return f"mov_{slug(title)}_{release_date[:4]}_{short_hash(value)}"


def person_key(name: str) -> str:
    return f"per_{slug(name)}_{short_hash(name)}"


def genre_key(name: str) -> str:
    return f"gen_{slug(name)}"


def read_seed() -> pd.DataFrame:
    if not STG_MOVIE_SEED.exists():
        raise FileNotFoundError(
            f"Missing {STG_MOVIE_SEED}. Run `python -m src.load_seed` first."
        )
    df = pd.read_csv(STG_MOVIE_SEED)
    df["movie_key"] = [
        movie_key(title, release_date)
        for title, release_date in zip(df["movie_title"], df["release_date"])
    ]
    df["release_year"] = pd.to_datetime(df["release_date"]).dt.year
    df["release_date_key"] = pd.to_datetime(df["release_date"]).dt.strftime("%Y%m%d")
    return df


def build_dim_movie(seed: pd.DataFrame) -> pd.DataFrame:
    return seed[
        ["movie_key", "movie_title", "release_date", "release_year", "wikipedia_url"]
    ].assign(
        original_title="",
        tmdb_id="",
        imdb_id="",
        wikidata_qid="",
        runtime_minutes=pd.NA,
        original_language="",
        overview="",
        poster_path="",
        homepage="",
    )[
        [
            "movie_key",
            "movie_title",
            "original_title",
            "release_date",
            "release_year",
            "wikipedia_url",
            "tmdb_id",
            "imdb_id",
            "wikidata_qid",
            "runtime_minutes",
            "original_language",
            "overview",
            "poster_path",
            "homepage",
        ]
    ]


def build_fact_movie_performance(seed: pd.DataFrame) -> pd.DataFrame:
    fact = seed[
        ["movie_key", "release_date_key", "budget_usd", "box_office_revenue_usd"]
    ].copy()
    fact["profit_usd"] = fact["box_office_revenue_usd"] - fact["budget_usd"]
    fact["roi"] = fact["profit_usd"] / fact["budget_usd"]
    fact["revenue_budget_multiple"] = fact["box_office_revenue_usd"] / fact["budget_usd"]
    return fact


def build_genres(seed: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    bridge_rows = []
    genre_names = {}
    for _, row in seed.iterrows():
        for order, col in enumerate(["genre_1", "genre_2"], start=1):
            name = row.get(col)
            if pd.isna(name) or not str(name).strip():
                continue
            key = genre_key(str(name))
            genre_names[key] = str(name)
            bridge_rows.append(
                {
                    "movie_key": row["movie_key"],
                    "genre_key": key,
                    "genre_order": order,
                    "is_primary": order == 1,
                }
            )

    bridge = pd.DataFrame(bridge_rows)
    dim = pd.DataFrame(
        [{"genre_key": key, "genre_name": name} for key, name in genre_names.items()]
    )
    return dim.sort_values("genre_name"), bridge


def build_people(seed: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    credit_rows = []
    person_names = {}
    director_cols = ["director_1", "director_2"]
    cast_cols = ["cast_1", "cast_2", "cast_3", "cast_4", "cast_5"]

    for _, row in seed.iterrows():
        for order, col in enumerate(director_cols, start=1):
            name = row.get(col)
            if pd.isna(name) or not str(name).strip():
                continue
            key = person_key(str(name))
            person_names[key] = str(name)
            credit_rows.append(
                {
                    "movie_key": row["movie_key"],
                    "person_key": key,
                    "department": "Directing",
                    "job": "Director",
                    "character_name": "",
                    "billing_order": order,
                }
            )

        for order, col in enumerate(cast_cols, start=1):
            name = row.get(col)
            if pd.isna(name) or not str(name).strip():
                continue
            key = person_key(str(name))
            person_names[key] = str(name)
            credit_rows.append(
                {
                    "movie_key": row["movie_key"],
                    "person_key": key,
                    "department": "Acting",
                    "job": "Actor",
                    "character_name": "",
                    "billing_order": order,
                }
            )

    bridge = pd.DataFrame(credit_rows)
    dim = pd.DataFrame(
        [{"person_key": key, "person_name": name} for key, name in person_names.items()]
    )
    dim["tmdb_person_id"] = ""
    dim["imdb_name_id"] = ""
    return dim.sort_values("person_name"), bridge


def build_dim_date(seed: pd.DataFrame) -> pd.DataFrame:
    dates = pd.to_datetime(seed["release_date"]).drop_duplicates().sort_values()
    dim = pd.DataFrame({"date": dates})
    dim["date_key"] = dim["date"].dt.strftime("%Y%m%d")
    dim["year"] = dim["date"].dt.year
    dim["quarter"] = dim["date"].dt.quarter
    dim["month"] = dim["date"].dt.month
    dim["month_name"] = dim["date"].dt.month_name()
    dim["day"] = dim["date"].dt.day
    dim["date"] = dim["date"].dt.date.astype(str)
    return dim[["date_key", "date", "year", "quarter", "month", "month_name", "day"]]


def build_identity_map(seed: pd.DataFrame) -> pd.DataFrame:
    return seed[
        ["movie_key", "movie_title", "release_year", "wikipedia_url"]
    ].assign(
        tmdb_id="",
        imdb_id="",
        wikidata_qid="",
        match_status="seed_only",
    )


def write_csv(name: str, df: pd.DataFrame) -> None:
    path = PROCESSED_DIR / name
    df.to_csv(path, index=False)
    print(f"Wrote {path} ({len(df)} rows)")


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    seed = read_seed()

    dim_genre, bridge_movie_genre = build_genres(seed)
    dim_person, bridge_movie_credit = build_people(seed)

    outputs = {
        "dim_movie.csv": build_dim_movie(seed),
        "fact_movie_performance.csv": build_fact_movie_performance(seed),
        "dim_genre.csv": dim_genre,
        "bridge_movie_genre.csv": bridge_movie_genre,
        "dim_person.csv": dim_person,
        "bridge_movie_credit.csv": bridge_movie_credit,
        "dim_date.csv": build_dim_date(seed),
        "movie_identity_map.csv": build_identity_map(seed),
    }
    for name, df in outputs.items():
        write_csv(name, df)


if __name__ == "__main__":
    main()
