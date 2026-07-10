from __future__ import annotations

import re

import pandas as pd

from .paths import (
    MANUAL_DIR,
    MANUAL_TMDB_MATCHES,
    MOVIE_IDENTITY_MAP,
    PROCESSED_DIR,
    STG_MOVIE_SEED,
    STG_TMDB_MOVIE_CAST,
    STG_TMDB_MOVIE_CREW,
    STG_TMDB_MOVIE_DETAILS,
)
from .tmdb_client import TMDbClient


def norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def clean_names(values: list[object]) -> set[str]:
    names = set()
    for value in values:
        if pd.isna(value) or not str(value).strip():
            continue
        names.add(norm(str(value)))
    return names


def release_year_from(*records: dict) -> int | None:
    for record in records:
        release_date = record.get("release_date") or ""
        if str(release_date)[:4].isdigit():
            return int(str(release_date)[:4])
    return None


def director_names(detail: dict) -> set[str]:
    return {
        norm(crew.get("name") or "")
        for crew in (detail.get("credits") or {}).get("crew") or []
        if crew.get("job") == "Director" and crew.get("name")
    }


def result_title_matches(title: str, result: dict) -> bool:
    title_norm = norm(title)
    names = [result.get("title") or "", result.get("original_title") or ""]
    return any(norm(name) == title_norm for name in names)


def read_manual_matches() -> pd.DataFrame:
    MANUAL_DIR.mkdir(parents=True, exist_ok=True)
    if not MANUAL_TMDB_MATCHES.exists():
        pd.DataFrame(columns=["movie_key", "tmdb_id", "note"]).to_csv(
            MANUAL_TMDB_MATCHES, index=False
        )
    return pd.read_csv(MANUAL_TMDB_MATCHES)


def pick_match(
    title: str,
    year: int,
    directors: list[object],
    results: list[dict],
    client: TMDbClient,
) -> tuple[int | None, str, str]:
    exact_title_matches = [
        result for result in results if result.get("id") and result_title_matches(title, result)
    ]
    exact_year_title_matches = [
        result
        for result in exact_title_matches
        if release_year_from(result) == year
    ]
    if len(exact_year_title_matches) == 1:
        return int(exact_year_title_matches[0]["id"]), "matched", "exact_title_year"

    director_norms = clean_names(directors)
    director_matches = []
    far_year_matches = []
    candidate_results = exact_title_matches or results[:5]

    for result in candidate_results:
        if not result.get("id"):
            continue
        detail = client.movie_details(int(result["id"]))
        release_year = release_year_from(detail, result)

        if director_norms and director_norms & director_names(detail):
            if release_year is not None and abs(release_year - year) > 2:
                far_year_matches.append(result)
            else:
                director_matches.append(result)

    if len(director_matches) == 1:
        return int(director_matches[0]["id"]), "matched", "title_director"
    if director_matches:
        return None, "needs_review", "multiple_title_director_matches"
    if far_year_matches:
        return None, "needs_review", "release_year_gap_gt_2"
    if len(exact_year_title_matches) == 1:
        return int(exact_year_title_matches[0]["id"]), "matched", "exact_title_year"
    if exact_year_title_matches:
        return None, "needs_review", "multiple_exact_year_matches"
    if results and director_norms:
        return None, "needs_review", "no_title_director_match"
    if results:
        return None, "needs_review", "no_exact_title_year_match"
    return None, "unmatched", "none"


def detail_row(movie_key: str, detail: dict) -> dict:
    external_ids = detail.get("external_ids") or {}
    return {
        "movie_key": movie_key,
        "tmdb_id": detail.get("id"),
        "imdb_id": external_ids.get("imdb_id") or "",
        "wikidata_qid": external_ids.get("wikidata_id") or "",
        "original_title": detail.get("original_title") or "",
        "runtime_minutes": detail.get("runtime") or "",
        "original_language": detail.get("original_language") or "",
        "overview": detail.get("overview") or "",
        "poster_path": detail.get("poster_path") or "",
        "homepage": detail.get("homepage") or "",
        "tagline": detail.get("tagline") or "",
        "status": detail.get("status") or "",
        "tmdb_popularity": detail.get("popularity") or "",
        "tmdb_vote_average": detail.get("vote_average") or "",
        "tmdb_vote_count": detail.get("vote_count") or "",
    }


def cast_rows(movie_key: str, detail: dict) -> list[dict]:
    rows = []
    for cast in (detail.get("credits") or {}).get("cast") or []:
        rows.append(
            {
                "movie_key": movie_key,
                "person_name": cast.get("name") or "",
                "tmdb_person_id": cast.get("id") or "",
                "character_name": cast.get("character") or "",
                "credit_order": cast.get("order") if cast.get("order") is not None else "",
                "tmdb_credit_id": cast.get("credit_id") or "",
            }
        )
    return rows


