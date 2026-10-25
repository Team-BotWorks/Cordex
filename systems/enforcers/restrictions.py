from typing import cast, final, override

from discord import Guild, Object
from discord.ext.commands import Cog
from discord.ext.tasks import loop

from bot import Cordex, log

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Restriction Enforcing
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
class RestrictionEnforcer(Cog):
    """Removes command restrictions when the bot leaves a guild, when a command no longer exists, or when the database holds stale entries (possibly due to the bot leaving or being updated while offline)."""

    def __init__(self, bot : Cordex) -> None:
        super().__init__()
        self.bot = bot
        self._loop_restrictionenforce.start()

    async def _purge(self, pairs : list[tuple[int, str]]) -> int:
        if not pairs:
            return 0

        try:
            for guild_id, command_name in pairs:
                await self.bot.db.execute(
                    t"DELETE FROM CommandRestrictions WHERE guild_id = {guild_id} AND command_name = {command_name}",
                )
            await self.bot.db.commit()
        except Exception:
            log.exception("An exception occurred during the restriction purge. Moving on.")
            return 0

        for guild_id, command_name in pairs:
            guild = self.bot.get_guild(guild_id) or cast("Guild", cast("object", Object(id = guild_id)))
            self.bot.set_command_restriction(guild, command_name, None)

        return len(pairs)

    @override
    async def cog_unload(self) -> None:
        self._loop_restrictionenforce.cancel()

    @loop(minutes = 10)
    async def _loop_restrictionenforce(self) -> None:
        async with self.bot.db.execute(
            t"SELECT DISTINCT guild_id, command_name FROM CommandRestrictions;",
        ) as cursor:
            rows = await cursor.fetchall()

        true_guild_ids = {guild.id for guild in self.bot.guilds}
        true_commands  = {command.qualified_name for command in self.bot.tree.walk_commands()}

        configured_pairs = [(cast("int", row[0]), cast("str", row[1])) for row in rows]
        stale_pairs      = [
            (guild_id, command_name)
            for guild_id, command_name in configured_pairs
            if guild_id not in true_guild_ids or command_name not in true_commands
        ]

        purged = await self._purge(stale_pairs)
        if purged > 0:
            log.info("Restriction cleanup complete. %s restrictions removed.", purged)

    @_loop_restrictionenforce.before_loop
    async def _beforeloop_restrictionenforce(self) -> None:
        await self.bot.wait_until_ready()

    @Cog.listener("on_guild_remove")
    async def _listener_restriction_guildremove(self, guild : Guild) -> None:
        async with self.bot.db.execute(
            t"SELECT DISTINCT command_name FROM CommandRestrictions WHERE guild_id = {guild.id};",
        ) as cursor:
            rows = await cursor.fetchall()

        await self._purge([(guild.id, cast("str", row[0])) for row in rows])


async def setup(bot : Cordex) -> None:  # ruff: ignore[undocumented-public-function]
    cog = RestrictionEnforcer(bot)
    await bot.add_cog(cog)
