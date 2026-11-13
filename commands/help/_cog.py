from typing import final

from discord.app_commands import Choice, Group, command, describe
from discord.ext.commands import Cog

from bot import Cordex, Interaction
from core.state import unrestrictable

from .help import run_help

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Help Command
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
class HelpCommand(Cog):
    @unrestrictable
    @command(
        name        = "help",
        description = "Receive helpful information for a command.",
    )
    @describe(command = "The command to view information for.")
    async def cmd_help(self, interaction : Interaction, command : str) -> None:
        await run_help(interaction, command)

    @cmd_help.autocomplete("command")
    async def autocomplete_cmdhelp(self, interaction : Interaction, current : str) -> list[Choice[str]]:
        return [
            Choice(name = f"/{command.qualified_name}", value = command.qualified_name)
            for command in interaction.client.tree.walk_commands()
            if not isinstance(command, Group)
            and current.lower() in command.qualified_name.lower()
        ][:25]


async def setup(bot : Cordex) -> None:
    await bot.add_cog(HelpCommand())
