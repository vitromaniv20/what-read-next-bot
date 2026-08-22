import asyncio
import html
import json

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from google import genai

from backend.config import (
    BOT_TOKEN,
    GENAI_API_KEY,
    GEMINI_MODEL,
    MAX_AI_HISTORY,
)
from backend.database import db
from backend.repository import BookRepository
from bot import keyboards as kb
from bot.localization import LANG_UI
from bot.states import BookBotStates

# ── Helpers ──────────────────────────────────────────────────────────
def _esc(text: str) -> str:
    return html.escape(str(text)) if text else ""


async def _safe_callback_answer(callback: CallbackQuery, text: str = None, show_alert: bool = False):
    """Safely answer callback, ignoring expired queries."""
    try:
        await callback.answer(text=text, show_alert=show_alert)
    except Exception:
        pass


async def get_lang(state: FSMContext) -> str:
    data = await state.get_data()
    return data.get("lang", "uk")


async def safe_edit_text(message: Message, text: str, reply_markup=None, parse_mode="HTML"):
    try:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception as e:
        if "message is not modified" in str(e).lower():
            return
        try:
            await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception:
            pass


# ── Global instances ─────────────────────────────────────────────────
repo = BookRepository(db)
client = genai.Client(api_key=GENAI_API_KEY)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ── Gemini Wrapper ───────────────────────────────────────────────────
async def _gemini_generate(contents: str, system_instruction: str) -> str:
    full_prompt = f"{system_instruction}\n\n{contents}"
    loop = asyncio.get_event_loop()
    try:
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model=GEMINI_MODEL,
                contents=full_prompt,
            ),
        )
        return response.text
    except Exception as e:
        print(f"❌ GEMINI ERROR: {type(e).__name__}: {e}")
        raise


# ═════════════════════════════════════════════════════════════════════
#  MENU & LIST RENDERERS
# ═════════════════════════════════════════════════════════════════════

