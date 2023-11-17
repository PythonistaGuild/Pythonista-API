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

from __future__ import annotations

import datetime
import itertools
import logging
import pathlib
from typing import TYPE_CHECKING, Any, Self

import asyncpg

import core
from core.config import config

from .models import *

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response

LOGGER: logging.Logger = logging.getLogger(__name__)


class Database:
    _pool: asyncpg.Pool[asyncpg.Record]

    def __init__(self) -> None:
        self.schema_file = pathlib.Path("core/database/SCHEMA.sql")

    async def __aenter__(self) -> Self:
        await self.setup()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._pool.close()

    async def setup(self) -> Self:
        LOGGER.info("Setting up Database.")

        self._pool = await asyncpg.create_pool(dsn=config["DATABASE"]["dsn"])  # type: ignore
        assert self._pool

        async with self._pool.acquire() as connection:
            with self.schema_file.open() as schema:
                await connection.execute(schema.read())

        LOGGER.info("Completed Database Setup.")

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

    async def fetch_applications(self, *, user_id: int) -> list[ApplicationModel] | None:
        query: str = """
        SELECT * FROM tokens
        LEFT OUTER JOIN users u on u.uid = tokens.user_id
        WHERE user_id = $1
        """

        async with self._pool.acquire() as connection:
            rows = await connection.fetch(query, user_id)

        if not rows:
            return None

        apps = [ApplicationModel(r) for r in rows]
        return apps

    async def create_user(self, *, github_id: int, username: str) -> UserModel:
        uid: int = int((datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000) - core.EPOCH)
        bearer: str = core.generate_token(uid)

        query: str = """INSERT INTO users(uid, github_id, username, bearer) VALUES ($1, $2, $3, $4) RETURNING *"""

        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(query, uid, github_id, username, bearer)

        assert row
        return UserModel(record=row)

    async def refresh_or_create_user(self, *, github_id: int, username: str) -> UserModel:
        uid: int = int((datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000) - core.EPOCH)
        bearer: str = core.generate_token(uid)

        query: str = """
        INSERT INTO users(uid, github_id, username, bearer) VALUES ($1, $2, $3, $4)
        ON CONFLICT (github_id) DO UPDATE SET username = $3, bearer = $4 RETURNING *
        """

        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(query, uid, github_id, username, bearer)

        assert row
        return UserModel(record=row)

    async def regenerate_application_token(self, *, user_id: int, old: str) -> ApplicationModel:
        new: str = core.generate_token(user_id)

        query: str = """
        WITH updated_tokens AS (
          UPDATE tokens SET token = $1 WHERE token = $2 RETURNING *
        )
        SELECT * FROM updated_tokens
        JOIN users u ON u.uid = updated_tokens.user_id
        """

        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(query, new, old)

        assert row
        return ApplicationModel(record=row)

    async def delete_application(self, *, token: str) -> None:
        query: str = """UPDATE tokens SET invalid = true WHERE token = $1"""

        async with self._pool.acquire() as connection:
            await connection.execute(query, token)

    async def create_application(self, *, user_id: int, name: str, description: str) -> ApplicationModel:
        token: str = core.generate_token(user_id)

        query: str = """
        WITH create_application AS (
         INSERT INTO tokens(user_id, token_name, token_description, token) VALUES ($1, $2, $3, $4) RETURNING *
        )
        SELECT * FROM create_application
        JOIN users u ON u.uid = create_application.user_id
        """

        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(query, user_id, name, description, token)

        assert row
        return ApplicationModel(record=row)

    async def add_log(self, *, request: Request, response: Response) -> None:
        query: str = """INSERT INTO logs VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)"""

        try:
            body: str | None = str(request._body.decode(encoding="UTF-8"))  # pyright: ignore [reportPrivateUsage]
        except AttributeError:
            body = None

        uid: int | None = None
        tid: int | None = None

        try:
            model: ApplicationModel | UserModel = request.user.model
        except AttributeError:
            pass
        else:
            if isinstance(model, ApplicationModel):
                tid = model.tid
            uid = model.uid

        host: str | None = getattr(request.client, "host", None)
        ip: str | None = request.headers.get("X-Forwarded-For", host)

        async with self._pool.acquire() as connection:
            await connection.execute(
                query,
                ip,
                uid,
                tid,
                datetime.datetime.now(datetime.timezone.utc),
                request.headers.get("CF-RAY"),
                request.headers.get("CF-IPCOUNTRY"),
                request.method.upper(),
                str(request.url.include_query_params()),
                body,
                response.status_code,
            )

    async def fetch_application_logs(self, *, token_id: int) -> list[LogModel]:
        query: str = """SELECT * FROM logs WHERE appid = $1"""

        async with self._pool.acquire() as connection:
            rows = await connection.fetch(query, token_id)

        logs = [LogModel(record=r) for r in rows]
        return logs

    async def fetch_user_logs(self, *, user_id: int) -> list[LogModel]:
        query: str = """SELECT * FROM logs WHERE userid = $1"""

        async with self._pool.acquire() as connection:
            rows = await connection.fetch(query, user_id)

        logs = [LogModel(record=r) for r in rows]
        return logs

    async def fetch_all_user_uses(self, *, user_id: int) -> dict[Any, int]:
        logs = await self.fetch_user_logs(user_id=user_id)
        logs.sort(key=lambda l: (l.tid is None, l.tid))

        grouped = [(k, len(list(group))) for k, group in itertools.groupby(logs, lambda l: l.tid)]
        base = {"total": len(logs)}
        base.update(grouped)  # type: ignore

        return base
