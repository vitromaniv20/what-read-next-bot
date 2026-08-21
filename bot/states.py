from aiogram.fsm.state import State, StatesGroup


class BookBotStates(StatesGroup):
    choosing_mode = State()           # Main menu / browsing
    waiting_local_search_query = State()  # Waiting for local DB search text
    in_discussion_with_ai = State()   # Chatting about a local DB book
    waiting_global_title = State()    # Waiting for global AI search query
    in_global_ai_critics = State()    # Chatting about a global AI-found book