from __future__ import annotations

from collections import Counter

import pandas as pd

from .build_model import tmdb_movie_key
from .enrich_tmdb import cast_rows, crew_rows, detail_row
from .paths import (
    PROCESSED_DIR,
    STG_MOVIE_SEED,
    STG_TMDB_MOVIE_CAST,
    STG_TMDB_MOVIE_CREW,
    STG_TMDB_MOVIE_DETAILS,
)
from .tmdb_client import TMDbClient


START_YEAR = 2010
END_YEAR = 2025
# ponytail: top 100 revenue-sorted movies/year is a clean dashboard sample, not a completeness claim.
PAGES_PER_YEAR = 5
MAX_GENRES = 6
MAX_DIRECTORS = 2
MAX_CAST = 5
# ponytail: avoid noisy micro-budget/outlier ROI rows; lower this if indie coverage matters.
MIN_BUDGET_USD = 1_000_000


GENRE_COLUMNS = [f"genre_{index}" for index in range(1, MAX_GENRES + 1)]
DIRECTOR_COLUMNS = [f"director_{index}" for index in range(1, MAX_DIRECTORS + 1)]
CAST_COLUMNS = [f"cast_{index}" for index in range(1, MAX_CAST + 1)]
SEED_COLUMNS = [
    "movie_key",
    "tmdb_id",
    "movie_title",
    "release_date",
    "wikipedia_url",
    *GENRE_COLUMNS,
    *DIRECTOR_COLUMNS,
    *CAST_COLUMNS,
    "budget_usd",
    "box_office_revenue_usd",
]


def release_year(detail: dict) -> int | None:
    release_date = detail.get("release_date") or ""
    if str(release_date)[:4].isdigit():
        return int(str(release_date)[:4])
    return None


def names(values: list[dict], key: str = "name", limit: int | None = None) -> list[str]:
    output = []
    for value in values:
        name = value.get(key) or ""
        if name.strip():
            output.append(name.strip())
    return output[:limit]


def directors(detail: dict) -> list[str]:
    crew = (detail.get("credits") or {}).get("crew") or []
    return names(
        [person for person in crew if person.get("job") == "Director"],
        limit=MAX_DIRECTORS,
    )


def cast(detail: dict) -> list[str]:
    return names((detail.get("credits") or {}).get("cast") or [], limit=MAX_CAST)


def seed_row(detail: dict) -> dict | None:
    year = release_year(detail)
    movie_directors = directors(detail)
    movie_cast = cast(detail)
    genres = names(detail.get("genres") or [], limit=MAX_GENRES)
    budget = int(detail.get("budget") or 0)
    revenue = int(detail.get("revenue") or 0)
    title = (detail.get("title") or detail.get("original_title") or "").strip()

    if (
        not detail.get("id")
        or not title
        or not detail.get("release_date")
        or year is None
        or year < START_YEAR
        or year > END_YEAR
        or detail.get("adult")
        or detail.get("status") != "Released"
        or int(detail.get("runtime") or 0) <= 0
        or budget < MIN_BUDGET_USD
        or revenue <= 0
        or not genres
        or not movie_directors
        or not movie_cast
    ):
        return None

    row = {
        "movie_key": tmdb_movie_key(detail["id"]),
        "tmdb_id": int(detail["id"]),
        "movie_title": title,
        "release_date": detail["release_date"],
        "wikipedia_url": "",
        "budget_usd": budget,
        "box_office_revenue_usd": revenue,
    }
    for column, genre in zip(GENRE_COLUMNS, genres):
        row[column] = genre
    for column, director in zip(DIRECTOR_COLUMNS, movie_directors):
        row[column] = director
    for column, actor in zip(CAST_COLUMNS, movie_cast):
        row[column] = actor
    return row


def main() -> None:
    client = TMDbClient()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    seen_tmdb_ids = set()
    seed_rows = []
    detail_rows = []
    cast_output = []
    crew_output = []
    counts = Counter()

    for year in range(START_YEAR, END_YEAR + 1):
        accepted_before = len(seed_rows)
        for page in range(1, PAGES_PER_YEAR + 1):
            discovered = client.discover_movies(year, page)
            results = discovered.get("results") or []
            if not results:
                break
            for result in results:
                tmdb_id = result.get("id")
                if not tmdb_id or tmdb_id in seen_tmdb_ids:
                    continue
                seen_tmdb_ids.add(tmdb_id)
                detail = client.movie_details(int(tmdb_id))
                row = seed_row(detail)
                if row is None:
                    counts["filtered"] += 1
                    continue
                seed_rows.append(row)
                movie_key = row["movie_key"]
                detail_rows.append(detail_row(movie_key, detail))
                cast_output.extend(cast_rows(movie_key, detail))
                crew_output.extend(crew_rows(movie_key, detail))

        print(f"{year}: accepted {len(seed_rows) - accepted_before} movies")

    seed = pd.DataFrame(seed_rows, columns=SEED_COLUMNS).sort_values(
        ["release_date", "movie_title"]
    )
    seed = seed.drop_duplicates("tmdb_id")

    pd.DataFrame(seed, columns=SEED_COLUMNS).to_csv(STG_MOVIE_SEED, index=False)
    pd.DataFrame(detail_rows).drop_duplicates("tmdb_id").to_csv(
        STG_TMDB_MOVIE_DETAILS, index=False
    )
    pd.DataFrame(cast_output).to_csv(STG_TMDB_MOVIE_CAST, index=False)
    pd.DataFrame(crew_output).to_csv(STG_TMDB_MOVIE_CREW, index=False)

    print(f"Wrote {STG_MOVIE_SEED} ({len(seed)} rows)")
    print(f"Wrote {STG_TMDB_MOVIE_DETAILS} ({len(detail_rows)} rows)")
    print(f"Wrote {STG_TMDB_MOVIE_CAST} ({len(cast_output)} rows)")
    print(f"Wrote {STG_TMDB_MOVIE_CREW} ({len(crew_output)} rows)")
    print(f"Filtered {counts['filtered']} incomplete or out-of-scope movies")


if __name__ == "__main__":
    main()
