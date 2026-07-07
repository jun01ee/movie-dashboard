from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
SEED_WORKBOOK = RAW_DIR / "Movie Data Starter Project.xlsx"
STG_MOVIE_SEED = PROCESSED_DIR / "stg_movie_seed.csv"
