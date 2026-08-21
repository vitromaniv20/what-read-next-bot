import os
from pathlib import Path

from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / "data" / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set! Add it to your .env file.")

GENAI_API_KEY = os.getenv("GENAI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

BASE_DIR = Path(__file__).resolve().parent.parent

# Resolve CSV_PATH relative to project root if it's a relative path
csv_env = os.getenv("CSV_PATH")
if csv_env:
    _csv_path = Path(csv_env)
    CSV_PATH = _csv_path if _csv_path.is_absolute() else BASE_DIR / _csv_path
else:
    CSV_PATH = BASE_DIR / "data" / "books.csv"

db_env = os.getenv("DB_PATH")
if db_env:
    _db_path = Path(db_env)
    DB_PATH = _db_path if _db_path.is_absolute() else BASE_DIR / _db_path
else:
    DB_PATH = BASE_DIR / "data" / "books.db"

RATING_THRESHOLD = 3.5
PAGES_THRESHOLD = 100
MAX_AI_HISTORY = 10
BOOKS_PAGE_SIZE = 5

GENRE_MAPPING = {
    'sci-fi': ['science fiction', 'sci-fi', 'dystopia', 'post apocalyptic'],
    'fantasy': ['fantasy', 'magic', 'supernatural'],
    'romance': ['romance', 'love', 'historical romance'],
    'mystery': ['mystery', 'thriller', 'crime', 'suspense', 'detective'],
    'historical': ['historical', 'historical fiction', 'history', 'war'],
    'young_adult': ['young adult', 'ya', 'teen', 'juvenile', 'coming of age'],
    'horror': ['horror', 'ghost', 'paranormal'],
    'nonfiction': ['nonfiction', 'non-fiction', 'biography', 'memoir', 'self-help'],
}