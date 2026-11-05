from datetime import datetime
from pathlib import Path
from sqlite3 import PARSE_COLNAMES as SQLITE3_PARSE_COLNAMES
from sqlite3 import PARSE_DECLTYPES as SQLITE3_PARSE_DECLTYPES
from sqlite3 import register_converter
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
    register_converter("TIMESTAMP", lambda v : datetime.fromisoformat(v.decode("utf-8")))

    raw_connection = await aiosqlite_connect(database, detect_types = SQLITE3_PARSE_DECLTYPES | SQLITE3_PARSE_COLNAMES)

    connection = cast("Connection", raw_connection)
    connection.__class__ = Connection
    return connection
