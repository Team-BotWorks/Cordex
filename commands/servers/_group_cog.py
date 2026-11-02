from typing import final

from discord.app_commands import allowed_installs, command, guild_only
from discord.ext.commands import GroupCog

from bot import Cordex, Interaction
from core.state import requires_restriction

from .commands import run_server_commands
from .configure import run_server_configure
from .info import run_server_info
from .personalize import run_server_personalize

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Server Group Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
@guild_only
@allowed_installs(guilds = True, users = False)
class ServerCommands(
    GroupCog,
    name        = "server",
    description = "Server commands.",
):
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /server commands Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @requires_restriction
    @command(
        name        = "commands",
        description = "Configure guild commands.",
    )
    async def cmd_server_commands(self, interaction : Interaction) -> None:
        await run_server_commands(interaction)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /server configure Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @requires_restriction
    @command(
        name        = "configure",
        description = "Configure guild settings.",
    )
    async def cmd_server_configure(self, interaction : Interaction) -> None:
        await run_server_configure(interaction)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /server info Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @command(
        name        = "info",
        description = "View information for this guild.",
    )
    async def cmd_server_info(self, interaction : Interaction) -> None:
        await run_server_info(interaction)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /server personalize Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @requires_restriction
    @command(
        name        = "personalize",
        description = "Personalize my avatar, banner, biography, and display name style.",
    )
    async def cmd_server_personalize(self, interaction : Interaction) -> None:
        await run_server_personalize(interaction)


async def setup(bot : Cordex) -> None:
    cog = ServerCommands()
    await bot.add_cog(cog)
