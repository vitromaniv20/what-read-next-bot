import ast
import sqlite3
from pathlib import Path

import pandas as pd

from backend.config import CSV_PATH, DB_PATH


class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _map_genre(self, raw_genres) -> str:
        """Convert ['Young Adult', 'Fantasy'] → 'young_adult' etc."""
        PRIORITY = {
            'science fiction': 'sci-fi', 'sci-fi': 'sci-fi', 'dystopia': 'sci-fi',
            'post apocalyptic': 'sci-fi', 'cyberpunk': 'sci-fi', 'apocalyptic': 'sci-fi',
            'fantasy': 'fantasy', 'magic': 'fantasy', 'supernatural': 'fantasy',
            'romance': 'romance', 'historical romance': 'romance', 'love': 'romance',
            'mystery': 'mystery', 'thriller': 'mystery', 'crime': 'mystery',
            'suspense': 'mystery', 'detective': 'mystery',
            'historical': 'historical', 'historical fiction': 'historical',
            'history': 'historical', 'war': 'historical',
            'young adult': 'young_adult', 'ya': 'young_adult', 'teen': 'young_adult',
            'juvenile': 'young_adult', 'coming of age': 'young_adult',
            'horror': 'horror', 'ghost': 'horror', 'paranormal': 'horror',
            'nonfiction': 'nonfiction', 'non-fiction': 'nonfiction',
            'biography': 'nonfiction', 'memoir': 'nonfiction', 'self-help': 'nonfiction',
        }
        if pd.isna(raw_genres):
            return 'fantasy'
        try:
            genres = ast.literal_eval(str(raw_genres))
            if not isinstance(genres, list):
                genres = str(raw_genres).split(',')
        except Exception:
            genres = str(raw_genres).split(',')
        for g in (x.strip().lower() for x in genres):
            if g in PRIORITY:
                return PRIORITY[g]
        return 'fantasy'

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    genre TEXT NOT NULL,
                    is_famous INTEGER DEFAULT 0,
                    description TEXT,
                    goodreads_query TEXT,
                    cover_url TEXT,
                    rating REAL,
                    pages INTEGER
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_favorites (
                    user_id INTEGER NOT NULL,
                    book_id INTEGER NOT NULL,
                    PRIMARY KEY (user_id, book_id),
                    FOREIGN KEY (book_id) REFERENCES books(id)
                )
            ''')
            # Speed indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_books_genre ON books(genre)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_books_title ON books(title)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_books_author ON books(author)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_favorites_user ON user_favorites(user_id)')
            conn.commit()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def is_empty(self) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM books")
            return cursor.fetchone()[0] == 0

    def import_from_csv(self, csv_path: Path = CSV_PATH):
        if not csv_path.exists():
            print(f"❌ CSV not found: {csv_path}")
            return
        print(f"⏳ Loading dataset from {csv_path.name}...")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM books')
            cursor.execute('DELETE FROM user_favorites')
            total = 0
            for chunk in pd.read_csv(csv_path, chunksize=5000, low_memory=False, encoding='utf-8'):
                chunk.columns = chunk.columns.str.lower()
                chunk = chunk.where(pd.notnull(chunk), None)
                for _, row in chunk.iterrows():
                    # Pages: extract digits from "324 pages" or "1 page"
                    pages_raw = row.get('pages')
                    try:
                        if pd.isna(pages_raw):
                            pages_val = None
                        else:
                            digits = ''.join(c for c in str(pages_raw) if c.isdigit())
                            pages_val = int(digits) if digits else None
                    except Exception:
                        pages_val = None

                    # Rating
                    try:
                        rating_val = float(row['rating']) if pd.notna(row.get('rating')) else None
                    except Exception:
                        rating_val = None

                    # Genre mapping
                    mapped_genre = self._map_genre(row.get('genres'))

                    # Famous flag
                    is_famous = 0
                    if str(row.get('is_famous', '')).lower() in ['true', '1', 'yes']:
                        is_famous = 1
                    elif 'numRatings' in row and pd.notna(row.get('numRatings')):
                        try:
                            is_famous = 1 if int(row['numRatings']) > 10000 else 0
                        except Exception:
                            pass

                    cursor.execute('''
                        INSERT INTO books (title, author, genre, is_famous, description, goodreads_query, cover_url, rating, pages)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        row.get('title'), row.get('author'), mapped_genre,
                        is_famous,
                        row.get('description'), row.get('coverimg'), row.get('coverimg'),
                        rating_val, pages_val,
                    ))
                    total += 1
                conn.commit()
                print(f"   ... imported {total} books so far")
            conn.commit()
        print("✅ Dataset imported successfully.")
        # Show genre distribution
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT genre, COUNT(*) FROM books GROUP BY genre")
            print("\n📊 Genre distribution:")
            for g, c in cursor.fetchall():
                print(f"   {g}: {c}")


db = Database()