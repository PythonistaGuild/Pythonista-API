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
from typing import Any

import asyncpg


__all__ = ('UserModel', 'ApplicationModel')


class UserModel:
    def __init__(self, record: asyncpg.Record) -> None:
        self.uid: int = record['uid']
        self.github_id: int = record['github_id']
        self.username: str = record['username']
        self.admin: bool = record['admin']
        self.bearer: str = record['bearer']
        self.created: datetime.datetime = record['created']

    def as_dict(self) -> dict[str, Any]:
        return {
            'uid': self.uid,
            'github_id': self.github_id,
            'username': self.username,
            'admin': self.admin,
            'bearer': self.bearer,
            'created': self.created.isoformat(),
        }


class ApplicationModel(UserModel):
    def __init__(self, record: asyncpg.Record) -> None:
        super().__init__(record)

        self.tid: int = record['tid']
        self.name: str = record['token_name']
        self.description: str = record['token_description']
        self.token: str = record['token']
        self.verified: bool = record['verified']
        self.uses: int = record['uses']

    def as_dict(self) -> dict[str, Any]:
        user = super().as_dict()
        user.update(
            {
                'tid': self.tid,
                'name': self.name,
                'description': self.description,
                'token': self.token,
                'verified': self.verified,
                'uses': self.uses,
            }
        )

        return user
