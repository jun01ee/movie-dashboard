from src.enrich_tmdb import pick_match


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
