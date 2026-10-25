# pyright: reportIncompatibleMethodOverride = false

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Self, final, override

from discord import Member, Role, SelectOption, User
from discord.ext.commands import GroupCog

from bot import Cordex, Interaction, log
from bot.types import AnnotatedCommand
from bot.ui import (
    ActionRow,
    Button,
    ButtonSection,
    Checkbox,
    Container,
    Item,
    Label,
    MentionableSelect,
    Modal,
    Select,
    TextDisplay,
)
from constants import (
    ACCEPTED_EMOJI,
    COG_EMOJI,
    COMMAND_EMOJI,
    EMOJI_EMOJI,
    HORIZONTAL_SETTINGS,
    MEMBER_EMOJI,
    MEMBERS_EMOJI,
    MODERATION_EMOJI,
    PENCIL_EMOJI,
    TEXT_EMOJI,
    WARNING_EMOJI,
)
from core.exceptions import send_bad_argument, send_bad_operation
from core.paginator import Footer, UnnamedPaginator
from core.responses import FormatOverride, MessageType, PunctuationOverride, format_send
from core.state import is_restrictable, is_restriction_required
from core.utilities import format_command

COG_EMOJIS : dict[str, str] = {
    "moderation" : MODERATION_EMOJI,
    "server"     : EMOJI_EMOJI,
    "role"       : MEMBERS_EMOJI,
    "channel"    : TEXT_EMOJI,
    "member"     : MEMBER_EMOJI,
}

type CommandList = list[AnnotatedCommand]

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /server commands Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@dataclass
class _State:
    title    : str
    commands : CommandList


def _build_sections(interaction : Interaction, state : _State) -> list[str | Item[UnnamedPaginator]]:
    commands = state.commands
    mentions = [format_command(command.qualified_name) for command in commands]

    guild = interaction.guild
    if not guild:
        return []

    sections : list[str | Item[UnnamedPaginator]] = []
    for i, (command, mention) in enumerate(zip(commands, mentions, strict = False), start = 1):
        requires_restriction = is_restriction_required(command)
        is_restricted = interaction.client.get_command_restriction(guild, command.qualified_name) is not None

        status = ""
        if is_restricted:
            status = ACCEPTED_EMOJI
        if requires_restriction and not is_restricted:
            status = WARNING_EMOJI
        if not requires_restriction and not is_restricted:
            status = ""

        sections.append(
            ButtonSection(
                f"**{i}.** {status}{mention}\n"
                f"-# {COG_EMOJI if requires_restriction else ""} {command.description or "*No description provided.*"}",
                button = _ConfigButton(command, state),
            ),
        )

    return sections


async def _refresh(interaction : Interaction, view : UnnamedPaginator, state : _State) -> None:
    view.update_data(state.title, _build_sections(interaction, state))
    await interaction.response.edit_message(view = view)


@final
class _ConfigModal(Modal):
    def __init__(
        self,
        command : AnnotatedCommand,
        allowed : Sequence[Role | Member],
        view    : UnnamedPaginator,
        state   : _State,
    ) -> None:
        super().__init__(title = f"Configuring /{command.qualified_name}")
        self._command = command
        self._view    = view
        self._state   = state

        mentions = "\n".join(f"- {target.mention}" for target in allowed) or "- @everyone"

        self.current_allowed = TextDisplay[Self](
           f"**Currently allowed:**\n"
           f"{mentions}\n\n"
            "Please note that the guild owner may *always* run commands.",
        )

        configuration_required = is_restriction_required(command)

        description = "The users/roles allowed to run the command. Uses OR logic."
        if not configuration_required:
            description += " Leave empty to allow everyone."

        self._allowed = MentionableSelect[Self](
            placeholder    = "Enter up to 25 users/roles...",
            min_values     = 1 if configuration_required else 0,
            max_values     = 25,
            default_values = allowed,
            required       = configuration_required,
        )
        self.allowed  = Label[Self](
            text        = "Allowed",
            description = description,
            component   = self._allowed,
        )

        self.add_items(self.current_allowed, self.allowed)

    @override
    async def on_submit(self, interaction : Interaction) -> None:
        allowed = [member for member in self._allowed.values if not isinstance(member, User)]

        client = interaction.client
        guild  = interaction.guild
        if not guild:
            return

        config = client.config(guild)
        quarantine_role = await config.get_moderation_quarantine_role()
        if quarantine_role in allowed:
            await send_bad_argument(
                interaction,
                subtitle = {"allowed" : "The quarantine role cannot be used as a command restriction."},
            )
            return

        if guild.default_role in allowed:
            await send_bad_argument(
                interaction,
                subtitle = {"allowed" : "The @everyone role cannot be used as a command restriction."},
            )
            return

        try:
            await config.set_command_allowed(self._command.qualified_name, allowed)
        except Exception:
            await send_bad_operation(interaction, title = "configure command")
            raise

        await _refresh(interaction, self._view, self._state)

        name = format_command(self._command.qualified_name)

        if allowed:
            mentions = "\n".join(target.mention for target in allowed)

            title    = f"set restrictions for {name}"
            subtitle = (
                "Allowed:\n"
               f"{mentions}"
            )
        else:
            title    = f"removed restrictions for {name}"
            subtitle = None

        await format_send(
            interaction,
            MessageType.success,
            title    = title,
            subtitle = subtitle,
            override = FormatOverride(punctuation = PunctuationOverride(subtitle = False)),
        )


