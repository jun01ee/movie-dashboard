from src.build_model import profile_url
from src.enrich_tmdb import cast_rows, detail_row, pick_match
from src.enrich_tmdb_people import fetch_person_detail, person_detail_row
import requests


class FakeClient:
    def __init__(self, details):
        self.details = details

    def movie_details(self, tmdb_id):
        return self.details[tmdb_id]


def detail(release_date, director):
    return {
        "release_date": release_date,
        "credits": {"crew": [{"job": "Director", "name": director}]},
    }


def test_title_director_match_allows_small_release_year_difference():
    client = FakeClient({207703: detail("2015-01-24", "Matthew Vaughn")})

    assert pick_match(
        "Kingsman: The Secret Service",
        2014,
        ["Matthew Vaughn"],
        [{"id": 207703, "title": "Kingsman: The Secret Service"}],
        client,
    ) == (207703, "matched", "title_director")


def test_title_director_match_flags_large_release_year_difference():
    client = FakeClient({744: detail("1986-05-16", "Tony Scott")})

    assert pick_match(
        "Top Gun 3D",
        2013,
        ["Tony Scott"],
        [{"id": 744, "title": "Top Gun"}],
        client,
    ) == (None, "needs_review", "release_year_gap_gt_2")


def test_cast_rows_keep_profile_path_for_person_images():
    rows = cast_rows(
        "mov_tmdb_1",
        {
            "credits": {
                "cast": [
                    {
                        "name": "Actor Name",
                        "id": 123,
                        "profile_path": "/actor.jpg",
                    }
                ]
            }
        },
    )

    assert rows[0]["profile_path"] == "/actor.jpg"


def test_profile_url_is_blank_when_profile_path_is_missing():
    assert profile_url("") == ""
    assert profile_url("/actor.jpg") == "https://image.tmdb.org/t/p/w185/actor.jpg"


def test_detail_row_removes_newlines_from_long_text():
    row = detail_row(
        "mov_tmdb_1",
        {
            "id": 1,
            "external_ids": {},
            "overview": "first line\rsecond line\nthird line",
            "tagline": "tag\rline",
        },
    )

    assert row["overview"] == "first line second line third line"
    assert row["tagline"] == "tag line"


def test_person_detail_row_keeps_semantic_model_key_and_fallback_image():
    row = person_detail_row(
        {
            "person_key": "per_actor_123",
            "tmdb_person_id": 123,
            "profile_path": "/fallback.jpg",
        },
        {
            "id": 123,
            "biography": "first line\nsecond line",
            "gender": 2,
        },
    )

    assert row["person_key"] == "per_actor_123"
    assert row["biography"] == "first line second line"
    assert row["gender_label"] == "Male"
    assert row["profile_url"].endswith("/fallback.jpg")


def test_missing_tmdb_person_returns_fallback_detail():
    response = requests.Response()
    response.status_code = 404

    class MissingPersonClient:
        def person_details(self, tmdb_person_id):
            raise requests.HTTPError(response=response)

    assert fetch_person_detail(MissingPersonClient(), 6321600) == {"id": 6321600}
