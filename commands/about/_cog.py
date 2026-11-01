from typing import final

from discord.app_commands import command
from discord.ext.commands import Cog

from bot import Cordex, Interaction
from core.state import unrestrictable

from .about import run_about

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# About Command
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
class AboutCommand(Cog):
    def __init__(self) -> None:
        super().__init__()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /about Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @unrestrictable
    @command(
        name        = "about",
        description = "View information about me.",
    )
    async def cmd_about(self, interaction : Interaction) -> None:
        await run_about(interaction)


async def setup(bot : Cordex) -> None:
    cog = AboutCommand()
    await bot.add_cog(cog)