def crew_rows(movie_key: str, detail: dict) -> list[dict]:
    rows = []
    for crew in (detail.get("credits") or {}).get("crew") or []:
        if crew.get("job") != "Director":
            continue
        rows.append(
            {
                "movie_key": movie_key,
                "person_name": crew.get("name") or "",
                "tmdb_person_id": crew.get("id") or "",
                "department": crew.get("department") or "",
                "job": crew.get("job") or "",
                "tmdb_credit_id": crew.get("credit_id") or "",
            }
        )
    return rows


def main() -> None:
    if not MOVIE_IDENTITY_MAP.exists():
        raise FileNotFoundError(
            f"Missing {MOVIE_IDENTITY_MAP}. Run `python -m src.build_model` first."
        )

    client = TMDbClient()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    identity_base = pd.read_csv(MOVIE_IDENTITY_MAP)
    seed = pd.read_csv(STG_MOVIE_SEED)
    seed["release_year"] = pd.to_datetime(seed["release_date"]).dt.year
    seed_lookup = seed[
        ["movie_title", "release_year", "director_1", "director_2"]
    ].drop_duplicates(["movie_title", "release_year"])
    identity = identity_base.merge(seed_lookup, on=["movie_title", "release_year"], how="left")
    manual = read_manual_matches()
    manual_ids = {
        row.movie_key: int(row.tmdb_id)
        for row in manual.itertuples()
        if pd.notna(row.tmdb_id) and str(row.tmdb_id).strip()
    }

    detail_rows = []
    cast_output = []
    crew_output = []
    identity_updates = []

    for row in identity.itertuples():
        if len(identity_updates) and len(identity_updates) % 50 == 0:
            print(f"Processed {len(identity_updates)} / {len(identity)} movies")

        tmdb_id = manual_ids.get(row.movie_key)
        status = "manual" if tmdb_id else ""
        confidence = "manual" if tmdb_id else ""

        if not tmdb_id:
            search = client.search_movie(str(row.movie_title), int(row.release_year))
            tmdb_id, status, confidence = pick_match(
                str(row.movie_title),
                int(row.release_year),
                [row.director_1, row.director_2],
                search.get("results") or [],
                client,
            )
            if not tmdb_id:
                search = client.search_movie(str(row.movie_title))
                tmdb_id, status, confidence = pick_match(
                    str(row.movie_title),
                    int(row.release_year),
                    [row.director_1, row.director_2],
                    search.get("results") or [],
                    client,
                )

        update = {
            "movie_key": row.movie_key,
            "tmdb_id": tmdb_id or "",
            "match_status": status,
            "match_confidence": confidence,
            "imdb_id": "",
            "wikidata_qid": "",
        }

        if tmdb_id:
            detail = client.movie_details(tmdb_id)
            details = detail_row(row.movie_key, detail)
            update["imdb_id"] = details["imdb_id"]
            update["wikidata_qid"] = details["wikidata_qid"]
            detail_rows.append(details)
            cast_output.extend(cast_rows(row.movie_key, detail))
            crew_output.extend(crew_rows(row.movie_key, detail))

        identity_updates.append(update)

    updates = pd.DataFrame(identity_updates)
    merged = identity_base.drop(
        columns=[
            col
            for col in ["tmdb_id", "imdb_id", "wikidata_qid", "match_status", "match_confidence"]
            if col in identity.columns
        ]
    ).merge(updates, on="movie_key", how="left")

    merged.to_csv(MOVIE_IDENTITY_MAP, index=False)
    pd.DataFrame(
        detail_rows,
        columns=[
            "movie_key",
            "tmdb_id",
            "imdb_id",
            "wikidata_qid",
            "original_title",
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
        ],
    ).to_csv(STG_TMDB_MOVIE_DETAILS, index=False)
    pd.DataFrame(
        cast_output,
        columns=[
            "movie_key",
            "person_name",
            "tmdb_person_id",
            "character_name",
            "credit_order",
            "tmdb_credit_id",
        ],
    ).to_csv(STG_TMDB_MOVIE_CAST, index=False)
    pd.DataFrame(
        crew_output,
        columns=[
            "movie_key",
            "person_name",
            "tmdb_person_id",
            "department",
            "job",
            "tmdb_credit_id",
        ],
    ).to_csv(STG_TMDB_MOVIE_CREW, index=False)
    print(f"Wrote {MOVIE_IDENTITY_MAP} ({len(merged)} rows)")
    print(f"Wrote {STG_TMDB_MOVIE_DETAILS} ({len(detail_rows)} rows)")
    print(f"Wrote {STG_TMDB_MOVIE_CAST} ({len(cast_output)} rows)")
    print(f"Wrote {STG_TMDB_MOVIE_CREW} ({len(crew_output)} rows)")


if __name__ == "__main__":
    main()
