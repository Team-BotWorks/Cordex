from platform import python_version
from typing import Self, final

from discord import __version__ as DISCORD_VERSION  # ruff: ignore[lowercase-imported-as-non-lowercase]

from bot import Interaction
from bot.ui import Container, TextDisplay, View, VisibleLargeSeparator
from constants import COLOR_BLUE
from core.utilities import format_table

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /about Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


async def run_about(interaction : Interaction) -> None:
    """
    View information about Cordex.

    Parameters
    ----------
    interaction : `Interaction`
        The interaction context to run the command with.
    """
    client = interaction.client

    await interaction.response.defer()

    owners = client.developers
    s = "s" if len(owners) > 1 else ""

    @final
    class AboutView(View):
        container = Container[Self](
            TextDisplay("# About Me,"),
            VisibleLargeSeparator(),
            TextDisplay(
                format_table(
                    {
                       f"Owner{s}"     : ", ".join(owner.name for owner in owners),
                        "Bot Version"  : f"v{client.version}",
                        "Guilds"       : len(client.guilds),
                        "Unique Users" : len(client.users),
                        "Commands"     : len(list(client.tree.walk_commands())),
                        "Latency"      : f"{client.latency * 1000:.2f}",
                        "Python"       : python_version(),
                        "Discord.py"   : DISCORD_VERSION,
                    },
                ),
            ),
            color = COLOR_BLUE,
        )

    await interaction.followup.send(view = AboutView())
