from typing import Literal, cast, final, overload

from discord import Color, Forbidden, Guild, HTTPException, Member, Permissions, Role
from discord.abc import GuildChannel

from bot import Cordex, log
from core.responses import FormatOverride, MessageType, format_send

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Moderation Managers
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

RATE_LIMITED = 429

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Lockdown Manager
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
class LockdownManager:
    """
    A manager for lockdown operations that don't pertain to primary moderation actions.

    Parameters
    ----------
    bot : `Cordex`
        The bot instance.
    guild : `Guild`
        The guild where lockdown is being managed.
    """

    __slots__ = ("bot", "guild")

    def __init__(self, bot : Cordex, guild : Guild) -> None:
        super().__init__()
        self.bot   = bot
        self.guild = guild

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # _log_failure
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    def _log_failure(self, msg : str, /, *, rate_limited : bool = False) -> None:
        rate_limited_msg = " — Rate-limited" if rate_limited else ""
        log.exception("Failure during %s in guild %s, %s%s", msg, self.guild.name, self.guild.id, rate_limited_msg)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # get_channels
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @overload
    async def get_channels(self, *, by_id : Literal[True]) -> set[int]: ...

    @overload
    async def get_channels(self, *, by_id : Literal[False] = False) -> set[GuildChannel]: ...

    async def get_channels(self, *, by_id : bool = False) -> set[GuildChannel] | set[int]:
        """
        Fetch every channel in lockdown found in the database.

        Parameters
        ----------
        *
        by_id : `bool = False`
            Whether to return the IDs of the channels over actual channel objects or not. This is useful in cases where a channel may have been deleted, as deleted channels are only included when this is `True`.

        Returns
        -------
        `by_id = False -> set[GuildChannel]`
            Every channel in lockdown found in the database.
        `by_id = True -> set[int]`
            The ID of every channel in lockdown found in the database.
        """
        async with self.bot.db.execute(
            t"SELECT channel_id FROM Lockdowns WHERE guild_id = {self.guild.id}",
        ) as cursor:
            rows = await cursor.fetchall()

        channel_ids = {cast("int", row[0]) for row in rows}
        if by_id:
            return channel_ids

        return {
            channel for channel_id in channel_ids
            if (channel := self.guild.get_channel(channel_id))
        }

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # add_channel
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def add_channel(self, channel : GuildChannel, /) -> None:
        """
        Mark a channel as locked down in the database.

        Parameters
        ----------
        channel : `GuildChannel`
            The channel to mark as locked down.
        /
        """
        await self.bot.db.execute(
            t"INSERT INTO Lockdowns (channel_id, guild_id) VALUES ({channel.id}, {self.guild.id}) "
            t"ON CONFLICT (channel_id, guild_id) DO NOTHING",
        )
        await self.bot.db.commit()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # remove_channel
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def remove_channel(self, channel : GuildChannel, /) -> None:
        """
        Unmark a channel as locked down in the database.

        Parameters
        ----------
        channel : `GuildChannel`
            The channel to unmark as locked down.
        /
        """
        await self.bot.db.execute(
            t"DELETE FROM Lockdowns WHERE channel_id = {channel.id} AND guild_id = {self.guild.id}",
        )
        await self.bot.db.commit()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # remove_all_channels
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def remove_all_channels(self) -> None:
        """Unmark all of this guild's channels as locked down in the database."""
        await self.bot.db.execute(
            t"DELETE FROM Lockdowns WHERE guild_id = {self.guild.id}",
        )
        await self.bot.db.commit()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # enforce
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def enforce(self) -> None:
        """
        Enforces lockdown operations by ensuring channels in lockdown have the proper permission overwrites.

        Raises
        ------
        HTTPException
            The enforcement caused a ratelimit.
        """
        me = self.guild.me
        if not me or not me.guild_permissions.manage_channels:
            return

        locked_channels = await self.get_channels()
        if not locked_channels:
            return

        everyone = self.guild.default_role

        for channel in locked_channels:
            overwrites = channel.overwrites_for(everyone)

            if overwrites.send_messages is False:
                continue

            overwrites.send_messages = False

            try:
                await channel.set_permissions(
                    everyone,
                    overwrite = overwrites,
                    reason    = "Lockdown enforcement.",
                )
            except Forbidden:
                pass
            except HTTPException as e:
                rate_limited = (e.status == RATE_LIMITED)
                self._log_failure("channel lockdown enforcement", rate_limited = rate_limited)
                if rate_limited:
                    raise

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Quarantine Manager
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
class QuarantineManager:
    """
    A manager for quarantine operations that don't pertain to primary moderation actions.

    Parameters
    ----------
    bot : `Cordex`
        The bot instance.
    guild : `Guild`
        The guild where quarantine is being managed.
    """

    __slots__ = ("bot", "guild")

    def __init__(self, bot : Cordex, guild : Guild) -> None:
        super().__init__()
        self.bot   = bot
        self.guild = guild

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # _log_failure
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    def _log_failure(self, msg : str, /, *, rate_limited : bool = False) -> None:
        rate_limited_msg = " — Rate-limited" if rate_limited else ""
        log.exception("Failure during %s in guild %s, %s%s", msg, self.guild.name, self.guild.id, rate_limited_msg)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # get_members
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def get_members(self) -> set[Member]:
        """
        Fetch every quarantined member found in the database.

        Returns
        -------
        `set[Member]`
            Every quarantined member found in the database.
        """
        async with self.bot.db.execute(
            t"SELECT member_id FROM Quarantines WHERE guild_id = {self.guild.id}",
        ) as cursor:
            rows = await cursor.fetchall()
            if not rows:
                return set()

        return {
            member for row in rows
            if (member := self.guild.get_member(cast("int", row[0])))
        }

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # add_member
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def add_member(self, member : Member, /) -> None:
        """
        Mark a member as quarantined in the database, saving their current roles.

        Parameters
        ----------
        member : `Member`
            The member to mark as quarantined.
        /
        """
        current_roles = [role for role in member.roles if not role.is_default()]
        roles_str     = ",".join(str(role.id) for role in current_roles)

        await self.bot.db.execute(
            t"INSERT INTO Quarantines (member_id, guild_id, old_roles) VALUES ({member.id}, {member.guild.id}, {roles_str}) "
            t"ON CONFLICT (member_id, guild_id) DO UPDATE SET old_roles = excluded.old_roles",
        )
        await self.bot.db.commit()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # remove_member
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def remove_member(self, member : Member, /) -> list[Role] | None:
        """
        Unmark a member as quarantined in the database.

        Parameters
        ----------
        member : `Member`
            The member to unmark as quarantined.
        /

        Returns
        -------
        `list[Role] | None`
            The roles the member had before being quarantined, or `None` if the member was not marked to begin wtih.
        """
        async with self.bot.db.execute(
            t"SELECT old_roles FROM Quarantines WHERE member_id = {member.id} AND guild_id = {member.guild.id}",
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            return None

        roles_str = cast("str", row[0])

        await self.bot.db.execute(
            t"DELETE FROM Quarantines WHERE member_id = {member.id} AND guild_id = {member.guild.id}",
        )
        await self.bot.db.commit()

        return [
            role for role_id_str in roles_str.split(",")
            if role_id_str and (role := member.guild.get_role(int(role_id_str)))
        ]

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # remove_all_members
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def remove_all_members(self) -> None:
        """Unmark all of this guild's members as quarantined in the database."""
        await self.bot.db.execute(
            t"DELETE FROM Quarantines WHERE guild_id = {self.guild.id}",
        )
        await self.bot.db.commit()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # enforce
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    type EnforceTypes = Literal["Channels", "Role", "Members"]

    async def enforce(self, enforce_type : EnforceTypes = "Members", /) -> None:
        """
        Enforces quarantine operations.

        - Channels: Ensures the quarantine role has certain permissions disabled in every guild channel.quarantine channel enforcement.
        - Role: Ensures the quarantine role has all permissions set to false and that the role is below the bot's top role.
        - Members: Ensures the quarantine role doesn't contain members that are not quarantined, and that quarantined members have the quarantine role.

        The channels and role types will have no effect if the guild has not configured quarantine enforcement for those types. The members type will always run as it is not configurable (always enabled).

        Parameters
        ----------
        enforce_type : `Literal["Channels", "Role", "Members"]`
            The type of quarantine enforcement to execute.
        /

        Raises
        ------
        HTTPException
            The enforcement caused a ratelimit.
        """
        config = self.bot.config(self.guild)

        deleted = False
        quarantine_role = await config.get_moderation_quarantine_role()
        if not quarantine_role:
            if not await self.get_members():
                return

            try:
                quarantine_role = await self.guild.create_role(
                    name        = "Quarantine",
                    color       = Color.dark_gold(),
                    permissions = Permissions.none(),
                    reason      = "Quarantine enforcement. Previous role was deleted.",
                )
            except Forbidden:
                return
            except HTTPException as e:
                rate_limited = (e.status == RATE_LIMITED)
                self._log_failure("quarantine enforcement", rate_limited = rate_limited)
                if rate_limited:
                    raise
                return

            await config.set_moderation_quarantine_role(quarantine_role)
            deleted = True

        # ⸻ Channels

        if enforce_type == "Channels" or deleted:
            wants_enforcement = await config.get_whether_moderation_quarantine_enforce_channels()
            if not wants_enforcement and not deleted:
                return

            me = self.guild.me
            if not me or not me.guild_permissions.manage_channels:
                return

            for channel in self.guild.channels:
                overwrites = channel.overwrites_for(quarantine_role)

                overwrites.update(
                    send_messages_in_threads = False,
                    create_instant_invite    = False,
                    send_messages            = False,
                    create_public_threads    = False,
                    create_private_threads   = False,
                    read_messages            = False,
                )

                try:
                    await channel.set_permissions(
                        quarantine_role,
                        overwrite = overwrites,
                        reason    = "Quarantine enforcement.",
                    )
                except Forbidden:
                    pass
                except HTTPException as e:
                    rate_limited = (e.status == RATE_LIMITED)
                    self._log_failure("channel quarantine enforcement", rate_limited = rate_limited)
                    if rate_limited:
                        raise

        # ⸻ Role

        if enforce_type == "Role" or deleted:
            wants_enforcement = await config.get_whether_moderation_quarantine_enforce_roles()
            if not wants_enforcement and not deleted:
                return

            me = self.guild.me
            if not me or not me.guild_permissions.manage_roles:
                return

            my_role = me.top_role
            if quarantine_role.permissions.value != 0:
                try:
                    await quarantine_role.edit(permissions = Permissions.none())
                except Forbidden:
                    pass
                except HTTPException as e:
                    rate_limited = (e.status == RATE_LIMITED)
                    self._log_failure("role quarantine enforcement", rate_limited = rate_limited)
                    if rate_limited:
                        raise

            if my_role.position > 1 and quarantine_role.position != my_role.position - 1:
                try:
                    await quarantine_role.edit(position = my_role.position - 1)
                except Forbidden:
                    pass
                except HTTPException as e:
                    rate_limited = (e.status == RATE_LIMITED)
                    self._log_failure("role quarantine enforcement", rate_limited = rate_limited)
                    if rate_limited:
                        raise

        # ⸻ Members

        if enforce_type == "Members" or deleted:
            me = self.guild.me
            if not me or not me.guild_permissions.manage_roles:
                return

            true_quarantined = await self.get_members()
            role_quarantined = set(quarantine_role.members)

            for member in true_quarantined:
                if member.roles != [quarantine_role]:
                    await member.edit(roles = [quarantine_role], reason = "Quarantine enforcement.")

            # ⸻ Role members matches quarantined members. Exit.

            if role_quarantined == true_quarantined:
                return

            # ⸻ Some role members have the quarantine role but are not quarantined. Remove the role.

            for member in (role_quarantined - true_quarantined):
                try:
                    await member.remove_roles(quarantine_role, reason = "Quarantine enforcement.")
                except Forbidden:
                    pass
                except HTTPException as e:
                    rate_limited = (e.status == RATE_LIMITED)
                    self._log_failure("member quarantine enforcement (removal)", rate_limited = rate_limited)
                    if rate_limited:
                        raise

            # ⸻ Some quarantined members are missing the quarantine role. Add the role.

            for member in (true_quarantined - role_quarantined):
                try:
                    await member.add_roles(quarantine_role, reason = "Quarantine enforcement.")
                except Forbidden:
                    pass
                except HTTPException as e:
                    rate_limited = (e.status == RATE_LIMITED)
                    self._log_failure("member quarantine enforcement (addition)", rate_limited = rate_limited)
                    if rate_limited:
                        raise

        channel = await config.get_moderation_logging_channel()
        if deleted and channel:
            await format_send(
                channel,
                MessageType.warning,
                title    = "The quarantine role was deleted",
                subtitle = (
                   f"The quarantine role was deleted. I have created a new one ({quarantine_role.mention}) and transferred all quarantined members over.\n"
                    "If you'd like to remove quarantine operations, remove all members from quarantine first, then delete the role."
                ),
                footer   = "Please do not delete the quarantine role!",
                override = FormatOverride(prefix = False),
            )
