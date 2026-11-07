"""Error handling, confirmation, timing, and closure-based caching."""

import time
from functools import wraps


def handle_db_errors(func):
    """Report expected database failures without terminating the CLI."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (KeyError, ValueError, FileNotFoundError) as error:
            print(f"Ошибка: {error}")
            return None

    return wrapper


def confirm_action(action_name):
    """Require explicit y confirmation before a destructive operation."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            answer = (
                input(f'Вы уверены, что хотите выполнить "{action_name}"? [y/n]: ')
                .strip()
                .lower()
            )
            if answer != "y":
                print("Операция отменена.")
                return None
            return func(*args, **kwargs)

        return wrapper

    return decorator


def log_time(func):
    """Print the execution duration using a monotonic clock."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        started = time.monotonic()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed = time.monotonic() - started
            print(f"Функция {func.__name__} выполнилась за {elapsed:.3f} секунд")

    return wrapper


def create_cacher():
    """Return a closure that memoizes results by key."""
    cache = {}

    def cache_result(key, value_func):
        if key not in cache:
            cache[key] = value_func()
        return cache[key]

    return cache_result
