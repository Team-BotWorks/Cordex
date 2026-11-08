from typing import cast, final, override

from discord import Guild
from discord.ext.commands import Cog
from discord.ext.tasks import loop

from bot import Cordex, log
from core.moderation import CasesManager

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Case Enforcing
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
class CasesEnforcer(Cog):
    """Deletes cases when the bot leaves a guild or when the database guilds don't match the current ones (possibly due to the bot leaving while offline)."""

    def __init__(self, bot : Cordex) -> None:
        super().__init__()
        self.bot = bot
        self._loop_caseenforce.start()

    @override
    async def cog_unload(self) -> None:
        self._loop_caseenforce.cancel()

    @loop(minutes = 10)
    async def _loop_caseenforce(self) -> None:
        async with self.bot.db.execute(t"SELECT DISTINCT guild_id FROM Cases;") as cursor:
            rows = await cursor.fetchall()

        locked_guild_ids = cast("set[int]", {row[0] for row in rows})
        true_guild_ids   = {guild.id for guild in self.bot.guilds}
        stale_guild_ids  = [guild_id for guild_id in locked_guild_ids if guild_id not in true_guild_ids]

        if stale_guild_ids:
            try:
                await self.bot.db.execute(t"DELETE FROM Cases WHERE guild_id IN {tuple(stale_guild_ids)}")
                await self.bot.db.commit()
            except Exception:
                log.exception("An exception occurred during the case deletions. Moving on.")
            else:
                log.info("Case deletion complete. %s guilds reset.", len(stale_guild_ids))

    @_loop_caseenforce.before_loop
    async def _beforeloop_caseenforce(self) -> None:
        await self.bot.wait_until_ready()

    @Cog.listener("on_guild_remove")
    async def _listener_caseenforce_guildleave(self, guild : Guild) -> None:
        await CasesManager(self.bot, guild).delete_all_cases()


async def setup(bot : Cordex) -> None:  # ruff: ignore[undocumented-public-function]
    await bot.add_cog(CasesEnforcer(bot))
