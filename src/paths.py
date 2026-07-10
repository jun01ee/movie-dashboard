from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
MANUAL_DIR = ROOT / "data" / "manual"
TMDB_CACHE_DIR = RAW_DIR / "api_cache" / "tmdb"
SEED_WORKBOOK = RAW_DIR / "Movie Data Starter Project.xlsx"
STG_MOVIE_SEED = PROCESSED_DIR / "stg_movie_seed.csv"
STG_TMDB_MOVIE_DETAILS = PROCESSED_DIR / "stg_tmdb_movie_details.csv"
STG_TMDB_MOVIE_CAST = PROCESSED_DIR / "stg_tmdb_movie_cast.csv"
STG_TMDB_MOVIE_CREW = PROCESSED_DIR / "stg_tmdb_movie_crew.csv"
MOVIE_IDENTITY_MAP = PROCESSED_DIR / "movie_identity_map.csv"
MANUAL_TMDB_MATCHES = MANUAL_DIR / "tmdb_movie_matches.csv"
MANUAL_SEED_CORRECTIONS = MANUAL_DIR / "movie_seed_corrections.csv"
