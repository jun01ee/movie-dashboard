from __future__ import annotations

import re
import unicodedata
from hashlib import blake2s

import pandas as pd
from pandas.errors import EmptyDataError

from .paths import (
    MOVIE_IDENTITY_MAP,
    PROCESSED_DIR,
    STG_MOVIE_SEED,
    STG_TMDB_MOVIE_CAST,
    STG_TMDB_MOVIE_CREW,
    STG_TMDB_MOVIE_DETAILS,
)


DETAIL_COLUMNS = [
    "tmdb_id",
    "imdb_id",
    "wikidata_qid",
    "runtime_minutes",
    "original_language",
    "overview",
    "poster_path",
    "homepage",
    "tagline",
    "status",
    "tmdb_popularity",
    "tmdb_vote_average",
    "tmdb_vote_count",
]

IDENTITY_COLUMNS = [
    "tmdb_id",
    "imdb_id",
    "wikidata_qid",
    "match_status",
    "match_confidence",
]


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


def tmdb_movie_key(tmdb_id: object) -> str:
    return f"mov_tmdb_{int(tmdb_id)}"


def person_key(name: str) -> str:
    return f"per_{slug(name)}_{short_hash(name)}"


def genre_key(name: str) -> str:
    return f"gen_{slug(name)}"


def norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def read_optional_csv(path, columns: list[str]) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=columns)
    try:
        return pd.read_csv(path)
    except EmptyDataError:
        return pd.DataFrame(columns=columns)


def apply_movie_updates(
    base: pd.DataFrame, updates: pd.DataFrame, columns: list[str]
) -> pd.DataFrame:
    if updates.empty:
        return base
    available = ["movie_key"] + [col for col in columns if col in updates.columns]
    merged = base.merge(updates[available], on="movie_key", how="left", suffixes=("", "_new"))
    for col in available[1:]:
        new_col = f"{col}_new"
        if new_col in merged:
            merged[col] = merged[new_col].combine_first(merged[col])
            merged = merged.drop(columns=[new_col])
    return merged


def read_seed() -> pd.DataFrame:
    if not STG_MOVIE_SEED.exists():
        raise FileNotFoundError(
            f"Missing {STG_MOVIE_SEED}. Run `python -m src.load_seed` first."
        )
    df = pd.read_csv(STG_MOVIE_SEED)
    if "movie_key" not in df.columns:
        if "tmdb_id" in df.columns and df["tmdb_id"].notna().all():
            df["movie_key"] = df["tmdb_id"].map(tmdb_movie_key)
        else:
            df["movie_key"] = [
                movie_key(title, release_date)
                for title, release_date in zip(df["movie_title"], df["release_date"])
            ]
    df["release_year"] = pd.to_datetime(df["release_date"]).dt.year
    df["release_date_key"] = pd.to_datetime(df["release_date"]).dt.strftime("%Y%m%d")
    return df


def build_dim_movie(seed: pd.DataFrame) -> pd.DataFrame:
    dim = seed[
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
        tagline="",
        status="",
        tmdb_popularity=pd.NA,
        tmdb_vote_average=pd.NA,
        tmdb_vote_count=pd.NA,
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
            "tagline",
            "status",
            "tmdb_popularity",
            "tmdb_vote_average",
            "tmdb_vote_count",
        ]
    ]
    details = read_optional_csv(STG_TMDB_MOVIE_DETAILS, ["movie_key"] + DETAIL_COLUMNS)
    return apply_movie_updates(dim, details, DETAIL_COLUMNS + ["original_title"])


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
    genre_cols = sorted(
        [col for col in seed.columns if col.startswith("genre_")],
        key=lambda col: int(col.rsplit("_", 1)[1]),
    )
    for _, row in seed.iterrows():
        for order, col in enumerate(genre_cols, start=1):
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
    bridge["tmdb_credit_id"] = ""
    bridge["tmdb_person_id"] = ""
    bridge["credit_order"] = pd.NA
    return apply_tmdb_credit_enrichment(dim.sort_values("person_name"), bridge)


