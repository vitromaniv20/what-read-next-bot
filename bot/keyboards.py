from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.localization import LANG_UI

GENRE_KEY_MAP = {
    'sci-fi': 'btn_scifi',
    'historical': 'btn_hist',
    'young_adult': 'btn_ya',
}


def _genre_emoji(genre: str) -> str:
    mapping = {
        'sci-fi': '🚀', 'fantasy': '🐉', 'romance': '❤️', 'mystery': '🕵️',
        'historical': '🏛️', 'young_adult': '🎓', 'horror': '👻', 'nonfiction': '📖',
    }
    return mapping.get(genre, '📚')


def get_genres_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    ui = LANG_UI[lang]
    buttons = []
    genres = ['sci-fi', 'fantasy', 'romance', 'mystery', 'historical', 'young_adult', 'horror', 'nonfiction']
    for g in genres:
        key = GENRE_KEY_MAP.get(g, f"btn_{g}")
        btn_text = ui.get(key, g.replace('_', ' ').title())
        buttons.append([InlineKeyboardButton(text=f"{_genre_emoji(g)} {btn_text}", callback_data=f"targetgenre_{g}")])
    buttons.append([
        InlineKeyboardButton(text=ui.get("btn_random", "🎲 Random Mix"), callback_data="action_random_mix"),
        InlineKeyboardButton(text=ui.get("btn_global_ai", "🌐 Global AI"), callback_data="action_global_ai_search"),
    ])
    buttons.append([
        InlineKeyboardButton(text=ui.get("btn_search", "🔍 Search"), callback_data="action_local_search"),
        InlineKeyboardButton(text=ui.get("btn_favorites", "⭐ Bookmarks"), callback_data="action_my_favorites"),
    ])
    buttons.append([
        InlineKeyboardButton(text=ui.get("btn_change_lang", "🌐 Language"), callback_data="action_change_language"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_books_keyboard(books, lang: str, offset: int, total_count: int) -> InlineKeyboardMarkup:
    ui = LANG_UI[lang]
    buttons = []
    for book in books:
        buttons.append([
            InlineKeyboardButton(
                text=f"📖 {book.title[:30]}{'...' if len(book.title) > 30 else ''}",
                callback_data=f"localbook_{book.id}",
            )
        ])
    nav_buttons = []
    if offset > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"paginate_{offset - 5}"))
    nav_buttons.append(InlineKeyboardButton(text=f"{offset + 1}-{min(offset + 5, total_count)} / {total_count}", callback_data="noop"))
    if offset + 5 < total_count:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"paginate_{offset + 5}"))
    if nav_buttons:
        buttons.append(nav_buttons)
    buttons.append([InlineKeyboardButton(text=ui.get("btn_back", "🔙 Back"), callback_data="action_go_to_genres")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_book_detail_keyboard(book, lang: str, is_favorite: bool, back_callback: str = "return_to_list_0") -> InlineKeyboardMarkup:
    ui = LANG_UI[lang]
    row = []
    if is_favorite:
        row.append(InlineKeyboardButton(text=ui.get("btn_remove_fav", "❌ Remove"), callback_data=f"action_remove_fav_{book.id}"))
    else:
        row.append(InlineKeyboardButton(text=ui.get("btn_add_fav", "⭐ Add"), callback_data=f"action_add_fav_{book.id}"))
    if book.goodreads_query:
        row.append(InlineKeyboardButton(text=ui.get("btn_gr", "📖 Goodreads"), url=f"https://www.goodreads.com/search?q={book.goodreads_query}"))
    keyboard = [
        row,
        [InlineKeyboardButton(text=ui.get("btn_discuss_ai", "💬 AI Critics"), callback_data=f"local_aidiscuss_{book.id}")],
        [InlineKeyboardButton(text=ui.get("btn_back", "🔙 Back"), callback_data=back_callback)],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_discussion_keyboard(lang: str, back_callback: str) -> InlineKeyboardMarkup:
    ui = LANG_UI[lang]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=ui.get("btn_exit_chat", "🔙 Exit Chat"), callback_data=back_callback)],
    ])


def get_discussion_exit_keyboard(lang: str, book_id: int) -> InlineKeyboardMarkup:
    ui = LANG_UI[lang]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=ui.get("btn_exit_chat", "🔙 Exit Chat"), callback_data=f"back_to_card_{book_id}")],
    ])


def get_global_discussion_exit_keyboard(lang: str) -> InlineKeyboardMarkup:
    ui = LANG_UI[lang]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=ui.get("btn_exit_chat", "🔙 Exit Chat"), callback_data="action_go_to_genres")],
    ])


def get_back_to_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    ui = LANG_UI[lang]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=ui.get("btn_back", "🔙 Back"), callback_data="action_go_to_genres")],
    ])


def get_favorites_keyboard(books, lang: str) -> InlineKeyboardMarkup:
    ui = LANG_UI[lang]
    buttons = []
    for book in books:
        buttons.append([
            InlineKeyboardButton(
                text=f"📖 {book.title[:30]}{'...' if len(book.title) > 30 else ''}",
                callback_data=f"favbook_{book.id}",
            )
        ])
    buttons.append([InlineKeyboardButton(text=ui.get("btn_back", "🔙 Back"), callback_data="action_go_to_genres")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_random_books_keyboard(books, lang: str) -> InlineKeyboardMarkup:
    ui = LANG_UI[lang]
    buttons = []
    for book in books:
        buttons.append([
            InlineKeyboardButton(
                text=f"📖 {book.title[:30]}{'...' if len(book.title) > 30 else ''}",
                callback_data=f"localbook_{book.id}",
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="🔄 " + ui.get("btn_refresh", "Ще 5 / New 5"), callback_data="action_random_mix"),
    ])
    buttons.append([InlineKeyboardButton(text=ui.get("btn_back", "🔙 Назад"), callback_data="action_go_to_genres")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_local_search_results_keyboard(books, lang: str) -> InlineKeyboardMarkup:
    ui = LANG_UI[lang]
    buttons = []
    for book in books:
        buttons.append([
            InlineKeyboardButton(
                text=f"📖 {book.title[:30]}{'...' if len(book.title) > 30 else ''}",
                callback_data=f"localbook_{book.id}",
            )
        ])
    buttons.append([InlineKeyboardButton(text=ui.get("btn_back", "🔙 Back"), callback_data="action_go_to_genres")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_ai_books_keyboard(books_data: list, lang: str) -> InlineKeyboardMarkup:
    ui = LANG_UI[lang]
    buttons = []
    for idx, book_str in enumerate(books_data):
        buttons.append([
            InlineKeyboardButton(text=f"📖 {book_str[:30]}{'...' if len(book_str) > 30 else ''}", callback_data=f"select_ai_book_{idx}"),
        ])
    buttons.append([InlineKeyboardButton(text=ui.get("btn_back", "🔙 Back"), callback_data="action_go_to_genres")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇦 Українська", callback_data="setlang_uk")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="setlang_en")],
    ])