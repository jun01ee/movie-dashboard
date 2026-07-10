import pandas as pd

from src.load_seed import apply_manual_corrections


def test_apply_manual_corrections_updates_dates_and_drops_rows():
    seed = pd.DataFrame(
        [
            {"movie_title": "Monster Hunt", "release_date": "2016-01-22"},
            {"movie_title": "Top Gun 3D", "release_date": "2013-02-08"},
        ]
    )
    corrections = pd.DataFrame(
        [
            {
                "movie_title": "Monster Hunt",
                "action": "update",
                "release_date": "2015-07-16",
            },
            {"movie_title": "Top Gun 3D", "action": "drop", "release_date": ""},
        ]
    )

    corrected = apply_manual_corrections(seed, corrections)

    assert corrected.to_dict("records") == [
        {"movie_title": "Monster Hunt", "release_date": "2015-07-16"}
    ]
