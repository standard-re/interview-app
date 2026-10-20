from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import asyncpg


class DatabaseService:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self._database_url)

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[asyncpg.Connection]:
        if self._pool is None:
            raise RuntimeError("Database pool is not connected")

        async with self._pool.acquire() as connection:
            yield connection
