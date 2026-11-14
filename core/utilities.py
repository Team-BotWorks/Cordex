from collections.abc import Awaitable, Callable
from typing import Literal

from discord import Member, User
from discord.app_commands import check
from discord.utils import format_dt, utcnow

from bot import (
    Interaction,
    cordex,  # ⸻ Nottt a great practice, but having to pass bot is inconvenient.
)
from constants import DEVELOPER_IDS

type _Styles = Literal["f", "F", "d", "D", "t", "T", "s", "S", "R"]

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Utilities Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# is_bot_owner
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


def is_bot_owner(target : User | Member, /) -> bool:
    """
    Check if a user or member is a bot owner.

    Parameters
    ----------
    target : `User | Member`
        The user or member to check.

    Returns
    -------
    `bool`
        Whether the user or member was a bot owner or not.
    """
    return target.id in DEVELOPER_IDS

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# @unimplemented
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


def unimplemented[F : Callable[..., Awaitable[None]]](func : F) -> F:
    """
    Mark a command as unimplemented.

    Returns
    -------
    `F`
        The command marked as unimplemented.
    """
    def predicate(_interaction : Interaction) -> bool:
        from .exceptions import UnimplementedCommand  # ruff: ignore[import-outside-top-level]
        raise UnimplementedCommand

    return check(predicate)(func)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# format_now
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


def format_now(style : _Styles = "F", /) -> str:
    """
    Format `utcnow` into a discord timestamp.

    Parameters
    ----------
    style : `Literal["f", "F", "d", "D", "t", "T", "s", "S", "R"]`
        The style of the timestamp to create.

    Returns
    -------
    `str`
        The formatted timestamp.
    """
    return format_dt(utcnow(), style)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# format_command
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


def format_command(path : str, /) -> str:
    """
    Format a command path into a clickable mention.

    Parameters
    ----------
    path : `str`
        The path of the command to format into a mention.
    /

    Returns
    -------
    `str`
        The formatted command.

    Raises
    ------
    ValueError
        `path` is empty.
    """
    parts = path.strip().split()
    if not parts:
        error = "path string cannot be empty"
        raise ValueError(error)

    root_name = parts[0]
    root_id   = None

    commands = cordex.get_api_commands_cache()
    for command in commands:
        if command.name == root_name:
            root_id = command.id
            break

    return f"</{path}:{root_id}>" if root_id else f"`/{path}`"

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# format_table
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


def format_table[K, V](table : dict[K, V], /, *, padding : int = 1) -> str:
    """
    Format a dictionary into a table.

    Parameters
    ----------
    table : `dict[K, V]`
        The table to format.
    /
    *
    padding : `int = 1`
        The spacing to apply on the left side of the table.

    Returns
    -------
    `str`
        The formatted table.

    Raises
    ------
    ValueError
        - `table` is empty.
        - `table` contains newlines in any of the keys or values.
    """
    if not table:
        return ""

    if (
        any("\n" in key   for key   in table          if isinstance(key, str)) or
        any("\n" in value for value in table.values() if isinstance(value, str))
    ):
        error = "table dictionary cannot contain newlines"
        raise ValueError(error)

    width = max(len(str(key)) for key in table) + padding
    return "\n".join(f"`{key!s:>{width}}`: {value}" for key, value in table.items())

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# format_values
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


def format_values(
    items   : list[str],
    /,
    *,
    divider : str = ", ",
    conj    : str = "and",
    wrap    : str = "",
) -> str:
    """
    Format a list of items into a readable, oxford-comma style string.

    Parameters
    ----------
    items : `list[str]`
        The list of strings to format.
    /
    *
    divider : `str = ", "`
        The divider between every item.
    conj : `str = "and"`
        The conjunction to use before the very last item.
    wrap : `str = ""`
        The string to wrap every item in.

    Returns
    -------
    `str`
        The formatted values.
    """
    if not items:
        return ""

    items = [f"{wrap}{item}{wrap}" for item in items]

    if len(items) == 1:
        return items[0]

    if len(items) == 2:
        return f"{items[0]} {conj} {items[1]}"

    return f"{divider.join(items[:-1])}{divider.rstrip()} {conj} {items[-1]}"

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# codeblock
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


def codeblock(code : str | Exception, /, *, language : str | None = "py") -> str:
    """
    Format a string or exception into a codbelock.

    Parameters
    ----------
    code : `str | Exception`
        The string or exception to place in a codeblock.
    /
    *
    language : `str | None = "py"`
        The language of the codeblock to use for markdown.

    Returns
    -------
    `str`
        The text in a codeblock.
    """
    return (
       f"```{language or ""}\n"
       f"{code}\n"
        "```"
    )

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# truncate
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


def truncate(text : str, /, *, limit : int = 2000) -> str:
    """
    Truncate a block of text by replacing the last 3 characters before the limit with an ellipsis (...).

    If `text` ends with three backticks, then it will replace the three characters *before* said bacticks to prevent codeblocks from breaking.

    Parameters
    ----------
    text : `str`
        The text to truncate.
    /
    *
    limit : `int = 2000`
        The limit to truncate at.

    Returns
    -------
    `str`
        The truncated text.
    """
    if not len(text) > limit:
        return text

    if limit < 3 or (text.endswith("```") and limit < 6):
        return "..."

    if text.endswith("```"):
        return text[: limit - 6] + "..." + text[-3 :]
    return text[: limit - 3] + "..."
