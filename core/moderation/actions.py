# pyright: reportImportCycles = false

from dataclasses import dataclass
from datetime import timedelta
from typing import Self, final

from discord import Enum, Forbidden, Guild, HTTPException, Message
from discord.utils import escape_markdown, format_dt, utcnow

from bot import Cordex, log
from bot.ui import LayoutView, TextDisplay, VisibleLargeSeparator
from constants import COLOR_BLACK, COLOR_GREY, COLOR_ORANGE, COLOR_YELLOW, WARNING_EMOJI
from core.paginator import Footer, UnnamedPaginator
from core.utilities import format_now, format_table

from .managers import LockdownManager, QuarantineManager
from .payloads import (
    BanAddPayload,
    BanRemovePayload,
    KickPayload,
    LockdownAddPayload,
    LockdownRemovePayload,
    PurgePayload,
    QuarantineAddPayload,
    QuarantineRemovePayload,
    TimeoutAddPayload,
    TimeoutRemovePayload,
)


class ActionType(Enum):
    """Represents all moderation actions."""

    lockdown_add      = "lockdown_add"
    lockdown_remove   = "lockdown_remove"
    ban_add           = "ban_add"
    ban_remove        = "ban_remove"
    kick              = "kick"
    quarantine_add    = "quarantine_add"
    quarantine_remove = "quarantine_remove"
    timeout_add       = "timeout_add"
    timeout_remove    = "timeout_remove"
    purge             = "purge"

    @classmethod
    def from_sql(cls, value : str, /) -> Self:
        """
        Get a moderation action from its SQL form.

        Parameters
        ----------
        value : `str`
            The SQL form of the action type.
        /

        Returns
        -------
        `Self`
            The moderation action.

        Raises
        ------
        ValueError
            The SQL form doesn't match any moderation action.
        """
        if not hasattr(cls, "_sql_map"):
            cls._sql_map = {member.sql() : member for member in cls}

        try:
            return cls._sql_map[value]
        except KeyError:
            error = f"{value} is not a valid form for ActionType"
            raise ValueError(error) from None

    @property
    def is_additive_type(self) -> bool:
        return self in {
            ActionType.lockdown_add,
            ActionType.ban_add,
            ActionType.kick,
            ActionType.quarantine_add,
            ActionType.timeout_add,
            ActionType.purge,
        }

    @property
    def is_removal_type(self) -> bool:
        return self in {
            ActionType.lockdown_remove,
            ActionType.ban_remove,
            ActionType.quarantine_remove,
            ActionType.timeout_remove,
        }

    def readable(self) -> str:
        """
        Present a moderation action in a readable form.

        Returns
        -------
        `str`
            The moderation action presented in a readable form.
        """
        return self.value.replace("_", " ").title()

    def sql(self) -> str:
        """
        Present a moderation action in SQL form.

        Returns
        -------
        `str`
            The moderation action presented in SQL form.
        """
        return self.value.replace("_", "")


@dataclass(frozen = True, slots = True)
class _ActionResult[T = None]:
    failed  : bool
    logged  : bool
    dmed    : bool | None
    data    : T    | None = None


