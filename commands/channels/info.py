from collections.abc import Sequence
from typing import Self, final

from discord import (
    AllowedMentions,
    CategoryChannel,
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
from bot.ui import Container, TextDisplay, View
from constants import (
    ACTIVE_LOCKED_STAGE_EMOJI,
    ACTIVE_LOCKED_VOICE_EMOJI,
    ACTIVE_STAGE_EMOJI,
    ACTIVE_VOICE_EMOJI,
    ANNOUNCEMENT_EMOJI,
    CATEGORY_EMOJI,
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


def _get_channel_emoji(target : GuildChannel) -> str | None:
    if target == target.guild.rules_channel:
        return RULES_EMOJI

    private = not target.permissions_for(target.guild.default_role).view_channel

    if isinstance(target, StageChannel):
        if len(target.members) > 0:
            return ACTIVE_LOCKED_STAGE_EMOJI if private else ACTIVE_STAGE_EMOJI
        return LOCKED_STAGE_EMOJI if private else STAGE_EMOJI
    if isinstance(target, VoiceChannel):
        if len(target.members) > 0:
            return ACTIVE_LOCKED_VOICE_EMOJI if private else ACTIVE_VOICE_EMOJI
        return LOCKED_VOICE_EMOJI if private else VOICE_EMOJI
    if isinstance(target, ForumChannel):
        if target.is_media():
            return LOCKED_MEDIA_EMOJI if private else MEDIA_EMOJI
        return LOCKED_FORUM_EMOJI if private else FORUM_EMOJI
    if isinstance(target, TextChannel):
        if target.is_news():
            return LOCKED_ANNOUNCEMENT_EMOJI if private else ANNOUNCEMENT_EMOJI
        return LOCKED_TEXT_EMOJI if private else TEXT_EMOJI
    if isinstance(target, CategoryChannel):
        return CATEGORY_EMOJI
    return None


def _member_section(title : str, members : Sequence[Member]) -> str | None:
    if not members:
        return None

    listing = "\n".join(f"{member.name} | {member.id}" for member in members)
    s = "s" if len(members) > 1 else ""

    return (
        f"**{len(members)} {title}{s}**\n"
        f"{codeblock(listing, language = None)}"
    )


def _format_auto_archive(archive_minutes : int) -> str:
    if archive_minutes >= 1440:
        days = archive_minutes // 1440
        s = "s" if days != 1 else ""
        return f"{days} day{s}"

    hours = archive_minutes // 60
    s = "s" if hours != 1 else ""
    return f"{hours} hour{s}"


def _build_header(target : GuildChannel, thread_target : Thread | None) -> str:
    channel_type_emoji = _get_channel_emoji(target)

    if thread_target:
        emoji_display = (
            f"| {channel_type_emoji} {RIGHTWARDS_ARROW_EMOJI} {THREAD_EMOJI} "
            if channel_type_emoji else
            f"| {THREAD_EMOJI} "
        )
        return f"### {thread_target.mention} {emoji_display}| {thread_target.id}"

    emoji_display = f"| {channel_type_emoji} " if channel_type_emoji else ""
    mention       = target.mention if not isinstance(target, CategoryChannel) else target.name
    return f"### {mention} {emoji_display}| {target.id}"


def _build_thread_info(parent : GuildChannel, thread : Thread) -> dict[str, str]:
    nsfw = parent.nsfw if isinstance(parent, TextChannel | ForumChannel) else False
    owner_mention = (
        thread.owner.mention
        if thread.owner else
        (f"<@{thread.owner_id}>" if thread.owner_id else "Unknown")
    )

    info = {
        "Parent"            : parent.mention,
        "Owner"             : owner_mention,
        "Not Safe for Work" : "Yes" if nsfw else "No",
        "Locked"            : "Yes" if thread.locked else "No",
        "Archived"          : "Yes" if thread.archived else "No",
        "Auto Archive"      : _format_auto_archive(thread.auto_archive_duration),
        "Last Modified"     : f"{format_dt(thread.archive_timestamp, style = "F")} | {format_dt(thread.archive_timestamp, style = "R")}",
        "Created at"        : f"{format_dt(thread.created_at, style = "F")} | {format_dt(thread.created_at, style = "R")}" if thread.created_at else "Unknown",
    }

    if thread.applied_tags:
        info["Tags"] = ", ".join(tag.name for tag in thread.applied_tags)

    return info


def _build_category_info(category : CategoryChannel) -> dict[str, str]:
    return {
        "Channels"   : str(len(category.channels)),
        "Created at" : f"{format_dt(category.created_at, style = "F")} | {format_dt(category.created_at, style = "R")}",
    }


def _build_channel_info(target : GuildChannel) -> dict[str, str]:
    nsfw = target.nsfw if isinstance(target, TextChannel | VoiceChannel | StageChannel | ForumChannel) else False

    info : dict[str, str] = {
        "Not Safe for Work" : "Yes" if nsfw else "No",
        "Category"          : f"{target.category.name} | {target.category.id}" if target.category else "None",
        "Created at"        : f"{format_dt(target.created_at, style = "F")} | {format_dt(target.created_at, style = "R")}",
    }

    if isinstance(target, TextChannel):
        info["Slowmode"] = f"{target.slowmode_delay} seconds" if target.slowmode_delay else "Off"
    elif isinstance(target, ForumChannel):
        info["Slowmode"] = f"{target.slowmode_delay} seconds" if target.slowmode_delay else "Off"
        if target.available_tags:
            info["Tags"] = ", ".join(tag.name for tag in target.available_tags)
    elif isinstance(target, VoiceChannel | StageChannel):
        info["User Limit"] = str(target.user_limit) if target.user_limit else "Unlimited"
        info["Bitrate"]    = f"{target.bitrate // 1000} kbps"

    return info


def _build_sections(target : GuildChannel, thread_target : Thread | None) -> list[str]:
    sections : list[str] = []

    topic = target.topic if isinstance(target, TextChannel | StageChannel | ForumChannel) else None
    if topic:
        sections.append(
            "**Description**\n"
           f">>> {topic}",
        )

    if thread_target:
        return sections

    if isinstance(target, CategoryChannel) and target.channels:
        channel_list = "\n".join(f"{_get_channel_emoji(channel)} {channel.mention} | {channel.id}" for channel in target.channels)
        sections.append(
            f"**Channels**\n"
            f"{channel_list}",
        )
    elif isinstance(target, VoiceChannel):
        if member_section := _member_section("Member", target.members):
            sections.append(member_section)
    elif isinstance(target, StageChannel):
        sections.extend(
            section for section in (
                _member_section("Speaker",   target.speakers),
                _member_section("Moderator", target.moderators),
                _member_section("Listener",  target.listeners),
            ) if section
        )

    return sections


async def run_channel_info(interaction : Interaction, channel : GuildChannel | Thread | None = None) -> None:
    """
    View information for a channel.

    Parameters
    ----------
    interaction : `Interaction`
        The interaction context to run the command with.
    channel : `GuildChannel | None = None`
        The channel to view information for. Defaults to the current one.
    """
    await interaction.response.defer()

    if not interaction.guild or not isinstance(interaction.channel, GuildChannel | Thread):
        return

    raw_target    = channel or interaction.channel
    thread_target : Thread | None = None

    if isinstance(raw_target, Thread):
        thread_target = raw_target
        target        = raw_target.parent
    else:
        target = raw_target

    if not isinstance(target, GuildChannel):
        return

    header_text = _build_header(target, thread_target)

    if thread_target:
        info = _build_thread_info(target, thread_target)
    elif isinstance(target, CategoryChannel):
        info = _build_category_info(target)
    else:
        info = _build_channel_info(target)

    sections = _build_sections(target, thread_target)

    @final
    class InfoView(View):
        container = Container[Self](
            TextDisplay(header_text),
            TextDisplay(format_table(info)),
            *(TextDisplay[Self](section) for section in sections),
            color = COLOR_GREY,
        )

    await interaction.followup.send(view = InfoView(), allowed_mentions = AllowedMentions.none())
