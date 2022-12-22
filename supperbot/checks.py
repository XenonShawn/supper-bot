"""
This file contains a couple of helpful decorators to check if a command can be used.
"""
from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime
from typing import Callable, Any

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler


def cooldown(num: int, per_seconds: float):
    """
    A decorator that adds a cooldown to a command.

    This decorator only allows a command to be used `num` number of times every
    `per_seconds` seconds per user.

    If a cooldown is triggered, the callback_query will be answered with a message
    explaining the cooldown, and a `ConversationHandler.END` will be returned to ensure
    no ConversationHandlers are left on.

    :param num: The number of times the command can be used in the timeframe.
    :param per_seconds: The timeframe in seconds.
    """
    if num <= 0:
        raise ValueError(f"num must be a positive integer.")

    if per_seconds <= 0:
        raise ValueError(f"per_seconds must be positive.")

    # Each user has their own entry in the `timings` dict, accessed by user id.
    timings: dict[int, deque[datetime]] = defaultdict(deque)

    def inner(command: Callable[[Update, ContextTypes.DEFAULT_TYPE], Any]):
        async def coroutine(update: Update, context: ContextTypes.DEFAULT_TYPE):
            now = datetime.now()

            # Remove old timings
            queue = timings[update.effective_user.id]
            while queue and (now - queue[0]).total_seconds() >= per_seconds:
                queue.popleft()

            if len(queue) < num:
                queue.append(now)
                return await command(update, context)

            time_remaining = round(per_seconds - (now - queue[0]).total_seconds())
            await update.callback_query.answer(
                f"This command is under cooldown! "
                f"Time remaining: {time_remaining} second(s)"
            )
            return ConversationHandler.END

        return coroutine

    return inner


def delayed_cooldown(num: int, per_seconds: float):
    """
    A decorator that adds a cooldown to a command. This decorator only allows a command
    to be used `num` number of times every `per_seconds` seconds per user.

    This decorator adds a `add_cooldown` method to the function, and its internal
    counter will only be incremented when this method is called.

    If a cooldown is triggered, the callback_query will be answered with a message
    explaining the cooldown, and a `ConversationHandler.END` will be returned to ensure
    no ConversationHandlers are left on.

    :param num: The number of times the command can be used in the timeframe.
    :param per_seconds: The timeframe in seconds.
    """
    if num <= 0:
        raise ValueError(f"num must be a positive integer.")

    if per_seconds <= 0:
        raise ValueError(f"per_seconds must be positive.")

    class DelayedCooldown:
        def __init__(self, command: Callable[[Update, ContextTypes.DEFAULT_TYPE], Any]):
            # Each user has their own entry in the `timings` dict, accessed by user id.
            self.timings: dict[int, deque[datetime]] = defaultdict(deque)
            self.command = command

        def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            async def helper():
                uses_remaining = self.uses_remaining(update.effective_user.id)
                if uses_remaining > 0:
                    return await self.command(update, context)

                time_remaining = self.time_remaining(update.effective_user.id)
                await update.callback_query.answer(
                    "This command is under cooldown! Time remaining: "
                    f"{time_remaining} second(s)"
                )
                return ConversationHandler.END

            return helper()

        def uses_remaining(self, user_id: int) -> int:
            """
            Returns the number of times the user can use the command.
            """
            now = datetime.now()
            queue = self.timings[user_id]
            while queue and (now - queue[0]).total_seconds() >= per_seconds:
                queue.popleft()

            return num - len(queue)

        def time_remaining(self, user_id: int) -> int:
            """
            Return the time remaining (in seconds) before the cooldown expires.

            Returns 0 if there is no cooldown.
            """
            if self.uses_remaining(user_id) > 0:
                return 0

            now = datetime.now()
            earliest_invocation = self.timings[user_id][0]
            seconds_since = (now - earliest_invocation).total_seconds()
            return max(round(per_seconds - seconds_since), 1)

        def add_cooldown(self, user_id: int):
            """
            Add one usage of the command, with timing set to be the time this method
            is invoked.
            """
            self.timings[user_id].append(datetime.now())

    return DelayedCooldown