def apply_tmdb_credit_enrichment(
    dim_person: pd.DataFrame, bridge: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    cast = read_optional_csv(
        STG_TMDB_MOVIE_CAST,
        [
            "movie_key",
            "person_name",
            "tmdb_person_id",
            "character_name",
            "credit_order",
            "tmdb_credit_id",
        ],
    )
    crew = read_optional_csv(
        STG_TMDB_MOVIE_CREW,
        [
            "movie_key",
            "person_name",
            "tmdb_person_id",
            "department",
            "job",
            "tmdb_credit_id",
        ],
    )
    if cast.empty and crew.empty:
        return dim_person, bridge

    dim_lookup = dim_person[["person_key", "person_name"]].copy()
    dim_lookup["name_key"] = dim_lookup["person_name"].map(norm)
    bridge = bridge.merge(dim_lookup[["person_key", "person_name", "name_key"]], on="person_key", how="left")
    for col in ["character_name", "tmdb_person_id", "tmdb_credit_id", "credit_order"]:
        bridge[col] = bridge[col].astype("object")

    if not cast.empty:
        actor_updates = cast.copy()
        actor_updates["name_key"] = actor_updates["person_name"].fillna("").map(norm)
        actor_updates = actor_updates.drop_duplicates(["movie_key", "name_key"])
        bridge = bridge.merge(
            actor_updates[
                [
                    "movie_key",
                    "name_key",
                    "character_name",
                    "tmdb_person_id",
                    "tmdb_credit_id",
                    "credit_order",
                ]
            ],
            on=["movie_key", "name_key"],
            how="left",
            suffixes=("", "_tmdb"),
        )
        actor_mask = bridge["job"].eq("Actor")
        for col in ["character_name", "tmdb_person_id", "tmdb_credit_id", "credit_order"]:
            new_col = f"{col}_tmdb"
            if new_col in bridge:
                bridge.loc[actor_mask, col] = bridge.loc[actor_mask, new_col].combine_first(
                    bridge.loc[actor_mask, col]
                )
                bridge = bridge.drop(columns=[new_col])

    if not crew.empty:
        crew_updates = crew.copy()
        crew_updates["name_key"] = crew_updates["person_name"].fillna("").map(norm)
        crew_updates = crew_updates.drop_duplicates(["movie_key", "name_key", "job"])
        bridge = bridge.merge(
            crew_updates[["movie_key", "name_key", "job", "tmdb_person_id", "tmdb_credit_id"]],
            on=["movie_key", "name_key", "job"],
            how="left",
            suffixes=("", "_tmdb"),
        )
        director_mask = bridge["job"].eq("Director")
        for col in ["tmdb_person_id", "tmdb_credit_id"]:
            new_col = f"{col}_tmdb"
            if new_col in bridge:
                bridge.loc[director_mask, col] = bridge.loc[director_mask, new_col].combine_first(
                    bridge.loc[director_mask, col]
                )
                bridge = bridge.drop(columns=[new_col])

    person_ids = (
        bridge.loc[bridge["tmdb_person_id"].notna() & (bridge["tmdb_person_id"].astype(str) != "")]
        [["person_key", "tmdb_person_id"]]
        .drop_duplicates("person_key")
    )
    if not person_ids.empty:
        dim_person = dim_person.drop(columns=["tmdb_person_id"]).merge(
            person_ids, on="person_key", how="left"
        )
        dim_person["tmdb_person_id"] = dim_person["tmdb_person_id"].fillna("")

    return dim_person, bridge.drop(columns=["person_name", "name_key"])


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
    identity = seed[
        ["movie_key", "movie_title", "release_year", "wikipedia_url"]
    ].assign(
        tmdb_id="",
        imdb_id="",
        wikidata_qid="",
        match_status="seed_only",
        match_confidence="",
    )
    existing = read_optional_csv(
        MOVIE_IDENTITY_MAP, ["movie_key", "movie_title", "release_year", "wikipedia_url"] + IDENTITY_COLUMNS
    )
    details = read_optional_csv(STG_TMDB_MOVIE_DETAILS, ["movie_key"] + DETAIL_COLUMNS)
    identity = apply_movie_updates(identity, existing, IDENTITY_COLUMNS)
    identity = apply_movie_updates(identity, details, ["tmdb_id", "imdb_id", "wikidata_qid"])
    enriched = identity["tmdb_id"].notna() & identity["tmdb_id"].astype(str).str.strip().ne("")
    seed_only = identity["match_status"].eq("seed_only")
    identity.loc[enriched & seed_only, "match_status"] = "matched"
    identity.loc[enriched & seed_only, "match_confidence"] = "tmdb_source"
    return identity


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
