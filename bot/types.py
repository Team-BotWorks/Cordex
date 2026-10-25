from dataclasses import dataclass
from typing import TYPE_CHECKING

from discord import StageChannel, TextChannel, Thread, VoiceChannel
from discord.app_commands import Command, Group
from discord.ext.commands import Cog

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

GuildMessagable        = TextChannel | StageChannel | VoiceChannel | Thread
GuildMessagableChannel = TextChannel | StageChannel | VoiceChannel

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
    colors : `list[str]`
        The colors of the display name style. Up to five where the effect is either `gradient`, `prism`, or `gummy`, else one.
    """

    font   : DisplayNameFont
    effect : DisplayNameEffect
    colors : list[str]