async def render_genres_menu(message: Message, state: FSMContext, edit: bool = False):
    lang = await get_lang(state)
    ui = LANG_UI[lang]
    keyboard = kb.get_genres_keyboard(lang)
    text = ui.get("menu_title", "📚 <b>CyberLibrary PRO</b>\n\nОберіть жанр / Choose a genre:")
    if edit:
        await safe_edit_text(message, text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


async def render_books_list(message: Message, state: FSMContext, genre: str, offset: int):
    lang = await get_lang(state)
    ui = LANG_UI[lang]
    books = repo.get_books_by_genre(genre, offset=offset)
    total_count = repo.get_books_count_by_genre(genre)
    if not books:
        await safe_edit_text(message, ui["feed_empty"], reply_markup=kb.get_back_to_menu_keyboard(lang))
        return
    keyboard = kb.get_books_keyboard(books, lang, offset, total_count)
    title_text = ui["feed_title"].format(genre=genre.upper().replace('_', ' '), count=total_count)
    await safe_edit_text(message, title_text, reply_markup=keyboard)


async def _show_book_detail(message: Message, state: FSMContext, book_id: int, from_favorites: bool):
    lang = await get_lang(state)
    ui = LANG_UI[lang]
    book = repo.get_book_by_id(book_id)
    if not book:
        await message.answer(ui["err_empty"])
        return
    is_fav = repo.is_favorite(message.from_user.id, book_id)
    back_callback = "action_my_favorites" if from_favorites else "return_to_list_0"
    keyboard = kb.get_book_detail_keyboard(book, lang, is_fav, back_callback)
    text = ui["book_card"].format(title=_esc(book.title), author=_esc(book.author), desc=book.short_description)
    await safe_edit_text(message, text, reply_markup=keyboard)


# ═════════════════════════════════════════════════════════════════════
#  HANDLER FUNCTIONS
# ═════════════════════════════════════════════════════════════════════

async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await state.update_data(lang="uk", current_offset=0, current_genre=None)
    await render_genres_menu(message, state, edit=False)


async def cmd_search(message: Message, state: FSMContext):
    lang = await get_lang(state)
    ui = LANG_UI[lang]
    await state.set_state(BookBotStates.waiting_local_search_query)
    await message.answer(ui["search_local_prompt"])


async def cmd_favorites(message: Message, state: FSMContext):
    lang = await get_lang(state)
    ui = LANG_UI[lang]
    books = repo.get_favorites(message.from_user.id)
    if not books:
        await message.answer(ui["fav_empty"], reply_markup=kb.get_back_to_menu_keyboard(lang))
        return
    keyboard = kb.get_favorites_keyboard(books, lang)
    await message.answer(ui["fav_title"], reply_markup=keyboard, parse_mode="HTML")


async def cmd_help(message: Message, state: FSMContext):
    help_text = (
        "<b>🤖 CyberLibrary PRO Commands</b>\n\n"
        "/start — Головне меню / Main Menu\n"
        "/search — Пошук книги в базі / Search Database\n"
        "/favorites — Мої закладки / Bookmarks\n"
        "/help — Допомога / Help"
    )
    await message.answer(help_text, parse_mode="HTML")


async def callback_favorites(callback: CallbackQuery, state: FSMContext):
    await _safe_callback_answer(callback)
    lang = await get_lang(state)
    ui = LANG_UI[lang]
    books = repo.get_favorites(callback.from_user.id)
    if not books:
        await safe_edit_text(callback.message, ui["fav_empty"], reply_markup=kb.get_back_to_menu_keyboard(lang))
    else:
        keyboard = kb.get_favorites_keyboard(books, lang)
        await safe_edit_text(callback.message, ui["fav_title"], reply_markup=keyboard)


async def go_to_genres(callback: CallbackQuery, state: FSMContext):
    await _safe_callback_answer(callback)
    await state.set_state(BookBotStates.choosing_mode)
    await render_genres_menu(callback.message, state, edit=True)


async def handle_genre_selection(callback: CallbackQuery, state: FSMContext):
    await _safe_callback_answer(callback)
    genre_name = callback.data.replace("targetgenre_", "")
    await state.update_data(current_genre=genre_name, current_offset=0)
    await render_books_list(callback.message, state, genre_name, offset=0)


async def process_pagination(callback: CallbackQuery, state: FSMContext):
    await _safe_callback_answer(callback)
    new_offset = int(callback.data.split("_")[1])
    data = await state.get_data()
    genre = data.get("current_genre")
    if genre:
        await state.update_data(current_offset=new_offset)
        await render_books_list(callback.message, state, genre, new_offset)


async def show_random_books(callback: CallbackQuery, state: FSMContext):
    await _safe_callback_answer(callback)
    lang = await get_lang(state)
    ui = LANG_UI[lang]
    books = repo.get_random_books(5)
    if not books:
        await _safe_callback_answer(callback, ui["feed_empty"], show_alert=True)
        return
    keyboard = kb.get_random_books_keyboard(books, lang)
    await safe_edit_text(callback.message, ui["rand_title"], reply_markup=keyboard)


async def show_local_book_details(callback: CallbackQuery, state: FSMContext):
    await _safe_callback_answer(callback)
    book_id = int(callback.data.split("_")[-1])
    from_favorites = callback.data.startswith("favbook_")
    await state.update_data(from_favorites=from_favorites)
    await _show_book_detail(callback.message, state, book_id, from_favorites)


async def return_to_list(callback: CallbackQuery, state: FSMContext):
    await _safe_callback_answer(callback)
    offset = int(callback.data.split("_")[3])
    data = await state.get_data()
    genre = data.get("current_genre")
    if genre:
        await render_books_list(callback.message, state, genre, offset)


async def handle_discussion_entry(callback: CallbackQuery, state: FSMContext):
    await _safe_callback_answer(callback)
    book_id = int(callback.data.split("_")[2])
    lang = await get_lang(state)
    ui = LANG_UI[lang]
    book = repo.get_book_by_id(book_id)
    if not book:
        await _safe_callback_answer(callback, ui["err_empty"], show_alert=True)
        return
    await state.set_state(BookBotStates.in_discussion_with_ai)
    await state.update_data(discussion_book_id=book_id, ai_history=[])
    text = ui["chat_init"].format(title=_esc(book.title), author=_esc(book.author))
    await safe_edit_text(
        callback.message, text, reply_markup=kb.get_discussion_keyboard(lang, f"back_to_card_{book_id}")
    )


async def handle_discussion_exit(callback: CallbackQuery, state: FSMContext):
    await _safe_callback_answer(callback)
    book_id = int(callback.data.split("_")[3])
    lang = await get_lang(state)
    ui = LANG_UI[lang]
    book = repo.get_book_by_id(book_id)
    if not book:
        await _safe_callback_answer(callback, ui["err_empty"], show_alert=True)
        return
    await state.set_state(BookBotStates.choosing_mode)
    await state.update_data(discussion_book_id=None, ai_history=[])
    is_fav = repo.is_favorite(callback.from_user.id, book_id)
    keyboard = kb.get_book_detail_keyboard(book, lang, is_fav)
    text = ui["book_card"].format(title=_esc(book.title), author=_esc(book.author), desc=book.short_description)
    await safe_edit_text(callback.message, text, reply_markup=keyboard)


async def process_db_book_discussion(message: Message, state: FSMContext):
    lang = await get_lang(state)
    ui = LANG_UI[lang]
    data = await state.get_data()
    book_id = data.get("discussion_book_id")
    if not book_id:
        await message.answer(ui["err_empty"])
        return
    book = repo.get_book_by_id(book_id)
    if not book:
        await message.answer(ui["err_empty"])
        return
    history = data.get("ai_history", [])
    history.append({"role": "user", "text": message.text})
    if len(history) > MAX_AI_HISTORY:
        history = history[-MAX_AI_HISTORY:]
    history_text = "\n".join([f"{item.get('role', 'user').upper()}: {item.get('text', '')}" for item in history])
    prompt = ui["ai_sys_critics"].format(
        title=book.title,
        author=book.author,
        description=book.description,
        history=history_text,
        query=message.text,
    )
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    try:
        ai_output = await _gemini_generate(prompt, ui["ai_sys_critics_role"])
        ai_output = ai_output.strip()
    except Exception as e:
        print(f"API Error: {e}")
        ai_output = ui["err_api"]
    history.append({"role": "model", "text": ai_output})
    await state.update_data(ai_history=history)
    await message.answer(ai_output, reply_markup=kb.get_discussion_exit_keyboard(lang, book_id))


async def init_global_ai_search_mode(callback: CallbackQuery, state: FSMContext):
    await _safe_callback_answer(callback)
    lang = await get_lang(state)
    ui = LANG_UI[lang]
    await state.set_state(BookBotStates.waiting_global_title)
    await safe_edit_text(callback.message, ui["search_prompt"], reply_markup=kb.get_back_to_menu_keyboard(lang))


async def handle_global_book_search(message: Message, state: FSMContext):
    lang = await get_lang(state)
    ui = LANG_UI[lang]
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    try:
        sys_instr = ui["ai_sys_search"].format(query=message.text)
        ai_output = await _gemini_generate(message.text, sys_instr)
        ai_output = ai_output.strip()
        if ai_output.startswith("```"):
            ai_output = ai_output.split("```", 2)[-1].strip()
            if ai_output.lower().startswith("json"):
                ai_output = ai_output[4:].strip()
    except Exception as e:
        print(f"API Error: {e}")
        ai_output = "NOT_FOUND"
    if ai_output == "NOT_FOUND" or not ai_output:
        await message.answer(ui["err_empty_ai"], reply_markup=kb.get_back_to_menu_keyboard(lang))
        await state.set_state(BookBotStates.choosing_mode)
        return
    try:
        books = json.loads(ai_output)
        if not isinstance(books, list) or not books:
            raise ValueError("Empty list")
    except Exception:
        await message.answer(ui["err_parse_ai"], reply_markup=kb.get_back_to_menu_keyboard(lang))
        await state.set_state(BookBotStates.choosing_mode)
        return
    await state.update_data(global_ai_books=books)
    keyboard = kb.get_ai_books_keyboard(books, lang)
    await message.answer(ui["search_global_title"], reply_markup=keyboard)
    await state.set_state(BookBotStates.choosing_mode)


async def start_deep_ai_critics_discussion(callback: CallbackQuery, state: FSMContext):
    await _safe_callback_answer(callback)
    idx = int(callback.data.split("_")[3])
    data = await state.get_data()
    books = data.get("global_ai_books", [])
    if not books or idx >= len(books):
        await _safe_callback_answer(callback, "Error", show_alert=True)
        return
    target_book = books[idx]
    await state.set_state(BookBotStates.in_global_ai_critics)
    await state.update_data(global_target_book=target_book, global_ai_history=[])
    lang = await get_lang(state)
    ui = LANG_UI[lang]
    await safe_edit_text(
        callback.message,
        ui["chat_global_init"].format(book=_esc(target_book.replace('|', '—'))),
        reply_markup=kb.get_discussion_keyboard(lang, "action_go_to_genres"),
    )


async def process_global_book_discussion(message: Message, state: FSMContext):
    lang = await get_lang(state)
    ui = LANG_UI[lang]
    data = await state.get_data()
    target_book = data.get("global_target_book")
    if not target_book:
        await message.answer(ui["err_empty"])
        return
    history = data.get("global_ai_history", [])
    history.append({"role": "user", "text": message.text})
    if len(history) > MAX_AI_HISTORY:
        history = history[-MAX_AI_HISTORY:]
    history_text = "\n".join([f"{item.get('role', 'user').upper()}: {item.get('text', '')}" for item in history])
    prompt = ui["ai_sys_global_critics"].format(
        book=target_book,
        history=history_text,
        query=message.text,
    )
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    try:
        ai_output = await _gemini_generate(prompt, ui["ai_sys_critics_role"])
        ai_output = ai_output.strip()
    except Exception as e:
        print(f"API Error: {e}")
        ai_output = ui["err_api"]
    history.append({"role": "model", "text": ai_output})
    await state.update_data(global_ai_history=history)
    await message.answer(ai_output, reply_markup=kb.get_global_discussion_exit_keyboard(lang))


async def init_local_search(callback: CallbackQuery, state: FSMContext):
    await _safe_callback_answer(callback)
    lang = await get_lang(state)
    ui = LANG_UI[lang]
    await state.set_state(BookBotStates.waiting_local_search_query)
    await safe_edit_text(callback.message, ui["search_local_prompt"], reply_markup=kb.get_back_to_menu_keyboard(lang))


async def process_local_search(message: Message, state: FSMContext):
    lang = await get_lang(state)
    ui = LANG_UI[lang]
    books = repo.search_books(message.text)
    if not books:
        await message.answer(ui["search_empty"], reply_markup=kb.get_back_to_menu_keyboard(lang))
        await state.set_state(BookBotStates.choosing_mode)
        return
    keyboard = kb.get_local_search_results_keyboard(books, lang)
    await message.answer(ui["search_local_title"].format(query=_esc(message.text)), reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(BookBotStates.choosing_mode)


async def add_to_favorites(callback: CallbackQuery, state: FSMContext):
    await _safe_callback_answer(callback)
    book_id = int(callback.data.split("_")[3])
    repo.add_to_favorite(callback.from_user.id, book_id)
    lang = await get_lang(state)
    ui = LANG_UI[lang]
    await _safe_callback_answer(callback, ui["fav_added"], show_alert=True)
    data = await state.get_data()
    await _show_book_detail(callback.message, state, book_id, data.get("from_favorites", False))


async def remove_from_favorites(callback: CallbackQuery, state: FSMContext):
    await _safe_callback_answer(callback)
    book_id = int(callback.data.split("_")[-1])
    repo.remove_favorite(callback.from_user.id, book_id)
    lang = await get_lang(state)
    ui = LANG_UI[lang]
    await _safe_callback_answer(callback, ui["fav_removed"], show_alert=True)
    data = await state.get_data()
    if data.get("from_favorites"):
        await callback_favorites(callback, state)
    else:
        await _show_book_detail(callback.message, state, book_id, False)


async def change_lang_callback(callback: CallbackQuery, state: FSMContext):
    await _safe_callback_answer(callback)
    keyboard = kb.get_language_keyboard()
    await safe_edit_text(callback.message, "Please select your language / Оберіть мову:", reply_markup=keyboard)


async def set_language(callback: CallbackQuery, state: FSMContext):
    await _safe_callback_answer(callback)
    selected_lang = callback.data.split("_")[1]
    await state.update_data(lang=selected_lang)
    await _safe_callback_answer(callback, f"Language set to {selected_lang.upper()}")
    await render_genres_menu(callback.message, state, edit=True)


# ═════════════════════════════════════════════════════════════════════
#  REGISTRATION
# ═════════════════════════════════════════════════════════════════════
def register_handlers(dispatcher: Dispatcher):
    dispatcher.message.register(cmd_start, Command("start"))
    dispatcher.message.register(cmd_search, Command("search"))
    dispatcher.message.register(cmd_favorites, Command("favorites"))
    dispatcher.message.register(cmd_help, Command("help"))

    dispatcher.callback_query.register(go_to_genres, F.data == "action_go_to_genres")
    dispatcher.callback_query.register(handle_genre_selection, F.data.startswith("targetgenre_"))
    dispatcher.callback_query.register(process_pagination, F.data.startswith("paginate_"))
    dispatcher.callback_query.register(show_random_books, F.data == "action_random_mix")
    dispatcher.callback_query.register(show_local_book_details, F.data.startswith("localbook_"))
    dispatcher.callback_query.register(show_local_book_details, F.data.startswith("favbook_"))
    dispatcher.callback_query.register(return_to_list, F.data.startswith("return_to_list_"))
    dispatcher.callback_query.register(handle_discussion_entry, F.data.startswith("local_aidiscuss_"))
    dispatcher.callback_query.register(handle_discussion_exit, F.data.startswith("back_to_card_"))
    dispatcher.callback_query.register(init_global_ai_search_mode, F.data == "action_global_ai_search")
    dispatcher.callback_query.register(start_deep_ai_critics_discussion, F.data.startswith("select_ai_book_"))
    dispatcher.callback_query.register(init_local_search, F.data == "action_local_search")
    dispatcher.callback_query.register(add_to_favorites, F.data.startswith("action_add_fav_"))
    dispatcher.callback_query.register(remove_from_favorites, F.data.startswith("action_remove_fav_"))
    dispatcher.callback_query.register(change_lang_callback, F.data == "action_change_language")
    dispatcher.callback_query.register(set_language, F.data.startswith("setlang_"))
    dispatcher.callback_query.register(callback_favorites, F.data == "action_my_favorites")

    dispatcher.message.register(process_db_book_discussion, StateFilter(BookBotStates.in_discussion_with_ai))
    dispatcher.message.register(handle_global_book_search, StateFilter(BookBotStates.waiting_global_title))
    dispatcher.message.register(process_local_search, StateFilter(BookBotStates.waiting_local_search_query))
