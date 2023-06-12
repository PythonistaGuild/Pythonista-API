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
import asyncio
import inspect
from typing import Any, Awaitable, Callable, Iterator, Self

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route
from starlette.types import Receive, Scope, Send


__all__ = (
    'route',
    'View',
)


class _Route:

    def __init__(self, **kwargs) -> None:
        self._path: str = kwargs['path']
        self._coro: Callable[[Any, Request], Awaitable[Response]] = kwargs['coro']
        self._methods: list[str] = kwargs['methods']
        self._prefix: bool = kwargs['prefix']

        self._view: View | None = None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        request = Request(scope, receive, send)

        response = await self._coro(self._view, request)
        await response(scope, receive, send)


def route(path: str, /, *, methods: list[str], prefix: bool = True) -> Callable[..., _Route]:
    """Decorator which allows a coroutine to be turned into a `starlette.routing.Route` inside a `core.View`.

    Parameters
    ----------
    path: str
        The path to this route. By default, the path is prefixed with the View class name.
    methods: list[str]
        The allowed methods for this route.
    prefix: bool
        Whether the route path should be prefixed with the View class name. Defaults to True.
    """

    def decorator(coro: Callable[[Any, Request], Awaitable[Response]]) -> _Route:
        if not asyncio.iscoroutinefunction(coro):
            raise RuntimeError(f'Route must be a coroutine function.')

        return _Route(path=path, coro=coro, methods=methods, prefix=prefix)
    return decorator


class View:
    """Class based view for Starlette which allows use of the `core.route` decorator.

    All methods decorated with `core.route` are eventually turned into `starlette.routing.Route` which can be added to
    a Starlette app as a route.

    All decorated routes will have their path prefixed with the class name by default. Set `prefix=False`
    in the decorator to disable this.

    For example:

        class Stuff(View):

            @route('/hello', methods=['GET'])
            async def hello_endpoint(self, request: Request) -> Response:
                return Response(status_code=200)

        # The above View 'Stuff' has a route '/hello'. Since prefix=True by default, the full path to this route
        # is '/stuff/hello'.

    Calling `list()` on a view instance will return a list of the `starlette.routing.Route`'s in this instance.
    """

    __routes__: list[Route]

    def __new__(cls, *args, **kwargs) -> Self:
        self: Self = super().__new__(cls)
        name: str = cls.__name__

        self.__routes__ = []

        for _, member in inspect.getmembers(self, predicate=lambda m: isinstance(m, _Route)):
            member._view = self
            path: str = member._path

            if member._prefix:
                path = f'/{name.lower()}/{path.lstrip("/")}'

            self.__routes__.append(Route(path=path, endpoint=member, methods=member._methods))

        return self

    def __repr__(self) -> str:
        return f'View: name={self.__class__.__name__}, routes={self.__routes__}'

    def __getitem__(self, index: int) -> Route:
        return self.__routes__[index]

    def __len__(self) -> int:
        return len(self.__routes__)

    def __iter__(self) -> Iterator:
        return iter(self.__routes__)
