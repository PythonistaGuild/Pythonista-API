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
from typing import Any, TYPE_CHECKING

from starlette.authentication import requires
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.websockets import WebSocket

import core


if TYPE_CHECKING:
    from api.server import Server


logger: logging.Logger = logging.getLogger(__name__)


class Members(core.View):
    def __init__(self, app: Server) -> None:
        self.app = app

    @core.route('/dpy/modlog', methods=['POST'])
    @requires('member')
    async def post_dpy_modlog(self, request: Request) -> Response:
        application: core.ApplicationModel = request.user.model

        try:
            data = await request.json()
        except Exception as e:
            logger.debug(f'Received bad JSON in "/members/dpy/modlog": {e}')
            return JSONResponse({'error': 'Bad POST JSON Body.'}, status_code=400)

        payload: dict[str, Any] = {
            'op': core.WebsocketOPCodes.EVENT,
            'subscription': core.WebsocketSubscriptions.DPY_MOD_LOG,
            'application': application.uid,
            'application_name': application.name,
            'payload': data
        }

        count = 0
        for subscriber in self.app.subscription_sockets[core.WebsocketSubscriptions.DPY_MOD_LOG]:
            websocket: WebSocket = self.app.sockets[subscriber]

            payload['user_id'] = subscriber

            try:
                await websocket.send_json(data=payload)
            except Exception as e:
                logger.debug(f'Failed to send payload to websocket "{subscriber}": {e}')
            else:
                count += 1

        to_send: dict[str, int] = {
            'subscribers': len(self.app.subscription_sockets[core.WebsocketSubscriptions.DPY_MOD_LOG]),
            'successful': count
        }
        return JSONResponse(to_send, status_code=200)
