from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal, cast, final, overload

from discord import Guild, Member, NotFound, Role

from bot.types import GuildMessageable

from .restrictions import Restriction

if TYPE_CHECKING:
    from bot import Cordex

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Configuration State
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
class Config:
    """
    Represents a guild configuration.

    Parameters
    ----------
    bot : `Cordex`
        The bot instance.
    guild : `Guild`
        The guild the configuration belongs to.
    """

    def __init__(self, bot : Cordex, guild : Guild) -> None:
        super().__init__()
        self.bot   = bot
        self.guild = guild

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # get_command_allowed
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def get_command_allowed(self, command_name : str, /) -> list[Role | Member]:
        """
        Get the roles/members allowed to use a certain command.

        Parameters
        ----------
        command_name : `str`
            The command to get the allowed roles/members for.
        /

        Returns
        -------
        `list[Role | Member]`
            The roles/members allowed to use the command.
        """
        restriction = self.bot.get_command_restriction(self.guild, command_name)
        if not restriction:
            return []

        roles   = [role for role_id in sorted(restriction.role_ids) if (role := self.guild.get_role(role_id)) is not None]
        members = [member for user_id in sorted(restriction.user_ids) if (member := self.guild.get_member(user_id)) is not None]

        return [*roles, *members]

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # set_command_allowed
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def set_command_allowed(self, command_name : str, allowed : Sequence[Role | Member], /) -> None:
        """
        Set the roles/members allowed to use a certain command.

        Parameters
        ----------
        command_name : `str`
            The command to set the allowed roles/members for.
        allowed : `Sequence[Role | Member]`
            The roles/members allowed to use the command.
        /
        """
        role_ids = frozenset(target.id for target in allowed if isinstance(target, Role))
        user_ids = frozenset(target.id for target in allowed if isinstance(target, Member))

        try:
            await self.bot.db.execute(
                t"DELETE FROM CommandRestrictions WHERE guild_id = {self.guild.id} AND command_name = {command_name}",
            )

            for role_id in role_ids:
                await self.bot.db.execute(
                    t"INSERT INTO CommandRestrictions (guild_id, command_name, target_type, target_id) VALUES ({self.guild.id}, {command_name}, role, {role_id})",
                )

            for user_id in user_ids:
                await self.bot.db.execute(
                    t"INSERT INTO CommandRestrictions (guild_id, command_name, target_type, target_id) VALUES ({self.guild.id}, {command_name}, user, {user_id})",
                )

            await self.bot.db.commit()
        except Exception:
            await self.bot.db.rollback()
            raise

        self.bot.set_command_restriction(
            self.guild,
            command_name,
            Restriction(user_ids, role_ids) if (role_ids or user_ids) else None,
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # get_moderation_quarantine_role
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @overload
    async def get_moderation_quarantine_role(self, *, by_id : Literal[True]) -> int | None: ...

    @overload
    async def get_moderation_quarantine_role(self, *, by_id : Literal[False] = False) -> Role | None: ...

    async def get_moderation_quarantine_role(self, *, by_id : bool = False) -> Role | int | None:
        """
        Get the role the bot should assign to quarantined members, if any.

        Parameters
        ----------
        *
        by_id : `bool = False`
            Whether to return the ID of the role over an actual role object or not. This is useful in cases where the role may have been deleted.

        Returns
        -------
        `by_id = False -> Role | None`
            The role that the bot should assign to quarantined members. Returns `None` if not configured or deleted.
        `by_id = True -> int | None`
            The ID of the role that the bot should assign to quarantined members. Returns `None` if not configured or deleted.
        """
        async with self.bot.db.execute(
            t"SELECT config_value FROM Config WHERE guild_id = {self.guild.id} AND config_key = moderation_quarantine_role",
        ) as cursor:
            res = await cursor.fetchone()
            if not res:
                return None

        role_id = cast("int | None", res[0])
        if not role_id:
            return None

        if by_id:
            return role_id

        try:
            return self.guild.get_role(role_id) or await self.guild.fetch_role(role_id)
        except NotFound:
            return None

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # set_moderation_quarantine_role
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def set_moderation_quarantine_role(self, role : Role | None, /) -> None:
        """
        Set or reset the role the bot should assign to quarantined members.

        Parameters
        ----------
        role : `Role | None`
            The role the bot should assign to quarantined members, or `None` to reset.
        /
        """
        if not role:
            await self.bot.db.execute(
                t"DELETE FROM Config WHERE guild_id = {self.guild.id} AND config_key = moderation_quarantine_role",
            )
        else:
            await self.bot.db.execute(
                t"INSERT INTO Config (guild_id, config_key, config_value) VALUES ({self.guild.id}, moderation_quarantine_role, {role.id}) "
                t"ON CONFLICT (guild_id, config_key) DO UPDATE SET config_value = excluded.config_value",
            )
        await self.bot.db.commit()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # get_moderation_logging_channel
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @overload
    async def get_moderation_logging_channel(self, *, by_id : Literal[True]) -> int | None: ...

    @overload
    async def get_moderation_logging_channel(self, *, by_id : Literal[False] = False) -> GuildMessageable | None: ...

    async def get_moderation_logging_channel(self, *, by_id : bool = False) -> GuildMessageable | int | None:
        """
        Get the channel where the bot should log moderation actions, if any.

        Parameters
        ----------
        *
        by_id : `bool = False`
            Whether to return the ID of the channel over an actual channel object or not. This is useful in cases where the channel may have been deleted.

        Returns
        -------
        `by_id = False -> GuildMessageable | None`
            The channel in which the bot should log moderation actions. Returns `None` if not configured or deleted.
        `by_id = True -> int | None`
            The ID of the channel in which the bot should log moderation actions. Returns `None` if not configured or deleted.
        """
        async with self.bot.db.execute(
            t"SELECT config_value FROM Config WHERE guild_id = {self.guild.id} AND config_key = moderation_logging_channel",
        ) as cursor:
            res = await cursor.fetchone()
            if not res:
                return None

        channel_id = cast("int | None", res[0])
        if not channel_id:
            return None

        if by_id:
            return channel_id

        try:
            if not isinstance(
                log_channel := self.guild.get_channel(channel_id) or await self.guild.fetch_channel(channel_id),
                GuildMessageable,
            ):
                return None
        except NotFound:
            return None
        else:
            return log_channel

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # set_moderation_logging_channel
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def set_moderation_logging_channel(self, channel : GuildMessageable | None, /) -> None:
        """
        Set or reset the channel where the bot should log moderation actions.

        Parameters
        ----------
        channel : `GuildMessageable | None`
            The channel where the bot should log moderation actions, or `None` to reset.
        /
        """
        if not channel:
            await self.bot.db.execute(
                t"DELETE FROM Config WHERE guild_id = {self.guild.id} AND config_key = moderation_logging_channel",
            )
        else:
            await self.bot.db.execute(
                t"INSERT INTO Config (guild_id, config_key, config_value) VALUES ({self.guild.id}, moderation_logging_channel, {channel.id}) "
                t"ON CONFLICT (guild_id, config_key) DO UPDATE SET config_value = excluded.config_value",
            )
        await self.bot.db.commit()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # get_messages_delete_logging_channel
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @overload
    async def get_messages_delete_logging_channel(self, *, by_id : Literal[True]) -> int | None: ...

    @overload
    async def get_messages_delete_logging_channel(self, *, by_id : Literal[False] = False) -> GuildMessageable | None: ...

    async def get_messages_delete_logging_channel(self, *, by_id : bool = False) -> GuildMessageable | int | None:
        """
        Get the channel where the bot should log message deletions, if any.

        Parameters
        ----------
        *
        by_id : `bool = False`
            Whether to return the ID of the channel over an actual channel object or not. This is useful in cases where the channel may have been deleted.

        Returns
        -------
        `by_id = False -> GuildMessageable | None`
            The channel in which the bot should log message deletions. Returns `None` if not configured or deleted.
        `by_id = True -> int | None`
            The ID of the channel in which the bot should log message deletions. Returns `None` if not configured or deleted.
        """
        async with self.bot.db.execute(
            t"SELECT config_value FROM Config WHERE guild_id = {self.guild.id} AND config_key = messages_delete_channel",
        ) as cursor:
            res = await cursor.fetchone()
            if not res:
                return None

        channel_id = cast("int | None", res[0])
        if not channel_id:
            return None

        if by_id:
            return channel_id

        try:
            if not isinstance(
                log_channel := self.guild.get_channel(channel_id) or await self.guild.fetch_channel(channel_id),
                GuildMessageable,
            ):
                return None
        except NotFound:
            return None
        else:
            return log_channel

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # set_messages_delete_logging_channel
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def set_messages_delete_logging_channel(self, channel : GuildMessageable | None, /) -> None:
        """
        Set or reset the channel where the bot should log message deletions.

        Parameters
        ----------
        channel : `GuildMessageable | None`
            The channel where the bot should log message deletions, or `None` to reset.
        /
        """
        if not channel:
            await self.bot.db.execute(
                t"DELETE FROM Config WHERE guild_id = {self.guild.id} AND config_key = messages_delete_channel",
            )
        else:
            await self.bot.db.execute(
                t"INSERT INTO Config (guild_id, config_key, config_value) VALUES ({self.guild.id}, messages_delete_channel, {channel.id}) "
                t"ON CONFLICT (guild_id, config_key) DO UPDATE SET config_value = excluded.config_value",
            )
        await self.bot.db.commit()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # get_messages_edit_logging_channel
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @overload
    async def get_messages_edit_logging_channel(self, *, by_id : Literal[True]) -> int | None: ...

    @overload
    async def get_messages_edit_logging_channel(self, *, by_id : Literal[False] = False) -> GuildMessageable | None: ...

    async def get_messages_edit_logging_channel(self, *, by_id : bool = False) -> GuildMessageable | int | None:
        """
        Get the channel where the bot should log message edits, if any.

        Parameters
        ----------
        *
        by_id : `bool = False`
            Whether to return the ID of the channel over an actual channel object or not. This is useful in cases where the channel may have been deleted.

        Returns
        -------
        `by_id = False -> GuildMessageable | None`
            The channel in which the bot should log message edits. Returns `None` if not configured or deleted.
        `by_id = True -> int | None`
            The ID of the channel in which the bot should log message edits. Returns `None` if not configured or deleted.
        """
        async with self.bot.db.execute(
            t"SELECT config_value FROM Config WHERE guild_id = {self.guild.id} AND config_key = messages_edit_channel",
        ) as cursor:
            res = await cursor.fetchone()
            if not res:
                return None

        channel_id = cast("int | None", res[0])
        if not channel_id:
            return None

        if by_id:
            return channel_id

        try:
            if not isinstance(
                log_channel := self.guild.get_channel(channel_id) or await self.guild.fetch_channel(channel_id),
                GuildMessageable,
            ):
                return None
        except NotFound:
            return None
        else:
            return log_channel

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # set_messages_edit_logging_channel
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def set_messages_edit_logging_channel(self, channel : GuildMessageable | None, /) -> None:
        """
        Set or reset the channel where the bot should log message edits.

        Parameters
        ----------
        channel : `GuildMessageable | None`
            The channel where the bot should log message edits, or `None` to reset.
        /
        """
        if not channel:
            await self.bot.db.execute(
                t"DELETE FROM Config WHERE guild_id = {self.guild.id} AND config_key = messages_edit_channel",
            )
        else:
            await self.bot.db.execute(
                t"INSERT INTO Config (guild_id, config_key, config_value) VALUES ({self.guild.id}, messages_edit_channel, {channel.id}) "
                t"ON CONFLICT (guild_id, config_key) DO UPDATE SET config_value = excluded.config_value",
            )
        await self.bot.db.commit()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # get_whether_messages_preview
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def get_whether_messages_preview(self) -> bool:
        """
        Get whether the bot should provide previews for message links found in messages.

        Returns
        -------
        `bool`
            Whether the bot should provide previews for message links found in messages.
        """
        async with self.bot.db.execute(
            t"SELECT config_value FROM Config WHERE guild_id = {self.guild.id} AND config_key = messages_preview",
        ) as cursor:
            res = await cursor.fetchone()
            if not res:
                return False

        return bool(cast("int | None", res[0]))

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # set_whether_messages_preview
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def set_whether_messages_preview(self, enabled : bool, /) -> None:  # ruff: ignore[boolean-type-hint-positional-argument]
        """
        Set whether the bot should provide previews for message links found in messages.

        Parameters
        ----------
        enabled : `bool`
            Whether the bot should provide previews for message links found in messages.
        /
        """
        await self.bot.db.execute(
            t"INSERT INTO Config (guild_id, config_key, config_value) VALUES ({self.guild.id}, messages_preview, {int(enabled)}) "
            t"ON CONFLICT (guild_id, config_key) DO UPDATE SET config_value = excluded.config_value",
        )
        await self.bot.db.commit()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # get_whether_moderation_quarantine_enforce_channels
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def get_whether_moderation_quarantine_enforce_channels(self) -> bool:
        """
        Get whether the bot should automatically enforce quarantine for channels.

        Returns
        -------
        `bool`
            Whether the bot should automatically enforce quarantine for channels.
        """
        async with self.bot.db.execute(
            t"SELECT config_value FROM Config WHERE guild_id = {self.guild.id} AND config_key = moderation_quarantine_enforce_channels",
        ) as cursor:
            res = await cursor.fetchone()
            if not res:
                return False

        return bool(cast("int | None", res[0]))

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # set_whether_moderation_quarantine_enforce_channels
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def set_whether_moderation_quarantine_enforce_channels(self, enabled : bool, /) -> None:  # ruff: ignore[boolean-type-hint-positional-argument]
        """
        Set whether the bot should automatically enforce quarantine for channels.

        Parameters
        ----------
        enabled : `bool`
            Whether the bot should automatically enforce quarantine for channels.
        /
        """
        await self.bot.db.execute(
            t"INSERT INTO Config (guild_id, config_key, config_value) VALUES ({self.guild.id}, moderation_quarantine_enforce_channels, {int(enabled)}) "
            t"ON CONFLICT (guild_id, config_key) DO UPDATE SET config_value = excluded.config_value",
        )
        await self.bot.db.commit()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # get_whether_moderation_quarantine_enforce_roles
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def get_whether_moderation_quarantine_enforce_roles(self) -> bool:
        """
        Get whether the bot should automatically enforce quarantine for roles.

        Returns
        -------
        `bool`
            Whether the bot should automatically enforce quarantine for roles.
        """
        async with self.bot.db.execute(
            t"SELECT config_value FROM Config WHERE guild_id = {self.guild.id} AND config_key = moderation_quarantine_enforce_roles",
        ) as cursor:
            res = await cursor.fetchone()
            if not res:
                return False

        return bool(cast("int | None", res[0]))

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # set_whether_moderation_quarantine_enforce_roles
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def set_whether_moderation_quarantine_enforce_roles(self, enabled : bool, /) -> None:  # ruff: ignore[boolean-type-hint-positional-argument]
        """
        Set whether the bot should automatically enforce quarantine for roles.

        Parameters
        ----------
        enabled : `bool`
            Whether the bot should automatically enforce quarantine for roles.
        /
        """
        await self.bot.db.execute(
            t"INSERT INTO Config (guild_id, config_key, config_value) VALUES ({self.guild.id}, moderation_quarantine_enforce_roles, {int(enabled)}) "
            t"ON CONFLICT (guild_id, config_key) DO UPDATE SET config_value = excluded.config_value",
        )
        await self.bot.db.commit()
