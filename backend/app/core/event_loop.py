import asyncio


def selector_loop():
    """Psycopg async requires a SelectorEventLoop on Windows."""
    return asyncio.SelectorEventLoop()
