from contextlib import suppress
from typing import cast, final, override

from discord import Guild, HTTPException
from discord.abc import GuildChannel
from discord.ext.commands import Cog
from discord.ext.tasks import loop

from bot import Cordex, log
from bot.types import GuildMessagableChannel
from core.moderation import LockdownManager
from core.moderation.cases import CasesManager
from core.moderation.payloads import LockdownRemovePayload

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Lockdown Enforcing
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
class LockdownEnforcer(Cog):
    """Enforces lockdowns by ensuring specific channel permissions are configured properly."""

    def __init__(self, bot : Cordex) -> None:
        super().__init__()
        self.bot = bot
        self._loop_lockdownenforce.start()

    @override
    async def cog_unload(self) -> None:
        self._loop_lockdownenforce.cancel()

    @loop(minutes = 10)
    async def _loop_lockdownenforce(self) -> None:
        async with self.bot.db.execute(t"SELECT DISTINCT guild_id FROM Lockdowns;") as cursor:
            rows = await cursor.fetchall()

        locked_guild_ids = cast("set[int]", {row[0] for row in rows})
        true_guild_ids   = {guild.id for guild in self.bot.guilds}
        stale_guild_ids  = [guild_id for guild_id in locked_guild_ids if guild_id not in true_guild_ids]

        if stale_guild_ids:
            try:
                await self.bot.db.execute(t"DELETE FROM Lockdowns WHERE guild_id IN {tuple(stale_guild_ids)}")
                await self.bot.db.commit()
            except Exception:
                log.exception("An exception occurred during the lockdown resets. Moving on.")
            else:
                log.info("Lockdown reset complete. %s guilds reset.", len(stale_guild_ids))

        for guild in self.bot.guilds:
            try:
                await LockdownManager(self.bot, guild).enforce()
            except HTTPException as e:
                if e.status == 429:
                    break

    @_loop_lockdownenforce.before_loop
    async def _beforeloop_lockdownenforce(self) -> None:
        await self.bot.wait_until_ready()

    @Cog.listener("on_guild_remove")
    async def _listener_lockdownenforce_guildleave(self, guild : Guild) -> None:
        await LockdownManager(self.bot, guild).remove_all_channels()

    @Cog.listener("on_guild_channel_update")
    async def _listener_lockdownenforce_channelupdate(self, before : GuildChannel, after : GuildChannel) -> None:
        if before.overwrites == after.overwrites:
            return

        everyone = after.guild.default_role
        if after.overwrites_for(everyone).send_messages is False:
            return

        manager = LockdownManager(self.bot, after.guild)
        if after.id in await manager.get_channels(by_id = True):
            with suppress(HTTPException):
                await manager.enforce()

    @Cog.listener("on_guild_channel_delete")
    async def _listener_lockdownenforce_channeldelete(self, channel : GuildChannel) -> None:
        guild = channel.guild

        if not isinstance(channel, GuildMessagableChannel):
            return

        if channel.id in await LockdownManager(self.bot, guild).get_channels(by_id = True):
            await self.bot.db.execute(
                t"DELETE FROM Lockdowns WHERE channel_id = {channel.id} AND guild_id = {guild.id}",
            )
            await self.bot.db.commit()

            payload = LockdownRemovePayload(
                moderator = guild.me,
                channel   = channel,
                reason    = "The channel was deleted.",
            )
            await CasesManager(self.bot, guild).create_case(payload)


async def setup(bot : Cordex) -> None:  # ruff: ignore[undocumented-public-function]
    cog = LockdownEnforcer(bot)
    await bot.add_cog(cog)
