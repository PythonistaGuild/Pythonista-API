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

from typing import TYPE_CHECKING

from starlette.authentication import AuthCredentials, AuthenticationBackend, BaseUser
from starlette.requests import HTTPConnection

import core


if TYPE_CHECKING:
    from api.server import Server


class User(BaseUser):
    def __init__(self, model: core.UserModel) -> None:
        self.model = model


class AuthBackend(AuthenticationBackend):
    def __init__(self, app: Server) -> None:
        self.app = app

    async def authenticate(self, conn: HTTPConnection) -> tuple[AuthCredentials, User] | None:
        auth: str | None = conn.headers.get('authorization')
        if not auth:
            return

        scopes: list[str] = []

        # Check if the user is using a bearer token...
        user = await self.app.database.fetch_user(bearer=auth)

        if user:
            scopes.append('bearer')

        else:
            # Otherwise we check if the authentication token supplied is an Application Token...
            user = await self.app.database.fetch_application(token=auth)
            if not user:
                return

            if user.invalid:
                return

            scopes.append('application')
            if user.verified:
                scopes.append('verified')

        if user.admin:
            scopes.append('admin')

        return AuthCredentials(scopes), User(user)
