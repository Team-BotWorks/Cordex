from typing import Self, final

from discord import AllowedMentions, MediaGalleryItem, Member
from discord.utils import escape_markdown, format_dt, utcnow

from bot import Interaction
from bot.ui import (
    Container,
    MediaGallery,
    TextDisplay,
    Thumbnail,
    ThumbnailSection,
    View,
)
from constants import (
    ASTERISK_EMOJI,
    BIG_BOT_EMOJI,
    BOOSTER_EMOJI,
    COLOR_GREY,
    DEVELOPER_EMOJI,
    EMPLOYEE_EMOJI,
    MODERATION_EMOJI,
    OWNER_EMOJI,
    PARTNER_EMOJI,
    PET_CORDEX_EMOJI,
)
from core.utilities import codeblock, format_table, is_bot_owner

from ._base import Scope

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /member info Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


async def run_member_info(
    interaction : Interaction,
    member      : Member | None = None,
    scope       : Scope  | None = "global",
) -> None:
    """
    View information for a member.

    Parameters
    ----------
    interaction : `Interaction`
        The interaction context to run the command with.
    member : `Member | None = None`
        The member to view information for. Defaults to yourself.
    scope : `Scope | None = "global"`
        Whether to view the guild profile or the global profile of the member. Defaults to "global".
    """
    await interaction.response.defer()

    client = interaction.client
    client_user = client.user

    target = member or interaction.user

    guild = interaction.guild
    if not guild or not isinstance(target, Member):
        return

    # ⸻ Sort the joined and roles lists.

    guild_members = sorted(guild.members, key = lambda m : m.joined_at or utcnow())

    joins = "Unknown"
    roles = ", ".join(f"`{role.name}`" for role in target.roles if not role.is_default())

    # ⸻ Is the user special in anyway?

    characteristics = "\n".join(
        filter(
            None,
            [
                f"- {DEVELOPER_EMOJI} This user is one of my **my owners**." if is_bot_owner(target) else None,
                f"- {PET_CORDEX_EMOJI} This user is a **good boy**."         if client_user and target == client_user else None,
                f"- {EMPLOYEE_EMOJI} This user is a **Discord Employee**."   if target.public_flags.staff else None,
                f"- {PARTNER_EMOJI} This user is a **Discord Partner**."     if target.public_flags.partner else None,
                f"- {OWNER_EMOJI} This user is the **Server Owner**."        if guild.owner == target else None,
                f"- {ASTERISK_EMOJI} This user is an **Administrator**."     if target.guild_permissions.administrator else None,
                f"- {MODERATION_EMOJI} This user is a **Moderator**."        if target.guild_permissions.moderate_members else None,
                f"- {BOOSTER_EMOJI} This user is a **Server Booster**."      if target.premium_since is not None else None,
            ],
        ),
    )

    if target in guild_members:
        target_index = guild_members.index(target)

        join_lines = [
            f"{index + 1:>4}. {"> " if index == target_index else "  "}{str(member) if member.discriminator != "0" else member.name}"
            for index in range(
                max(
                    0,
                    target_index - 3,
                ),
                min(
                    len(guild_members),
                    target_index + 4,
                ),
            ) for member in [guild_members[index]]
        ]

        joins = codeblock("\n".join(join_lines), language = None) or "Unknown"

    # ⸻ Determine avatar and banner based on server parameter.

    fetched_target = await client.fetch_user(target.id)
    guild_target   = guild.get_member(target.id) or await guild.fetch_member(target.id)

    avatar = (guild_target.guild_avatar if scope == "guild" else None) or fetched_target.avatar
    banner = (guild_target.guild_banner if scope == "guild" else None) or fetched_target.banner

    # ⸻ Build the view.

    user_info = format_table(
        {
            "Name"       : escape_markdown(target.global_name or target.name),
            "Nickname"   : escape_markdown(target.nick or "None"),
            "Username"   : escape_markdown(f"{target.name}{f"#{target.discriminator}" if target.discriminator != "0" else ""}"),
            "Joined at"  : f"{format_dt(target.joined_at, style = "F")} | {format_dt(target.joined_at, style = "R")}" if target.joined_at else "Unknown",
            "Created at" : f"{format_dt(target.created_at, style = "F")} | {format_dt(target.created_at, style = "R")}",
        },
    )

    @final
    class InfoView(View):
        container = Container[Self](
            TextDisplay(f"### {target.mention} {f"| {BIG_BOT_EMOJI} " if target.bot else ""}| {target.id}"),
            color = target.color if target.color.value else COLOR_GREY,
        )

        if avatar:
            container.add_item(ThumbnailSection(user_info, thumbnail = Thumbnail(avatar.url)))
        else:
            container.add_text(user_info)

        if roles:
            container.add_text(
                "**Roles**\n"
               f"{roles}",
            )

        if characteristics:
            container.add_text(
                "**Characteristics**\n"
               f"{characteristics}",
            )

        container.add_text(
            "**Join Order**\n"
           f"{joins}",
        )

        if banner:
            container.add_item(MediaGallery(MediaGalleryItem(banner.url)))

    await interaction.followup.send(view = InfoView(), allowed_mentions = AllowedMentions.none())
