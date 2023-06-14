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

from starlette.authentication import requires
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

import core


if TYPE_CHECKING:
    from api.server import Server


class Users(core.View):
    def __init__(self, app: Server) -> None:
        self.app = app

    @core.route('/@me')
    @requires('bearer')
    async def at_me(self, request: Request) -> Response:
        user: core.UserModel = request.user.model

        return JSONResponse(user.as_dict(), status_code=200)

    @core.route('/@me/application')
    @requires('application')
    async def at_me_app(self, request: Request) -> Response:
        application: core.ApplicationModel = request.user.model

        return JSONResponse(application.as_dict(), status_code=200)

    @core.route('/@me/applications')
    @requires('bearer')
    async def at_me_apps(self, request: Request) -> Response:
        uid: int = request.user.model.uid
        applications = await self.app.database.fetch_applications(user_id=uid)

        if not applications:
            applications = []

        apps = [app.as_dict() for app in applications if not app.invalid]
        return JSONResponse(apps, status_code=200)

    @core.route('/@me/logs')
    @requires('bearer')
    async def fetch_application_logs(self, request: Request) -> Response:
        user: core.UserModel = request.user.model

        logs = await self.app.database.fetch_user_logs(user_id=user.uid)

        logs = [log.as_dict() for log in logs]
        return JSONResponse(logs, status_code=200)

    @core.route('/@me/logs/requests')
    @requires('bearer')
    async def fetch_user_requests(self, request: Request) -> Response:
        user: core.UserModel = request.user.model

        data = await self.app.database.fetch_all_user_uses(user_id=user.uid)
        return JSONResponse(data, status_code=200)
