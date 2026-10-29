from collections.abc import Sequence
from typing import Self, final

from discord import (
    AllowedMentions,
    ForumChannel,
    Member,
    StageChannel,
    TextChannel,
    Thread,
    VoiceChannel,
)
from discord.abc import GuildChannel
from discord.utils import format_dt

from bot import Interaction
from bot.types import GuildMessageable
from bot.ui import Container, LayoutView, TextDisplay
from constants import (
    ACTIVE_LOCKED_STAGE_EMOJI,
    ACTIVE_LOCKED_VOICE_EMOJI,
    ACTIVE_STAGE_EMOJI,
    ACTIVE_VOICE_EMOJI,
    ANNOUNCEMENT_EMOJI,
    COLOR_GREY,
    FORUM_EMOJI,
    LOCKED_ANNOUNCEMENT_EMOJI,
    LOCKED_FORUM_EMOJI,
    LOCKED_MEDIA_EMOJI,
    LOCKED_STAGE_EMOJI,
    LOCKED_TEXT_EMOJI,
    LOCKED_VOICE_EMOJI,
    MEDIA_EMOJI,
    RIGHTWARDS_ARROW_EMOJI,
    RULES_EMOJI,
    STAGE_EMOJI,
    TEXT_EMOJI,
    THREAD_EMOJI,
    VOICE_EMOJI,
)
from core.utilities import codeblock, format_table

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /channel info Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


def _is_private(target : GuildChannel) -> bool:
    return not target.permissions_for(target.guild.default_role).view_channel


def _get_channel_emoji(target : GuildChannel) -> str | None:

    # ⸻ target is the rules channel.

    if target.guild.rules_channel and target == target.guild.rules_channel:
        return RULES_EMOJI

    private = _is_private(target)

    # ⸻ target is a StageChannel.

    if isinstance(target, StageChannel):
        if len(target.members) > 0:
            return ACTIVE_LOCKED_STAGE_EMOJI if private else ACTIVE_STAGE_EMOJI
        return LOCKED_STAGE_EMOJI if private else STAGE_EMOJI

    # ⸻ target is a VoiceChannel.

    if isinstance(target, VoiceChannel):
        if len(target.members) > 0:
            return ACTIVE_LOCKED_VOICE_EMOJI if private else ACTIVE_VOICE_EMOJI
        return LOCKED_VOICE_EMOJI if private else VOICE_EMOJI

    # ⸻ target is a ForumChannel or media channel.

    if isinstance(target, ForumChannel):
        if target.is_media():
            return LOCKED_MEDIA_EMOJI if private else MEDIA_EMOJI
        return LOCKED_FORUM_EMOJI if private else FORUM_EMOJI

    # ⸻ target is a TextChannel or announcement channel.

    if isinstance(target, TextChannel):
        if target.is_news():
            return LOCKED_ANNOUNCEMENT_EMOJI if private else ANNOUNCEMENT_EMOJI
        return LOCKED_TEXT_EMOJI if private else TEXT_EMOJI

    return None


def _member_section(title : str, members : Sequence[Member]) -> str | None:
    if not members:
        return None

    shown     = "\n".join(f"{member.name} | {member.id}" for member in members)
    remaining = len(members) - 20
    listing   = (
        f"{shown}\n"
        f"(+{remaining} more)" if remaining > 0 else shown
    )

    s = "s" if len(members) > 1 else ""
    return (
        f"**{len(members)} {title}{s}**\n"
        f"{codeblock(listing, language = None)}"
    )