@final
class _ConfigButton(Button[UnnamedPaginator]):
    def __init__(self, command : AnnotatedCommand, state : _State) -> None:
        super().__init__(emoji = PENCIL_EMOJI)
        self._command = command
        self._state   = state

    @override
    async def callback(self, interaction : Interaction) -> None:
        guild = interaction.guild
        if not guild or not self.view:
            return

        allowed = await interaction.client.config(guild).get_command_allowed(self._command.qualified_name)

        await interaction.response.send_modal(_ConfigModal(self._command, allowed, self.view, self._state))


@final
class _GroupConfigModal(Modal):
    def __init__(
        self,
        group_name : str,
        view       : UnnamedPaginator,
        state      : _State,
    ) -> None:
        super().__init__(title = f"Configuring {group_name}")
        self._commands = list(state.commands)
        self._view     = view
        self._state    = state

        self.note = TextDisplay[Self]("Please note that the guild owner may *always* run commands.")

        self._allowed = MentionableSelect[Self](
            placeholder = "Enter up to 25 users/roles...",
            min_values  = 0,
            max_values  = 25,
            required    = False,
        )
        self.allowed  = Label[Self](
            text        = "Allowed",
            description = "The users/roles allowed to run these commands. Uses OR logic. Leave empty to allow everyone.",
            component   = self._allowed,
        )

        self._force = Checkbox[Self](default = True)
        self.force  = Label[Self](
            text        = "Force",
            description = "Whether to overwrite commands that are already restricted.",
            component   = self._force,
        )

        self.add_items(self.note, self.allowed, self.force)

        self._ignore : Checkbox[Self] | None = None
        if not all(is_restriction_required(command) for command in self._commands):
            self._ignore = Checkbox[Self](default = True)
            self.ignore  = Label[Self](
                text        = "Ignore",
                description = "Whether to ignore commands that do not require restriction.",
                component   = self._ignore,
            )

            self.add_item(self.ignore)

    @override
    async def on_submit(self, interaction : Interaction) -> None:
        allowed = [member for member in self._allowed.values if not isinstance(member, User)]
        force   = self._force.value
        ignore  = self._ignore.value if self._ignore is not None else False

        client = interaction.client
        guild  = interaction.guild
        if not guild:
            return

        config = client.config(guild)
        quarantine_role = await config.get_moderation_quarantine_role()
        if quarantine_role in allowed:
            await send_bad_argument(
                interaction,
                subtitle = {"allowed" : "The quarantine role cannot be used as a command restriction."},
            )
            return

        if guild.default_role in allowed:
            await send_bad_argument(
                interaction,
                subtitle = {"allowed" : "The @everyone role cannot be used as a command restriction."},
            )
            return

        affected : CommandList = []
        for command in self._commands:
            if not force and client.get_command_restriction(guild, command.qualified_name) is not None:
                continue

            if ignore and not is_restriction_required(command):
                continue

            if not allowed and is_restriction_required(command):
                continue

            try:
                await config.set_command_allowed(command.qualified_name, allowed)
                affected.append(command)
            except Exception:
                await send_bad_operation(interaction, title = "configure group")
                raise

        if affected:
            await _refresh(interaction, self._view, self._state)

        if not affected:
            subtitle = "No commands in this group were affected."
        elif len(affected) == len(self._commands):
            subtitle = "Every command in this group was affected."
        else:
            mentions = "\n".join(format_command(command.qualified_name) for command in affected)
            subtitle = (
                "Affected commands:\n"
               f"{mentions}"
            )

        await format_send(
            interaction,
            MessageType.success,
            title    = "configured group",
            subtitle = subtitle,
            override = FormatOverride(punctuation = PunctuationOverride(subtitle = False)),
        )


