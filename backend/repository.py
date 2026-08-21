import sqlite3
from typing import List, Optional

from backend.database import Database
from backend.models import Book
from backend.config import BOOKS_PAGE_SIZE


class BookRepository:
    def __init__(self, database: Database):
        self.db = database

    def _row_to_book(self, row: sqlite3.Row) -> Book:
        return Book(
            id=row['id'],
            title=row['title'],
            author=row['author'],
            genre=row['genre'],
            is_famous=row['is_famous'],
            description=row['description'],
            goodreads_query=row['goodreads_query'],
            cover_url=row['cover_url'],
            rating=row['rating'],
            pages=row['pages']
        )

    def get_book_by_id(self, book_id: int) -> Optional[Book]:
        with self.db.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
            row = cursor.fetchone()
            return self._row_to_book(row) if row else None

    def get_books_by_genre(self, genre: str, offset: int = 0, limit: int = BOOKS_PAGE_SIZE) -> List[Book]:
        with self.db.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM books WHERE genre = ? LIMIT ? OFFSET ?", (genre, limit, offset))
            return [self._row_to_book(row) for row in cursor.fetchall()]

    def get_random_books(self, limit: int = BOOKS_PAGE_SIZE) -> List[Book]:
        with self.db.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM books ORDER BY RANDOM() LIMIT ?", (limit,))
            return [self._row_to_book(row) for row in cursor.fetchall()]

    def get_books_count_by_genre(self, genre: str) -> int:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM books WHERE genre = ?", (genre,))
            return cursor.fetchone()[0]

    def search_books(self, query: str, limit: int = 10) -> List[Book]:
        """Case-insensitive search for ALL languages."""
        with self.db.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            pattern = f"%{query}%"
            cursor.execute("""
                SELECT * FROM books 
                WHERE LOWER(title) LIKE LOWER(?) OR LOWER(author) LIKE LOWER(?) 
                LIMIT ?
            """, (pattern, pattern, limit))
            return [self._row_to_book(row) for row in cursor.fetchall()]

    def add_to_favorite(self, user_id: int, book_id: int) -> None:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO user_favorites (user_id, book_id) VALUES (?, ?)
            """, (user_id, book_id))
            conn.commit()

    def remove_favorite(self, user_id: int, book_id: int) -> None:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM user_favorites WHERE user_id = ? AND book_id = ?
            """, (user_id, book_id))
            conn.commit()

    def is_favorite(self, user_id: int, book_id: int) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM user_favorites WHERE user_id = ? AND book_id = ?
            """, (user_id, book_id))
            return cursor.fetchone() is not None

    def get_favorites(self, user_id: int) -> List[Book]:
        with self.db.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT b.* FROM books b
                JOIN user_favorites uf ON b.id = uf.book_id
                WHERE uf.user_id = ?
            """, (user_id,))
            return [self._row_to_book(row) for row in cursor.fetchall()]