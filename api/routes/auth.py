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

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

import core


if TYPE_CHECKING:
    from api.server import Server


logger: logging.Logger = logging.getLogger(__name__)


class Auth(core.View):
    def __init__(self, app: Server) -> None:
        self.app = app

    @core.route('/github', methods=['POST'])
    async def github_auth(self, request: Request) -> Response:
        try:
            data = await request.json()
            code = data.get("code", None)
        except Exception as e:
            logger.debug(f'Bad JSON body in "/auth/github": {e}')

            return JSONResponse({"error": "Bad JSON body passed"}, status_code=421)

        if not code:
            return JSONResponse({"error": "Missing code query"}, status_code=400)

        client_id: str = core.config["OAUTH"]["github_id"]
        client_secret: str = core.config["OAUTH"]["github_secret"]
        url: str = core.config['OAUTH']['redirect']

        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": url,
            "grant_type": "authorization_code",
            "code": code,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        async with self.app.session.post(
            "https://github.com/login/oauth/access_token", data=data, headers=headers
        ) as resp:
            resp.raise_for_status()

            data = await resp.json()

            try:
                token = data["access_token"]
            except KeyError:
                return JSONResponse({'error': 'Bad code query sent.'}, status_code=400)

        async with self.app.session.get(
            "https://api.github.com/user", headers={"Authorization": f"Bearer {token}"}
        ) as resp:
            resp.raise_for_status()

            data = await resp.json()
            userid = data["id"]
            username = data["name"] or data["login"]

        user = await self.app.database.refresh_or_create_user(github_id=userid, username=username)
        logger.info(f'Refreshed Bearer: id={user.uid} github_id={user.github_id} username={username}')

        return JSONResponse(user.as_dict(), status_code=200)
