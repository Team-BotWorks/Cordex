from typing import Self, final

from discord import AllowedMentions, MediaGalleryItem, Member

from bot import Interaction
from bot.ui import Container, MediaGallery, TextDisplay, View
from constants import COLOR_GREY
from core.exceptions import send_bad_argument

from ._base import Scope

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /member banner Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


async def run_member_banner(
    interaction : Interaction,
    member      : Member | None = None,
    scope       : Scope  | None = "global",
) -> None:
    """
    View the banner of a member.

    Parameters
    ----------
    interaction : `Interaction`
        The interaction context to run the command with.
    member : `Member | None = None`
        The member to view the banner for. Defaults to yourself.
    scope : `Scope | None = "global"`
        Whether to view the guild banner or the global banner of the member. Defaults to "global".
    """
    await interaction.response.defer()

    target = member or interaction.user

    guild = interaction.guild
    if not guild or not isinstance(target, Member):
        return

    # ⸻ Determine banner based on server parameter.

    fetched_target = await interaction.client.fetch_user(target.id)
    guild_target   = guild.get_member(target.id) or await guild.fetch_member(target.id)

    banner = (guild_target.guild_banner if scope == "guild" else None) or fetched_target.banner

    if target == interaction.user:
        subtitle = "You do not have a banner set."
        mention  = "Your"
        name     = "your"
    elif target == interaction.client.user:
        subtitle = "I do not have a banner set."
        mention  = "My"
        name     = "my"
    else:
        subtitle = f"{target.mention} does not have a banner set."
        mention  = f"{target.mention}'s"
        name     = f"{target.name}'s"

    if not banner:
        await send_bad_argument(interaction, subtitle = {"member" : subtitle})
        return

    @final
    class BannerView(View):
        container = Container[Self](
            TextDisplay(f"### {mention} Banner"),
            TextDisplay(f"View {name} banner [here]({banner.url})."),
            MediaGallery(MediaGalleryItem(banner.url)),
            color = target.color if target.color.value else COLOR_GREY,
        )

    await interaction.followup.send(view = BannerView(), allowed_mentions = AllowedMentions.none())
