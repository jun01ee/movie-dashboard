from __future__ import annotations

import re

import pandas as pd

from .paths import MANUAL_SEED_CORRECTIONS, PROCESSED_DIR, SEED_WORKBOOK, STG_MOVIE_SEED


SOURCE_COLUMNS = [
    "Movie Title",
    "Release Date",
    "Wikipedia URL",
    "Genre (1)",
    "Genre (2)",
    "Director (1)",
    "Director (2)",
    "Cast (1)",
    "Cast (2)",
    "Cast (3)",
    "Cast (4)",
    "Cast (5)",
    "Budget ($)",
    "Box Office Revenue ($)",
]


def clean_column(name: str) -> str:
    name = name.lower().replace("$", "usd")
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return name.strip("_")


def whole_dollar_series(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="raise")
    rounded = numeric.round()
    if ((numeric.dropna() - rounded.dropna()).abs() > 0.001).any():
        raise ValueError(f"{series.name} contains fractional dollars")
    return rounded.astype("Int64")


def apply_manual_corrections(
    df: pd.DataFrame, corrections: pd.DataFrame | None = None
) -> pd.DataFrame:
    if corrections is None:
        if not MANUAL_SEED_CORRECTIONS.exists():
            return df
        corrections = pd.read_csv(MANUAL_SEED_CORRECTIONS)
    if corrections.empty:
        return df

    df = df.copy()
    for row in corrections.fillna("").itertuples():
        title = str(row.movie_title).strip()
        action = str(row.action).strip().lower()
        mask = df["movie_title"].eq(title)
        if mask.sum() != 1:
            raise ValueError(f"Manual correction for {title!r} matched {mask.sum()} rows")
        if action == "drop":
            df = df.loc[~mask].copy()
        elif action == "update":
            if str(row.release_date).strip():
                df.loc[mask, "release_date"] = pd.to_datetime(row.release_date).date().isoformat()
        else:
            raise ValueError(f"Unsupported manual correction action: {action}")
    return df.reset_index(drop=True)


def load_seed() -> pd.DataFrame:
    if not SEED_WORKBOOK.exists():
        raise FileNotFoundError(
            f"Missing seed workbook: {SEED_WORKBOOK}\n"
            "Copy it from Downloads into data/raw/ before running this command."
        )

    df = pd.read_excel(SEED_WORKBOOK, sheet_name="Movie Data", engine="openpyxl")
    df = df[SOURCE_COLUMNS].copy()
    df.columns = [clean_column(col) for col in SOURCE_COLUMNS]
    df = df.dropna(how="all")
    df["release_date"] = pd.to_datetime(df["release_date"]).dt.date.astype(str)
    df["budget_usd"] = whole_dollar_series(df["budget_usd"])
    df["box_office_revenue_usd"] = whole_dollar_series(df["box_office_revenue_usd"])
    df = apply_manual_corrections(df)
    return df


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df = load_seed()
    df.to_csv(STG_MOVIE_SEED, index=False)
    print(f"Wrote {STG_MOVIE_SEED} ({len(df)} rows)")


if __name__ == "__main__":
    main()
