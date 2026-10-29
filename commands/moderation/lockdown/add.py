from bot import Interaction
from bot.types import GuildMessageableChannel
from commands.moderation._base import send_moderation_modal
from core.exceptions import send_bad_argument
from core.moderation import ActionType

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation lockdown add Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


async def run_moderation_lockdown_add(interaction : Interaction) -> None:
    """
    Add a channel to lockdown.

    Parameters
    ----------
    interaction : `Interaction`
        The interaction context to run the command with.
    """
    channel = interaction.channel
    if not isinstance(channel, GuildMessageableChannel):
        await send_bad_argument(interaction, subtitle = {None : "Threads cannot be locked down."})
        return

    await send_moderation_modal(interaction, ActionType.lockdown_add, channel)
