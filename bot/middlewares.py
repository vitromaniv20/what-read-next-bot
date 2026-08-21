import time
from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 0.5):
        self.rate_limit = rate_limit
        self.last_update_time: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        user_id = event.from_user.id
        current_time = time.time()
        if user_id in self.last_update_time:
            if current_time - self.last_update_time[user_id] < self.rate_limit:
                return None
        self.last_update_time[user_id] = current_time
        return await handler(event, data)