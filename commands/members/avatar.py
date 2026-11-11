from typing import Self, final

from discord import AllowedMentions, MediaGalleryItem, Member

from bot import Interaction
from bot.ui import Container, MediaGallery, TextDisplay, View
from constants import COLOR_GREY
from core.exceptions import send_bad_argument

from ._base import Scope

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /member avatar Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


async def run_member_avatar(
    interaction : Interaction,
    member      : Member | None = None,
    scope       : Scope  | None = "global",
) -> None:
    """
    View the avatar of a member.

    Parameters
    ----------
    interaction : `Interaction`
        The interaction context to run the command with.
    member : `Member | None = None`
        The member to view the avatar for. Defaults to yourself.
    scope : `Scope | None = "global"`
        Whether to view the guild avatar or the global avatar of the member. Defaults to "global".
    """
    await interaction.response.defer()

    target = member or interaction.user

    guild = interaction.guild
    if not guild or not isinstance(target, Member):
        return

    # ⸻ Determine avatar based on server parameter.

    fetched_target = await interaction.client.fetch_user(target.id)
    guild_target   = guild.get_member(target.id) or await guild.fetch_member(target.id)

    avatar = (guild_target.guild_avatar if scope == "guild" else None) or fetched_target.avatar

    if target == interaction.user:
        subtitle = "You do not have an avatar set."
        mention  = "Your"
        name     = "your"
    elif target == interaction.client.user:
        subtitle = "I do not have an avatar set."
        mention  = "My"
        name     = "my"
    else:
        subtitle = f"{target.mention} does not have an avatar set."
        mention  = f"{target.mention}'s"
        name     = f"{target.name}'s"

    if not avatar:
        await send_bad_argument(interaction, subtitle = {"member" : subtitle})
        return

    @final
    class AvatarView(View):
        container = Container[Self](
            TextDisplay(f"### {mention} Avatar"),
            TextDisplay(f"View {name} avatar [here]({avatar.url})."),
            MediaGallery(MediaGalleryItem(avatar.url)),
            color = target.color if target.color.value else COLOR_GREY,
        )

    await interaction.followup.send(view = AvatarView(), allowed_mentions = AllowedMentions.none())
