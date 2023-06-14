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

import logging
from typing import TYPE_CHECKING

import asyncpg
from starlette.authentication import requires
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

import core


if TYPE_CHECKING:
    from api.server import Server


logger: logging.Logger = logging.getLogger(__name__)


class Applications(core.View):
    def __init__(self, app: Server) -> None:
        self.app = app

    @core.route('/regenerate')
    @requires('application')
    async def regenerate_application_token(self, request: Request) -> Response:
        app: core.ApplicationModel = request.user.model

        new = await self.app.database.regenerate_application_token(user_id=app.uid, old=app.token)
        return JSONResponse(new.as_dict(), status_code=200)

    @core.route('/delete', methods=['DELETE'])
    @requires('application')
    async def delete_application(self, request: Request) -> Response:
        app: core.ApplicationModel = request.user.model

        await self.app.database.delete_application(token=app.token)
        return Response(status_code=200)

    @core.route('/create', methods=['POST'])
    @requires('bearer')
    async def create_application(self, request: Request) -> Response:
        user: core.UserModel = request.user.model

        try:
            data = await request.json()
            name: str = data['name']
            description: str = data['description']
        except Exception as e:
            logger.debug(f'Received bad JSON in "/api/applications/create": {e}')
            return JSONResponse({'error': 'Bad POST JSON Body.'}, status_code=400)

        if len(name) < 3 or len(name) > 32:
            return JSONResponse({'error': 'name field must be between 3 and 32 characters long.'}, status_code=400)

        if len(description) > 512:
            return JSONResponse({'error': 'description field must not be over 512 characters long.'}, status_code=400)

        apps = await self.app.database.fetch_applications(user_id=user.uid)

        if not apps:
            pass

        elif len(apps) >= 25:
            return JSONResponse({'error': 'You have too many applications.'}, status_code=200)

        try:
            app = await self.app.database.create_application(user_id=user.uid, name=name, description=description)
        except asyncpg.UniqueViolationError:
            return JSONResponse({'error': 'You already have an application with that name.'}, status_code=409)

        return JSONResponse(app.as_dict(), status_code=201)
