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
from typing import Any

import aiohttp
from starlette.authentication import requires
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect

import core

from .middleware.auth import AuthBackend
from .routes.applications import Applications
from .routes.auth import Auth
from .routes.members import Members
from .routes.users import Users


class Server(core.Application):
    def __init__(self, *, session: aiohttp.ClientSession, database: core.Database) -> None:
        self.session = session
        self.database = database

        views: list[core.View] = [Users(self), Auth(self), Applications(self), Members(self)]
        middleware: list[Middleware] = [
            Middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*']),
            Middleware(AuthenticationMiddleware, backend=AuthBackend(self)),
        ]

        self.sockets: dict[int, WebSocket] = {}
        self.subscription_sockets: dict[str, set[int]] = {
            core.WebsocketSubscriptions.DPY_MOD_LOG: set()
        }

        super().__init__(
            prefix=core.config['SERVER']['prefix'],
            views=views,
            middleware=middleware,
            routes=[WebSocketRoute(f'{core.config["SERVER"]["prefix"]}/websocket', self.websocket_connector)]
        )

    @requires('websockets')
    async def websocket_connector(self, websocket: WebSocket) -> None:
        await websocket.accept()

        subs: str = websocket.headers.get('subscriptions', '').replace(' ', '')
        token: str = websocket.headers['authorization']
        uid: int | None = core.id_from_token(token)

        assert uid
        self.sockets[uid] = websocket

        # Filter out bad subscriptions...
        valid: list[str] = list(self.subscription_sockets.keys())
        subscriptions: list[str] = [sub for sub in subs.split(',') if sub in valid]

        # Add the initial websocket subscriptions...
        for sub in subscriptions:
            self.subscription_sockets[sub].add(uid)

        # Send the initial accepted response. Includes user_id and subscriptions... op: 0
        data: dict[str, Any] = {
            'op': core.WebsocketOPCodes.HELLO,
            'user_id': uid,
            'subscriptions': subscriptions
        }
        await websocket.send_json(data=data)

        # Listen for messages from our clients...
        # This keeps the connection alive on our end...
        while True:

            try:
                message: dict[str, Any] = await websocket.receive_json()
            except WebSocketDisconnect:
                break

            op: str | None = message.get('op')

            if op == core.WebsocketOPCodes.SUBSCRIBE:
                response = self.websocket_subscribe(uid=uid, message=message)
                await websocket.send_json(data=response)

            elif op == core.WebsocketOPCodes.UNSUBSCRIBE:
                response = self.websocket_unsubscribe(uid=uid, message=message)
                await websocket.send_json(data=response)

            else:
                response = {
                    'op': core.WebsocketOPCodes.NOTIFICATION,
                    'type': core.WebsocketNotificationTypes.UNKNOWN_OP,
                    'received': op
                }
                await websocket.send_json(data=response)

        # Remove the websocket and it's subscriptions...
        del self.sockets[uid]

        subscribed: list[str] = [sub for sub in self.subscription_sockets if uid in self.subscription_sockets[sub]]
        for sub in subscribed:
            self.subscription_sockets[sub].remove(uid)

    def websocket_subscribe(self, *, uid: int, message: dict[str, Any]) -> dict[str, Any]:
        subs: list[str] = message.get('subscriptions', [])

        # Filter out bad subscriptions...
        valid: list[str] = list(self.subscription_sockets.keys())
        subscriptions: list[str] = [sub for sub in subs if sub in valid]

        for sub in subscriptions:
            self.subscription_sockets[sub].add(uid)

        subscribed: list[str] = [sub for sub in self.subscription_sockets if uid in self.subscription_sockets[sub]]

        data: dict[str, Any] = {
            'op': core.WebsocketOPCodes.NOTIFICATION,
            'type': core.WebsocketNotificationTypes.SUBSCRIPTION_ADDED,
            'user_id': uid,
            'added': subscriptions,
            'subscriptions': subscribed
        }

        return data

    def websocket_unsubscribe(self, *, uid: int, message: dict[str, Any]) -> dict[str, Any]:
        subs: list[str] = message.get('subscriptions', [])

        # Filter out bad subscriptions...
        valid: list[str] = list(self.subscription_sockets.keys())
        subscriptions: list[str] = [sub for sub in subs if sub in valid]

        for sub in subscriptions:
            self.subscription_sockets[sub].remove(uid)

        subscribed: list[str] = [sub for sub in self.subscription_sockets if uid in self.subscription_sockets[sub]]

        data: dict[str, Any] = {
            'op': core.WebsocketOPCodes.NOTIFICATION,
            'type': core.WebsocketNotificationTypes.SUBSCRIPTION_REMOVED,
            'user_id': uid,
            'removed': subscriptions,
            'subscriptions': subscribed
        }

        return data