type DMActions = (
    BanAddPayload
    | BanRemovePayload
    | KickPayload
    | QuarantineAddPayload
    | QuarantineRemovePayload
    | TimeoutAddPayload
    | TimeoutRemovePayload
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Moderation Actions
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
class Actions:
    """
    A class for executing moderation actions.

    Parameters
    ----------
    bot : `Cordex`
        The bot instance.
    guild : `Guild`
        The guild in which moderation actions are being executed.
    """

    __slots__ = ("bot", "cases", "config", "guild", "lockdown", "quarantine")

    def __init__(self, bot : Cordex, guild : Guild) -> None:
        super().__init__()
        from .cases import CasesManager  # ruff: ignore[import-outside-top-level]

        self.bot    = bot
        self.guild  = guild
        self.config = self.bot.config(guild)

        self.cases      = CasesManager(bot, guild)
        self.lockdown   = LockdownManager(bot, guild)
        self.quarantine = QuarantineManager(bot, guild)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # _log_failure
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    def _log_failure(self, msg : str, /) -> None:
        log.exception("Failure during %s in guild %s, %s", msg, self.guild.name, self.guild.id)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # _dm_target
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def _dm_target(self, action : DMActions, /) -> bool:
        moderator = action.moderator
        target    = action.target

        guild_name = f"'{self.guild.name}'"

        type_map : dict[type[DMActions], str] = {
            BanAddPayload           : f"# {WARNING_EMOJI} You have been banned in the server {guild_name}.",
            BanRemovePayload        : f"# {WARNING_EMOJI} You have been un-banned from the server {guild_name}.",
            KickPayload             : f"# {WARNING_EMOJI} You have been kicked from the server {guild_name}.",
            QuarantineAddPayload    : f"# {WARNING_EMOJI} You have been placed in quarantine in the server {guild_name}.",
            QuarantineRemovePayload : f"# {WARNING_EMOJI} You have been removed from quarantine in the server {guild_name}.",
            TimeoutAddPayload       : f"# {WARNING_EMOJI} You have been placed in timeout in the server {guild_name}.",
            TimeoutRemovePayload    : f"# {WARNING_EMOJI} You have been removed from timeout in the server {guild_name}.",
        }

        title  = type_map[type(action)]

        undone_at = ""
        if isinstance(action, TimeoutAddPayload):
            end_time = utcnow() + timedelta(seconds = action.length)
            undone_at = f"-# This action will be undone {format_dt(end_time, style = "F")} | {format_dt(end_time, style = "R")}."

        moderation_table = format_table(
            {
                "Moderator" : f"{moderator.mention} | {moderator.id}",
                "Reason"    : action.reason,
            },
        )

        view = LayoutView()
        view.add_items(
            TextDisplay[LayoutView](
                f"{title}\n"
                f"-# You were moderated at {format_now()}!\n",
            ),
            VisibleLargeSeparator[LayoutView](),
            TextDisplay[LayoutView](
               f"{moderation_table}\n"
                "\n"
               f"{undone_at}",
            ),
        )

        try:
            await target.send(view = view)
        except Forbidden, HTTPException:
            return False
        else:
            return True

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # lockdown_add
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def lockdown_add(self, action : LockdownAddPayload, /) -> _ActionResult:
        """
        Place a channel in lockdown.

        Parameters
        ----------
        action : `LockdownAddPayload`
            The data associated with the lockdown addition.
        /

        Returns
        -------
        `ActionResult`
            The result of the lockdown addition.
        """
        channel   = action.channel
        everyone  = self.guild.default_role
        overwrite = channel.overwrites_for(everyone)

        await self.lockdown.add(channel)

        try:
            overwrite.send_messages = False
            await channel.set_permissions(
                everyone,
                overwrite = overwrite,
                reason    = f"Locked down by {action.moderator.name}: {action.reason}",
            )
        except Forbidden:
            failed = True
            await self.lockdown.remove(channel)
        except HTTPException:
            failed = True
            self._log_failure("lockdown add")
            await self.lockdown.remove(channel)
        else:
            failed = False

        case = await self.cases.create_case(action)

        return _ActionResult(
            failed = failed,
            logged = case.successful,
            dmed   = None,
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # lockdown_view
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def lockdown_view(self) -> UnnamedPaginator | None:
        """
        Display a paginator (`UnnamedPaginator`) of all channels in lockdown.

        Returns
        -------
        `LockdownPaginator | None`
            The paginator displaying all channels in lockdown, or `None` if no channels are in lockdown.
        """
        channels = await self.lockdown.get()
        if not channels:
            return None

        cases = await self.cases.filter_by(
            action_type = ActionType.lockdown_add,
            expired     = False,
        )

        case_by_channel = {case.channel.id : case for case in cases if case.channel is not None}

        entries : list[str] = []
        for channel in channels:
            case = case_by_channel.get(channel.id)
            if case is None:
                continue

            entries.append(
                f"**{channel.mention} | {case.moderator.mention}**\n"
                f"*{escape_markdown(case.reason)}*\n"
                f"-# Locked down at {format_dt(case.created_at, "F")}, {format_dt(case.created_at, "R")}.\n"
                f"-# Case ID: #{case.id}",
            )

        class LockdownPaginator(UnnamedPaginator):
            def __init__(self) -> None:
                super().__init__(
                    "# Server Lockdowns",
                    entries,
                    footer    = Footer("Page {smallest_page} of {biggest_page} | {count} Lockdown{s}"),
                    per_page  = 10,
                    color     = COLOR_GREY,
                    container = True,
                )

        return LockdownPaginator()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # lockdown_remove
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def lockdown_remove(self, action : LockdownRemovePayload, /) -> _ActionResult:
        """
        Remove a channel from lockdown.

        Parameters
        ----------
        action : `LockdownRemovePayload`
            The data associated with the lockdown removal.
        /

        Returns
        -------
        `ActionResult`
            The result of the lockdown removal.
        """
        channel  = action.channel
        everyone = self.guild.default_role

        try:
            overwrite = channel.overwrites_for(everyone)
            overwrite.send_messages = None

            await channel.set_permissions(
                everyone,
                overwrite = overwrite,
                reason    = f"Unlocked by {action.moderator.name}: {action.reason}",
            )
        except Forbidden:
            failed = True
        except HTTPException:
            failed = True
            self._log_failure("lockdown removal")
        else:
            failed = False
            await self.lockdown.remove(channel)

        case = await self.cases.create_case(action)

        return _ActionResult(
            failed = failed,
            logged = case.successful,
            dmed   = None,
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # ban_add
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def ban_add(self, action : BanAddPayload, /) -> _ActionResult:
        """
        Ban a member from the server. This also removes the target's quarantine, if applicable.

        Parameters
        ----------
        action : `BanAddPayload`
            The data associated with the ban addition.
        /

        Returns
        -------
        `ActionResult`
            The result of the ban addition.
        """
        success = await self._dm_target(action) if action.dm_user else None

        try:
            await action.target.ban(
                reason                 = f"Banned by {action.moderator.name}: {action.reason}",
                delete_message_seconds = action.seconds_to_delete,
            )
            if action.target in await self.quarantine.get():
                await self.quarantine.remove(action.target)  # TODO(FinestPerfectiomism): Expire the related quarantine case.
        except Forbidden:
            failed = True
        except HTTPException:
            failed = True
            self._log_failure("ban add")
        else:
            failed = False

        case = await self.cases.create_case(action)

        return _ActionResult(
            failed = failed,
            logged = case.successful,
            dmed   = success,
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # ban_view
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def ban_view(self) -> UnnamedPaginator | None:
        """
        Display a paginator (`UnnamedPaginator`) of all server bans.

        Returns
        -------
        `BanPaginator | None`
            The paginator displaying all banned members, or `None` if no members are banned.
        """
        db_cases = await self.cases.filter_by(
            action_type = ActionType.ban_add,
            expired     = False,
        )

        api_cases = [case async for case in self.guild.bans()]
        if not db_cases and not api_cases:
            return None

        class BanPaginator(UnnamedPaginator):
            def __init__(self) -> None:
                super().__init__(
                    "# Server Bans",
                    [
                        *[
                            (
                                f"**{case.target.mention if case.target else "Unknown Member"} | {case.moderator.mention}**\n"
                                f"*{escape_markdown(case.reason or "No reason provided")}*\n"
                                f"-# Banned at {format_dt(case.created_at, "F")}, {format_dt(case.created_at, "R")}.\n"
                                f"-# Case ID: #{case.id}"
                            ) for case in db_cases
                        ],
                        *[
                            (
                                f"**{case.user.mention if case.user else "Unknown Member"} | Unknown Moderator**\n"
                                f"*{escape_markdown(case.reason or "No reason provided")}*\n"
                                f"-# Banned at Unknown Time.\n"
                                f"-# Case ID: N/A (Ban is not managed by Cordex)"
                            ) for case in api_cases
                        ],
                    ],
                    footer    = Footer("Page {smallest_page} of {biggest_page} | {count} Ban{s}"),
                    per_page  = 10,
                    color     = COLOR_BLACK,
                    container = True,
                )

        return BanPaginator()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # ban_remove
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def ban_remove(self, action : BanRemovePayload, /) -> _ActionResult:
        """
        Remove a ban from a member.

        Parameters
        ----------
        action : `BanRemovePayload`
            The data associated with the ban removal.
        /

        Returns
        -------
        `ActionResult`
            The result of the ban removal.
        """
        success = await self._dm_target(action) if action.dm_user else None

        try:
            await self.guild.unban(
                action.target,
                reason = f"Unbanned by {action.moderator.name}: {action.reason}",
            )
        except Forbidden:
            failed = True
        except HTTPException:
            failed = True
            self._log_failure("ban removal")
        else:
            failed = False

        case = await self.cases.create_case(action)

        return _ActionResult(
            failed = failed,
            logged = case.successful,
            dmed   = success,
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # kick
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def kick(self, action : KickPayload, /) -> _ActionResult:
        """
        Kick a member from the server.

        Parameters
        ----------
        action : `KickPayload`
            The data associated with the kick.
        /

        Returns
        -------
        `ActionResult`
            The result of the kick.
        """
        success = await self._dm_target(action) if action.dm_user else None

        try:
            await self.guild.kick(
                action.target,
                reason = f"Kicked by {action.moderator.name}: {action.reason}",
            )
        except Forbidden:
            failed = True
        except HTTPException:
            failed = True
            self._log_failure("kick")
        else:
            failed = False

        case = await self.cases.create_case(action)

        return _ActionResult(
            failed = failed,
            logged = case.successful,
            dmed   = success,
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # quarantine_add
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def quarantine_add(self, action : QuarantineAddPayload, /) -> _ActionResult:
        """
        Place a member in quarantine.

        Parameters
        ----------
        action : `QuarantineAddPayload`
            The data associated with the quarantine addition.
        /

        Returns
        -------
        `ActionResult`
            The result of the quarantine addition.
        """
        quarantine_role = await self.config.get_moderation_quarantine_role()
        if not quarantine_role:
            return _ActionResult(
                failed = True,
                logged = False,
                dmed   = False,
            )

        success = await self._dm_target(action) if action.dm_user else None

        try:
            await self.quarantine.add(action.target)
            await action.target.edit(
                roles  = [quarantine_role],
                reason = f"Quarantined by {action.moderator.name}: {action.reason}",
            )
        except Forbidden:
            failed = True
        except HTTPException:
            failed = True
            self._log_failure("quarantine add")
        else:
            failed = False

        case = await self.cases.create_case(action)

        return _ActionResult(
            failed = failed,
            logged = case.successful,
            dmed   = success,
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # quarantine_view
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def quarantine_view(self) -> UnnamedPaginator | None:
        """
        Display a paginator (`UnnamedPaginator`) of all members in quarantine.

        Returns
        -------
        `QuarantinePaginator | None`
            The paginator displaying all quarantined members, or `None` if no members are quarantined.
        """
        cases = await self.cases.filter_by(
            action_type = ActionType.quarantine_add,
            expired     = False,
        )
        if not cases:
            return None

        class QuarantinePaginator(UnnamedPaginator):
            def __init__(self) -> None:
                super().__init__(
                    "# Server Quarantines",
                    [
                        (
                            f"**{case.target.mention if case.target else "Unknown Member"} | {case.moderator.mention}**\n"
                            f"*{escape_markdown(case.reason)}*\n"
                            f"-# Quarantined at {format_dt(case.created_at, "F")}, {format_dt(case.created_at, "R")}.\n"
                            f"-# Case ID: #{case.id}"
                        ) for case in cases
                    ],
                    footer    = Footer("Page {smallest_page} of {biggest_page} | {count} Quarantine{s}"),
                    per_page  = 10,
                    color     = COLOR_ORANGE,
                    container = True,
                )

        return QuarantinePaginator()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # quarantine_remove
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def quarantine_remove(self, action : QuarantineRemovePayload, /) -> _ActionResult:
        """
        Remove a member from quarantine.

        Parameters
        ----------
        action : `QuarantineRemovePayload`
            The data associated with the quarantine removal.
        /

        Returns
        -------
        `ActionResult`
            The result of the quarantine removal.
        """
        quarantine_role = await self.config.get_moderation_quarantine_role()
        if not quarantine_role:
            return _ActionResult(
                failed = True,
                logged = False,
                dmed   = False,
            )

        success = await self._dm_target(action) if action.dm_user else None

        roles = await self.quarantine.remove(action.target)

        try:
            if roles is not None:
                await action.target.edit(
                    roles  = roles,
                    reason = f"Unquarantined by {action.moderator.name}: {action.reason}",
                )
            else:
                await action.target.remove_roles(
                    quarantine_role,
                    reason = f"Unquarantined by {action.moderator.name}: {action.reason}",
                )
        except Forbidden:
            failed = True
        except HTTPException:
            failed = True
            self._log_failure("quarantine removal")
        else:
            failed = False

        case = await self.cases.create_case(action)

        return _ActionResult(
            failed = failed,
            logged = case.successful,
            dmed   = success,
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # timeout_add
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def timeout_add(self, action : TimeoutAddPayload, /) -> _ActionResult:
        """
        Place a member in timeout.

        Parameters
        ----------
        action : `TimeoutAddPayload`
            The data associated with the timeout addition.
        /

        Returns
        -------
        `ActionResult`
            The result of the timeout addition.
        """
        success = await self._dm_target(action) if action.dm_user else None

        try:
            await action.target.edit(
                timed_out_until = utcnow() + timedelta(seconds = action.length),
                reason          = f"Timed out by {action.moderator.name}: {action.reason}",
            )
        except Forbidden:
            failed = True
        except HTTPException:
            failed = True
            self._log_failure("timeout add")
        else:
            failed = False

        case = await self.cases.create_case(action)

        return _ActionResult(
            failed = failed,
            logged = case.successful,
            dmed   = success,
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # timeout_view
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def timeout_view(self) -> UnnamedPaginator | None:
        """
        Display a paginator (`UnnamedPaginator`) of all members in timeout.

        Returns
        -------
        `TimeoutPaginator | None`
            The paginator displaying all members in timeout, or `None` if no members are timed out.
        """
        db_cases = await self.cases.filter_by(
            action_type = ActionType.timeout_add,
            expired     = False,
        )

        db_target_ids = {case.target.id for case in db_cases if case.target}
        api_members = [
            member async for member in self.guild.fetch_members()
            if member.is_timed_out() and member.id not in db_target_ids
        ]

        if not db_cases and not api_members:
            return None

        class TimeoutPaginator(UnnamedPaginator):
            def __init__(self) -> None:
                super().__init__(
                    "# Server Timeouts",
                    [
                        *[
                            (
                                f"**{case.target.mention if case.target else "Unknown Member"} | {case.moderator.mention}**\n"
                                f"*{escape_markdown(case.reason or "No reason provided")}*\n"
                                f"-# Timed out at {format_dt(case.created_at, "F")}, {format_dt(case.created_at, "R")}.\n"
                                f"-# Case ID: #{case.id}"
                            ) for case in db_cases
                        ],
                        *[
                            (
                                f"**{member.mention} | Unknown Moderator**\n"
                                f"*No reason provided*\n"
                                f"-# Timed out until {format_dt(member.timed_out_until, "F") if member.timed_out_until else "Unknown Time"} ({format_dt(member.timed_out_until, "R") if member.timed_out_until else ""}).\n"
                                f"-# Case ID: N/A (Timeout is not managed by Cordex)"
                            ) for member in api_members
                        ],
                    ],
                    footer    = Footer("Page {smallest_page} of {biggest_page} | {count} Timeout{s}"),
                    per_page  = 10,
                    color     = COLOR_YELLOW,
                    container = True,
                )

        return TimeoutPaginator()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # timeout_remove
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def timeout_remove(self, action : TimeoutRemovePayload, /) -> _ActionResult:
        """
        Remove a member from timeout.

        Parameters
        ----------
        action : `TimeoutRemovePayload`
            The data associated with the timeout removal.
        /

        Returns
        -------
        `ActionResult`
            The result of the timeout removal.
        """
        success = await self._dm_target(action) if action.dm_user else None

        try:
            await action.target.edit(
                timed_out_until = None,
                reason          = f"Untimed out by {action.moderator.name}: {action.reason}",
            )
        except Forbidden:
            failed = True
        except HTTPException:
            failed = True
            self._log_failure("timeout removal")
        else:
            failed = False

        case = await self.cases.create_case(action)

        return _ActionResult(
            failed = failed,
            logged = case.successful,
            dmed   = success,
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # purge
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def purge(self, action : PurgePayload, /) -> _ActionResult[int]:
        """
        Purge messages.

        Parameters
        ----------
        action : `PurgePayload`
            The data associated with the purge.
        /

        Returns
        -------
        `ActionResult`
            The result of the purge.
        """
        target  = action.target
        reason  = action.reason
        channel = action.channel
        amount  = action.amount

        async def _purge() -> list[Message]:
            if not target:
                return await channel.purge(limit = amount, reason = reason)

            return await channel.purge(
                limit  = 1000 if action.force else amount,
                check  = lambda m : m.author == target,
                reason = reason,
            )

        try:
            deleted = await _purge()
        except Forbidden:
            failed  = True
            deleted = []
        except HTTPException:
            failed  = True
            deleted = []
            self._log_failure("purge")
        else:
            failed = False

        case = await self.cases.create_case(action)

        return _ActionResult(
            failed = failed,
            logged = case.successful,
            dmed   = None,
            data   = len(deleted),
        )
