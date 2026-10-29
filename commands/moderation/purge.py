from discord import Member

from bot import Interaction
from bot.types import GuildMessageable
from core.moderation import ActionType

from ._base import send_moderation_modal

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation purge Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


async def run_moderation_purge(interaction : Interaction, target : Member | None = None) -> None:
    """
    Purge messages from a channel or member.

    Parameters
    ----------
    interaction : `Interaction`
        The interaction context to run the command with.
    target : `Member | None = None`
        The member to purge messages from.
    """
    channel = interaction.channel
    if not isinstance(channel, GuildMessageable):
        return

    await send_moderation_modal(interaction, ActionType.purge, channel, target)
