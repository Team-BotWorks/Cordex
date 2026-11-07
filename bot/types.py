from dataclasses import dataclass
from string.templatelib import Template
from typing import TYPE_CHECKING, Literal, cast, final, override

from discord import Color, StageChannel, TextChannel, Thread, VoiceChannel
from discord.app_commands import Command, Group
from discord.ext.commands import Cog
from discord.http import Route as BaseRoute

from constants import DisplayNameEffect, DisplayNameFont

if TYPE_CHECKING:
    from typing_extensions import Sentinel as sentinel
else:
    from typing_extensions import (
        sentinel,  # ⸻ For whatever reason, pyright seems to not find the typing-extensions 4.16.0 sentinel function.
    )

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Bot Types
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Route
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
class Route(BaseRoute):
    """Represnts a Discord HTTP route."""

    def __init__(
        self,
        method   : Literal["GET", "POST", "PATCH", "PUT", "DELETE"],
        path     : Template,
        *,
        metadata : str | None = None,
    ) -> None:
        parameters  = {}
        path_string = ""

        for i, interpolation in enumerate(path.interpolations):
            key = interpolation.expression.replace(".", "_")
            path_string += path.strings[i] + "{" + key + "}"
            parameters[key] = cast("object", interpolation.value)

        path_string += path.strings[-1]
        self.path_string = path_string

        super().__init__(
            method,
            path_string,
            metadata = metadata,
            **parameters,
        )

    @override
    def __str__(self) -> str:
        return self.path_string

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# NOT_PASSED Sentinel
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


NOT_PASSED = sentinel("NOT_PASSED")

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# AnnotatedCommand
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

AnnotatedCommand = Command[Group | Cog, ..., object] | Group

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Guild Messagables
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

GuildMessageable        = TextChannel | StageChannel | VoiceChannel | Thread
GuildMessageableChannel = TextChannel | StageChannel | VoiceChannel

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# DisplayNameStyle
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@dataclass(frozen = True, slots = True)
class DisplayNameStyle:
    """
    Represents a display name style.

    Parameters
    ----------
    font : `DisplayNameFont`
        The font of the display name style.
    effect : `DisplayNameEffect`
        The effect of the display name style.
    colors : `list[Color]`
        The colors of the display name style. Up to five where the effect is either `gradient`, `prism`, or `gummy`, else one.
    """

    font   : DisplayNameFont
    effect : DisplayNameEffect
    colors : list[Color]
