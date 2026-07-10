from src.load_tmdb_seed import seed_row


def detail(**overrides):
    base = {
        "id": 1,
        "title": "Clean Movie",
        "original_title": "Clean Movie",
        "release_date": "2020-01-01",
        "adult": False,
        "status": "Released",
        "runtime": 100,
        "budget": 10_000_000,
        "revenue": 50_000_000,
        "genres": [{"name": "Drama"}],
        "credits": {
            "crew": [{"job": "Director", "name": "Director Name"}],
            "cast": [{"name": "Actor Name"}],
        },
    }
    base.update(overrides)
    return base


def test_seed_row_keeps_clean_tmdb_movie():
    row = seed_row(detail())

    assert row["movie_key"] == "mov_tmdb_1"
    assert row["movie_title"] == "Clean Movie"
    assert row["release_date"] == "2020-01-01"
    assert row["genre_1"] == "Drama"
    assert row["director_1"] == "Director Name"
    assert row["cast_1"] == "Actor Name"


def test_seed_row_filters_incomplete_movie():
    assert seed_row(detail(revenue=0)) is None