async def run_channel_info(interaction : Interaction, channel : GuildMessageable | None = None) -> None:
    """
    View information for a channel.

    Parameters
    ----------
    interaction : `Interaction`
        The interaction context to run the command with.
    channel : `GuildMessageable | None = None`
        The channel to view information for. Defaults to the current one.
    """
    await interaction.response.defer()

    target = channel or interaction.channel
    thread_target : Thread | None = None

    if not interaction.guild or not isinstance(target, GuildMessageable):
        return

    if isinstance(target, Thread):
        thread_target = target
        target = target.parent

    if not isinstance(target, GuildChannel):
        return

    # ⸻ Channel emoji.

    channel_type_emoji = _get_channel_emoji(target)

    # ⸻ Build the view.

    if thread_target:
        emoji_display = f"| {channel_type_emoji} {RIGHTWARDS_ARROW_EMOJI} {THREAD_EMOJI} " if channel_type_emoji else f"| {THREAD_EMOJI} "
        header_text   = f"### {thread_target.mention} {emoji_display}| {thread_target.id}"
    else:
        emoji_display = f"| {channel_type_emoji} " if channel_type_emoji else ""
        header_text   = f"### {target.mention} {emoji_display}| {target.id}"

    nsfw  = target.nsfw
    topic = target.topic if isinstance(target, TextChannel | StageChannel | ForumChannel) else None

    info     : dict[str, str]
    sections : list[str] = []

    if topic:
        sections.append(
            "**Description**\n"
           f"{topic}",
        )

    if thread_target:
        archive_minutes = thread_target.auto_archive_duration

        auto_archive = (
            f"{archive_minutes // 1440} day{"s" if archive_minutes != 1440 else ""}"
            if archive_minutes >= 1440 else
            f"{archive_minutes // 60} hour{"s" if archive_minutes != 60 else ""}"
        )

        info = {
            "Parent"            : target.mention,
            "Owner"             : f"<@{thread_target.owner.mention if thread_target.owner else thread_target.owner_id}>",
            "Not Safe for Work" :  "Yes" if nsfw else "No",
            "Locked"            :  "Yes" if thread_target.locked else "No",
            "Archived"          :  "Yes" if thread_target.archived else "No",
            "Auto Archive"      : auto_archive,
            "Last Modified"     : f"{format_dt(thread_target.archive_timestamp, style = "F")} | {format_dt(thread_target.archive_timestamp, style = "R")}",
            "Created at"        : f"{format_dt(thread_target.created_at, style = "F")} | {format_dt(thread_target.created_at, style = "R")}" if thread_target.created_at else "Unknown",
        }

        if thread_target.applied_tags:
            info["Tags"] = ", ".join(tag.name for tag in thread_target.applied_tags)
    else:
        category = f"{target.category.name} | {target.category.id}" if target.category else "None"

        info = {
            "Not Safe for Work" :  "Yes" if nsfw else "No",
            "Category"          : category,
            "Created at"        : f"{format_dt(target.created_at, style = "F")} | {format_dt(target.created_at, style = "R")}",
        }

        if isinstance(target, TextChannel):
            info["Slowmode"] = f"{target.slowmode_delay} seconds" if target.slowmode_delay else "Off"
        elif isinstance(target, VoiceChannel):
            info["User Limit"] = str(target.user_limit) if target.user_limit else "Unlimited"
            info["Bitrate"]    = f"{target.bitrate // 1000} kbps"

            sections.extend(
                section for section in (
                    _member_section("Member", target.members),
                ) if section
            )
        elif isinstance(target, StageChannel):
            info["User Limit"] = str(target.user_limit) if target.user_limit else "Unlimited"
            info["Bitrate"]    = f"{target.bitrate // 1000} kbps"

            sections.extend(
                section for section in (
                    _member_section("Speaker",   target.speakers),
                    _member_section("Moderator", target.moderators),
                    _member_section("Listener",  target.listeners),
                ) if section
            )

    @final
    class InfoView(LayoutView):
        container = Container[Self](
            TextDisplay(header_text),
            TextDisplay(format_table(info)),
            *(TextDisplay[Self](section) for section in sections),
            color = COLOR_GREY,
        )

    await interaction.followup.send(view = InfoView(), allowed_mentions = AllowedMentions.none())
