from typing import cast, final, override

from discord import AuditLogAction, Guild, HTTPException, Member, Role, User
from discord.abc import GuildChannel
from discord.ext.commands import Cog
from discord.ext.tasks import loop

from bot import Cordex, log
from core.moderation import CasesManager, QuarantineManager

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

    def _quarantine(self, guild : Guild) -> QuarantineManager:
        return QuarantineManager(self.bot, guild)

    def _cases(self, guild : Guild) -> CasesManager:
        return CasesManager(self.bot, guild)

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
            manager = self._quarantine(guild)
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
        await self._quarantine(guild).remove_all()

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

        await self._quarantine(after.guild).enforce("Channels")

    @Cog.listener("on_guild_channel_create")
    async def _listener_quarantineenforce_channelcreate(self, channel : GuildChannel) -> None:
        quarantine_role = await self.bot.config(channel.guild).get_moderation_quarantine_role()
        if not quarantine_role:
            return

        await self._quarantine(channel.guild).enforce("Channels")

    @Cog.listener("on_guild_role_update")
    async def _listener_quarantineenforce_roleupdate(self, before : Role, after : Role) -> None:
        if before.position == after.position:
            return

        await self._quarantine(after.guild).enforce("Role")

    @Cog.listener("on_guild_role_delete")
    async def _listener_quarantineenforce_roledelete(self, role : Role) -> None:
        quarantine_role_id = await self.bot.config(role.guild).get_moderation_quarantine_role(by_id = True)
        if role.id != quarantine_role_id:
            return

        await self._quarantine(role.guild).enforce()

    @Cog.listener("on_member_update")
    async def _listener_quarantineenforce_memberupdate_role(self, before : Member, after : Member) -> None:
        if before.roles == after.roles:
            return

        quarantine_role = await self.bot.config(after.guild).get_moderation_quarantine_role()
        if not quarantine_role:
            return

        if after.roles == [quarantine_role]:
            return

        await self._quarantine(after.guild).enforce("Members")

    @Cog.listener("on_member_join")
    async def _listener_quarantineenforce_memberjoin(self, member : Member) -> None:
        manager = self._quarantine(member.guild)
        quarantined_members = await manager.get()

        if not quarantined_members:
            return

        if member in quarantined_members:
            await manager.enforce("Members")

    @Cog.listener("on_member_ban")
    async def _listener_quarantineenforce_memberban(self, guild : Guild, member : Member) -> None:
        manager = self._quarantine(member.guild)
        if not await manager.is_quarantined(member):
            return

        await manager.remove(member)
        if case := await self._cases(guild).get_member_active_case(member):
            await case.expire()

    @Cog.listener("on_member_remove")
    async def _listener_quarantineenforce_memberremove(self, member : Member) -> None:
        manager = self._quarantine(member.guild)
        if not await manager.is_quarantined(member):
            return

        async for entry in member.guild.audit_logs(action = AuditLogAction.kick, limit = 1):
            target = entry.target
            if target and isinstance(target, User | Member):
                target = cast("Member", target)
                await manager.remove(target)
                if case := await self._cases(entry.guild).get_member_active_case(target):
                    await case.expire()

    @Cog.listener("on_member_update")
    async def _listener_quarantineenforce_memberupdate_timeout(self, before : Member, after : Member) -> None:
        manager = self._quarantine(after.guild)
        if not await manager.is_quarantined(after):
            return

        if (
            before.timed_out_until != after.timed_out_until
            and after.timed_out_until is not None
        ):
            await manager.remove(after)
            if case := await self._cases(after.guild).get_member_active_case(after):
                await case.expire()


async def setup(bot : Cordex) -> None:  # ruff: ignore[undocumented-public-function]
    cog = QuarantineEnforcer(bot)
    await bot.add_cog(cog)
