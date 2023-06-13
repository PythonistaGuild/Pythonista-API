"""MIT License

Copyright (c) 2023 PythonistaGuild

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import datetime
import logging
from typing import Any, Self

import asyncpg

import core
from core.config import config

from .models import *


logger: logging.Logger = logging.getLogger(__name__)


class Database:
    _pool: asyncpg.Pool[asyncpg.Record]

    async def __aenter__(self) -> Self:
        await self.setup()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._pool.close()

    async def setup(self) -> Self:
        logger.info('Setting up Database.')

        self._pool = await asyncpg.create_pool(dsn=config['DATABASE']['dsn'])  # type: ignore
        assert self._pool

        async with self._pool.acquire() as connection:
            with open('core/database/SCHEMA.sql', 'r') as schema:
                await connection.execute(schema.read())

        logger.info('Completed Database Setup.')

        return self

    async def fetch_user(
        self, *, uid: int | None = None, bearer: str | None = None, github_id: int | None = None
    ) -> UserModel | None:
        query: str = """SELECT * FROM users WHERE uid = $1 OR bearer = $2 OR github_id = $3"""

        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(query, uid, bearer, github_id)

        if not row:
            return None

        return UserModel(record=row)

    async def fetch_application(self, *, token: str) -> ApplicationModel | None:
        query: str = """
        SELECT * FROM tokens
        LEFT OUTER JOIN users u on u.uid = tokens.user_id
        WHERE token = $1
        """

        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(query, token)

        if not row:
            return None

        return ApplicationModel(record=row)

    async def create_user(self, *, github_id: int) -> UserModel:
        uid: int = int((datetime.datetime.utcnow().timestamp() * 1000) - core.EPOCH)
        bearer: str = core.generate_token(uid)

        query: str = """INSERT INTO users(uid, github_id, bearer) VALUES ($1, $2, $3) RETURNING *"""

        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(query, uid, github_id, bearer)

        assert row
        return UserModel(record=row)
