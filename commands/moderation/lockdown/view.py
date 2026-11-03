from discord import AllowedMentions

from bot import Interaction
from core.moderation import Actions
from core.responses import FormatOverride, MessageType, format_send

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation lockdown view Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


async def run_moderation_lockdown_view(interaction : Interaction) -> None:
    """
    View all channels in lockdown.

    Parameters
    ----------
    interaction : `Interaction`
        The interaction context to run the command with.
    """
    guild = interaction.guild
    if not guild:
        return

    actions = Actions(interaction.client, guild)
    paginator = await actions.lockdown_view()
    if not paginator:
        await format_send(
            interaction,
            MessageType.success,
            title    = "No channels are in lockdown",
            override = FormatOverride(prefix = False),
        )
        return

    await interaction.response.send_message(
        view             = paginator,
        ephemeral        = True,
        allowed_mentions = AllowedMentions.none(),
    )
