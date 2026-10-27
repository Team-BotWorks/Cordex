from typing import cast, final, override

from discord import Guild, HTTPException, Member, Role
from discord.abc import GuildChannel
from discord.ext.commands import Cog
from discord.ext.tasks import loop

from bot import Cordex, log
from core.moderation import QuarantineManager

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Quarantine Enforcing
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
class QuarantineEnforcer(Cog):
    """Enforces quarantines by ensuring specific channel and role permissions are configured properly and quarantine role members remain in proper state."""

    def __init__(self, bot : Cordex) -> None:
        super().__init__()
        self.bot = bot
        self._loop_quarantineenforce.start()

    @override
    async def cog_unload(self) -> None:
        self._loop_quarantineenforce.cancel()

    @loop(minutes = 10)
    async def _loop_quarantineenforce(self) -> None:
        async with self.bot.db.execute(t"SELECT DISTINCT guild_id FROM Quarantines;") as cursor:
            rows = await cursor.fetchall()

        quarantined_guild_ids = cast("set[int]", {row[0] for row in rows})
        true_guild_ids        = {guild.id for guild in self.bot.guilds}
        stale_guild_ids       = [guild_id for guild_id in quarantined_guild_ids if guild_id not in true_guild_ids]

        if stale_guild_ids:
            try:
                await self.bot.db.execute(t"DELETE FROM Quarantines WHERE guild_id IN {tuple(stale_guild_ids)}")
                await self.bot.db.commit()
            except Exception:
                log.exception("An exception occurred during the quarantine resets. Moving on.")
            else:
                log.info("Quarantine reset complete. %s guilds reset.", len(stale_guild_ids))

        for guild in self.bot.guilds:
            manager = QuarantineManager(self.bot, guild)
            config  = self.bot.config(guild)

            before_role_id = await config.get_moderation_quarantine_role(by_id = True)
            try:
                await manager.enforce("Channels")

                after_role_id = await config.get_moderation_quarantine_role(by_id = True)
                if before_role_id == after_role_id:
                    await manager.enforce("Role")
                    await manager.enforce("Members")
            except HTTPException as e:
                if e.status == 429:
                    break

    @_loop_quarantineenforce.before_loop
    async def _beforeloop_quarantineenforce(self) -> None:
        await self.bot.wait_until_ready()

    @Cog.listener("on_guild_remove")
    async def _listener_quarantineenforce_guildleave(self, guild : Guild) -> None:
        await QuarantineManager(self.bot, guild).remove_all_members()

    @Cog.listener("on_guild_channel_update")
    async def _listener_quarantineenforce_channelupdate(self, before : GuildChannel, after : GuildChannel) -> None:
        quarantine_role = await self.bot.config(after.guild).get_moderation_quarantine_role()
        if not quarantine_role:
            return

        before_ow = before.overwrites_for(quarantine_role)
        after_ow  = after.overwrites_for(quarantine_role)

        if before_ow == after_ow:
            return

        expected_send = False
        expected_read = False

        checks = [
            after_ow.send_messages            == expected_send,
            after_ow.read_messages            == expected_read,
            after_ow.send_messages_in_threads == expected_send,
            after_ow.create_public_threads    == expected_send,
            after_ow.create_private_threads   == expected_send,
            after_ow.create_instant_invite    == expected_send,
        ]

        if all(checks):
            return

        await QuarantineManager(self.bot, after.guild).enforce("Channels")

    @Cog.listener("on_guild_channel_create")
    async def _listener_quarantineenforce_channelcreate(self, channel : GuildChannel) -> None:
        quarantine_role = await self.bot.config(channel.guild).get_moderation_quarantine_role()
        if not quarantine_role:
            return

        await QuarantineManager(self.bot, channel.guild).enforce("Channels")

    @Cog.listener("on_guild_role_update")
    async def _listener_quarantineenforce_roleupdate(self, before : Role, after : Role) -> None:
        if before.position == after.position:
            return

        await QuarantineManager(self.bot, after.guild).enforce("Role")

    @Cog.listener("on_guild_role_delete")
    async def _listener_quarantineenforce_roledelete(self, role : Role) -> None:
        quarantine_role_id = await self.bot.config(role.guild).get_moderation_quarantine_role(by_id = True)
        if role.id != quarantine_role_id:
            return

        await QuarantineManager(self.bot, role.guild).enforce()

    @Cog.listener("on_member_update")
    async def _listener_quarantineenforce_memberupdate(self, before : Member, after : Member) -> None:
        if before.roles == after.roles:
            return

        quarantine_role = await self.bot.config(after.guild).get_moderation_quarantine_role()
        if not quarantine_role:
            return

        if after.roles == [quarantine_role]:
            return

        await QuarantineManager(self.bot, after.guild).enforce("Members")

    @Cog.listener("on_member_join")
    async def _listener_quarantineenforce_memberjoin(self, member : Member) -> None:
        manager = QuarantineManager(self.bot, member.guild)
        quarantined_members = await manager.get_members()

        if not quarantined_members:
            return

        if member in quarantined_members:
            await manager.enforce("Members")


async def setup(bot : Cordex) -> None:  # ruff: ignore[undocumented-public-function]
    cog = QuarantineEnforcer(bot)
    await bot.add_cog(cog)
