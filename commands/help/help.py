from typing import Self, final

from discord import AppCommandOptionType
from discord.utils import get as utils_get

from bot import Interaction
from bot.ui import Container, TextDisplay, View, VisibleLargeSeparator
from constants import REQUIRED_EMOJI
from core.exceptions import send_bad_argument
from core.help import HelpCommand, HelpParameter, get_command_help
from core.utilities import format_command

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /help Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


def _build_parameter_sections(parameters : list[HelpParameter]) -> str:
    option_types = {
        AppCommandOptionType.string      : "Text Input",
        AppCommandOptionType.integer     : "Integer",
        AppCommandOptionType.boolean     : "Boolean",
        AppCommandOptionType.user        : "User",
        AppCommandOptionType.channel     : "Channel",
        AppCommandOptionType.role        : "Role",
        AppCommandOptionType.mentionable : "Role or User",
        AppCommandOptionType.number      : "Number",
        AppCommandOptionType.attachment  : "Attachment",
    }

    sections : list[str] = []
    for parameter in parameters:
        if parameter.choices:
            option_type = f"Choice[{", ".join(choice.name for choice in parameter.choices)}]"
        elif parameter.autocomplete:
            option_type = "Autocomplete"
        else:
            option_type = option_types[parameter.type]

        required = f"{REQUIRED_EMOJI} " if parameter.required else ""
        sections.append(
            f"{required}`{parameter.name}`\n"
            f"-# {option_type} | *{parameter.description}*",
        )

    return "\n".join(sections)


@final
class _HelpView(View):
    def __init__(self, command : HelpCommand) -> None:
        super().__init__()
        container = Container[Self](
            TextDisplay(
                f"# {format_command(command.name)}\n"
                f"-# *{command.description}*",
            ),
        )

        if parameters := command.parameters:
            container.add_items(
                VisibleLargeSeparator(),
                TextDisplay(_build_parameter_sections(parameters)),
            )
            if any(parameter.required for parameter in parameters):
                container.add_items(
                    VisibleLargeSeparator(),
                    TextDisplay(f"-# {REQUIRED_EMOJI} **Denotes a required argument.**"),
                )

        self.add_item(container)


async def run_help(interaction : Interaction, command_name : str) -> None:
    """
    Receive helpful information for a command.

    Parameters
    ----------
    interaction : `Interaction`
        The interaction context to run the command with.
    command_name : `str`
        The name of the command to view information for.
    """
    command = utils_get(interaction.client.tree.walk_commands(), qualified_name = command_name)
    if not command:
        await send_bad_argument(
            interaction,
            subtitle = {"command" : "Command not found."},
        )
        return

    await interaction.response.send_message(view = _HelpView(get_command_help(command)))
