from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests

from .build_model import profile_url
from .paths import DIM_PERSON_DETAIL, PROCESSED_DIR
from .tmdb_client import TMDbClient


GENDER_LABELS = {
    0: "Unknown / Not specified",
    1: "Female",
    2: "Male",
    3: "Non-binary",
}


def single_line(value: object) -> str:
    return re.sub(r"[\r\n]+", " ", str(value or "")).strip()


def person_detail_row(person: pd.Series, detail: dict) -> dict:
    gender_code = detail.get("gender")
    path = detail.get("profile_path") or person.get("profile_path") or ""
    biography = single_line(detail.get("biography"))
    return {
        "person_key": person["person_key"],
        "tmdb_person_id": int(detail.get("id") or person["tmdb_person_id"]),
        "biography": biography,
        "biography_available": bool(biography),
        "birthday": detail.get("birthday") or "",
        "deathday": detail.get("deathday") or "",
        "place_of_birth": single_line(detail.get("place_of_birth")),
        "gender_code": gender_code,
        "gender_label": GENDER_LABELS.get(gender_code, "Unknown / Not specified"),
        "profile_path": path,
        "profile_url": profile_url(path),
        "profile_image_available": bool(path),
    }


def fetch_person_detail(client: TMDbClient, tmdb_person_id: int) -> dict:
    try:
        return client.person_details(tmdb_person_id)
    except requests.HTTPError as error:
        if error.response is not None and error.response.status_code == 404:
            return {"id": tmdb_person_id}
        raise


def main() -> None:
    dim_person_path = PROCESSED_DIR / "dim_person.csv"
    if not dim_person_path.exists():
        raise FileNotFoundError(
            f"Missing {dim_person_path}. Run `python -m src.build_model` first."
        )

    people = pd.read_csv(dim_person_path)
    people = people.loc[people["tmdb_person_id"].notna()].copy()
    people["tmdb_person_id"] = people["tmdb_person_id"].astype(int)
    client = TMDbClient()
    rows = []

    # ponytail: fixed pool is enough for this batch; tune only if TMDb throughput changes.
    with ThreadPoolExecutor(max_workers=4) as pool:
        details = pool.map(
            lambda person_id: fetch_person_detail(client, person_id),
            people["tmdb_person_id"],
        )
        for position, ((_, person), detail) in enumerate(
            zip(people.iterrows(), details), start=1
        ):
            rows.append(person_detail_row(person, detail))
            if position % 100 == 0:
                print(f"Processed {position} / {len(people)} people", flush=True)

    output = pd.DataFrame(rows)
    output.to_csv(DIM_PERSON_DETAIL, index=False)
    print(f"Wrote {DIM_PERSON_DETAIL} ({len(output)} rows)")


if __name__ == "__main__":
    main()
