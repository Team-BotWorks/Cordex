from pathlib import Path
from string.templatelib import Template
from typing import cast, override

from aiosqlite import Connection as AiosqliteConnection
from aiosqlite import Cursor
from aiosqlite import connect as aiosqlite_connect
from aiosqlite.context import Result

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# State Base
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


class Connection(AiosqliteConnection):
    @override
    def execute(self, sql : Template, /) -> Result[Cursor]:
        return super().execute("?".join(sql.strings), sql.values)

    def base_execute(self, sql : str, parameters : list[object] | None = None, /) -> Result[Cursor]:
        if parameters is None:
            parameters = []

        return super().execute(sql, parameters)


async def connect(database : str | Path) -> Connection:
    raw_connection = await aiosqlite_connect(database)

    connection = cast("Connection", raw_connection)
    connection.__class__ = Connection
    return connection