@final
class _GroupConfigButton(Button[UnnamedPaginator]):
    def __init__(self, group_name : str, state : _State) -> None:
        super().__init__(emoji = PENCIL_EMOJI)
        self._group_name = group_name
        self._state      = state

    @override
    async def callback(self, interaction : Interaction) -> None:
        if not self.view:
            return

        await interaction.response.send_modal(_GroupConfigModal(self._group_name, self.view, self._state))


@final
class _CategorySelect(Select[UnnamedPaginator]):
    def __init__(self, bot : Cordex, commands : CommandList, state : _State) -> None:
        self._commands = commands
        self._state    = state
        self._emojis : dict[str, str] = {}

        options = [
            SelectOption(
                label       = "All Commands",
                value       = "all",
                description = "All bot commands.",
                emoji       = HORIZONTAL_SETTINGS,
                default     = True,
            ),
        ]

        for cog in bot.cogs.values():

            # ⸻ Check that it's a GroupCog, and that the cog name is a str.

            if not isinstance(cog, GroupCog) or not isinstance(name := cog.__cog_group_name__, str):
                continue

            description = cog.__cog_group_description__

            # ⸻ Get the description and children.

            children = ", ".join(f"/{command.qualified_name.replace(name, "").strip()}" for command in cog.walk_app_commands())
            subtitle = f"{description} Children: {children}"

            if len(subtitle) > 100:
                subtitle = f"{description} Numerous children."

            # ⸻ Get the emoji.

            emoji = COG_EMOJIS.get(name)
            if emoji is None:
                log.warning("No emoji found for cog group '%s'.", name)
            else:
                self._emojis[name] = emoji

            options.append(
                SelectOption(
                    label       = f"{name.title()} Commands",
                    value       = name,
                    description = subtitle,
                    emoji       = emoji,
                ),
            )

        super().__init__(
            placeholder = "Select a command category.",
            options     = options,
        )

    @override
    async def callback(self, interaction : Interaction) -> None:
        value = self.values[0]

        # ⸻ Filter the title and commands based on the select input

        if value == "all":
            filtered   = self._commands
            group_name = None
            title      = f"# {HORIZONTAL_SETTINGS} All Commands"
        else:
            emoji  = self._emojis.get(value)
            prefix = f"{emoji} " if emoji else ""

            filtered   = [command for command in self._commands if command.qualified_name.startswith(value)]
            group_name = f"{value.title()} Commands"
            title      = f"# {prefix}{group_name}"

        if not self.view:
            return

        for option in self.options:
            option.default = (option.value == value)

        self._state.title    = title
        self._state.commands = filtered

        self.view.set_title_button(_GroupConfigButton(group_name, self._state) if group_name is not None else None)
        self.view.update_data(title, _build_sections(interaction, self._state))

        await interaction.response.edit_message(view = self.view)


async def run_server_commands(interaction : Interaction) -> None:
    """
    Configure guild commands.

    Parameters
    ----------
    interaction : `Interaction`
        The interaction context to run the command with.
    """
    await interaction.response.defer(ephemeral = True)

    # ⸻ Grab the commands from the cache and then sort them.

    commands = [command for command in interaction.client.tree.walk_commands() if is_restrictable(command)]
    commands.sort(key = lambda c : c.qualified_name)

    # ⸻ Build the view,

    state = _State(f"# {HORIZONTAL_SETTINGS} All Commands", commands)

    view = UnnamedPaginator(
        state.title,
        _build_sections(interaction, state),
        footer    = Footer("Page {smallest_page} of {biggest_page} | {count} Command{s}"),
        container = True,
    )
    view.add_under(
        TextDisplay(
            f"-# {COG_EMOJI} **Denotes a command that requires restriction.**\n"
            f"-# {WARNING_EMOJI} **Denotes a command that requires restriction, but does not have any set.**\n"
            f"-# {ACCEPTED_EMOJI} **Denotes a command that has restrictions set.**",
        ),
    )
    view.add_above(
        Container(
            TextDisplay(
               f"# {COMMAND_EMOJI} Command Browser\n"
                "-# Select a category to view commands.",
            ),
            ActionRow(_CategorySelect(interaction.client, commands, state)),
        ),
    )

    # ⸻ ...and then send it.

    view.message = await interaction.followup.send(view = view, ephemeral = True)
