from bot import Interaction
from bot.types import GuildMessageableChannel

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /channel permissions Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


async def run_channel_permissions(
    interaction  : Interaction,
    _channel     : GuildMessageableChannel | None = None,
    _perm_filter : str                     | None = None,
) -> None:
    """
    List permissions for a selected channel.

    Parameters
    ----------
    interaction : `Interaction`
        The interaction context to run the command with.
    _channel : `GuildMessageableChannel | None = None`
        The channel to list permissions for.
    _perm_filter : `str | None = None`
        Whether to show enabled or disabled permissions. Defaults to both.
    """
    await interaction.response.defer()

    if not interaction.guild:
        return

    await interaction.followup.send(
        "This command does nothing right now. :[",
        ephemeral = True,
    )
