from __future__ import annotations

import json
import os
import time
from hashlib import blake2s
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

from .paths import ROOT, TMDB_CACHE_DIR


class TMDbClient:
    BASE_URL = "https://api.themoviedb.org/3"

    def __init__(self) -> None:
        load_dotenv(ROOT / ".env")
        self.token = os.environ.get("TMDB_BEARER_TOKEN", "").strip()
        if not self.token:
            raise RuntimeError("Missing TMDB_BEARER_TOKEN in .env")
        TMDB_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def get(
        self, endpoint: str, params: dict[str, Any] | None = None, cache_prefix: str = "get"
    ) -> dict[str, Any]:
        params = params or {}
        cache_path = self._cache_path(endpoint, params, cache_prefix)
        if cache_path.exists():
            return json.loads(cache_path.read_text())

        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "accept": "application/json",
        }
        last_error = None
        for attempt in range(3):
            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
            except requests.RequestException as error:
                last_error = error
                time.sleep(2 + attempt)
                continue
            if response.status_code != 429:
                response.raise_for_status()
                data = response.json()
                cache_path.write_text(json.dumps(data, indent=2, sort_keys=True))
                return data
            time.sleep(int(response.headers.get("Retry-After", "2")) + attempt)

        if last_error is not None:
            raise last_error
        response.raise_for_status()
        raise RuntimeError("unreachable")

    def search_movie(self, title: str, year: int | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"query": title, "include_adult": "false"}
        if year is not None:
            params["year"] = year
        return self.get("search/movie", params, "search_movie")

    def discover_movies(self, year: int, page: int) -> dict[str, Any]:
        return self.get(
            "discover/movie",
            {
                "include_adult": "false",
                "include_video": "false",
                "page": page,
                "primary_release_date.gte": f"{year}-01-01",
                "primary_release_date.lte": f"{year}-12-31",
                "sort_by": "revenue.desc",
            },
            "discover_movie",
        )

    def movie_details(self, tmdb_id: int) -> dict[str, Any]:
        return self.get(
            f"movie/{tmdb_id}",
            {"append_to_response": "credits,external_ids"},
            "movie_details",
        )

    def person_details(self, tmdb_person_id: int) -> dict[str, Any]:
        return self.get(f"person/{tmdb_person_id}", cache_prefix="person_details")

    def _cache_path(
        self, endpoint: str, params: dict[str, Any], cache_prefix: str
    ) -> Path:
        payload = json.dumps(
            {"endpoint": endpoint, "params": params}, sort_keys=True, default=str
        )
        digest = blake2s(payload.encode("utf-8"), digest_size=12).hexdigest()
        return TMDB_CACHE_DIR / f"{cache_prefix}_{digest}.json"
