from collections.abc import Awaitable, Callable
from typing import final, override

from discord import Member, User
from discord.app_commands import (
    AppCommandError,
    Choice,
    Group,
    Range,
    allowed_installs,
    check,
    choices,
    command,
    describe,
    guild_only,
    rename,
)
from discord.app_commands.checks import bot_has_permissions
from discord.ext.commands import GroupCog

from bot import Cordex, Interaction
from bot.types import GuildMessageable
from core.exceptions import (
    BadEnvironmentGuildOnly,
    UnconfiguredQuarantine,
    send_bad_operation,
)
from core.moderation import ActionType, CasesManager
from core.state import requires_restriction

from .ban import (
    run_moderation_ban_add,
    run_moderation_ban_remove,
    run_moderation_ban_view,
)
from .cases import run_moderation_cases_query, run_moderation_cases_view
from .kick import run_moderation_kick
from .lockdown import (
    run_moderation_lockdown_add,
    run_moderation_lockdown_remove,
    run_moderation_lockdown_view,
)
from .purge import run_moderation_purge
from .quarantine import (
    run_moderation_quarantine_add,
    run_moderation_quarantine_remove,
    run_moderation_quarantine_view,
)
from .timeout import (
    run_moderation_timeout_add,
    run_moderation_timeout_remove,
    run_moderation_timeout_view,
)


def quarantine_cmd[F : Callable[..., Awaitable[None]]](func : F) -> F:
    async def predicate(interaction : Interaction) -> bool:
        guild = interaction.guild
        if not guild:
            raise BadEnvironmentGuildOnly

        quarantine_role = await interaction.client.config(guild).get_moderation_quarantine_role()
        if not quarantine_role:
            raise UnconfiguredQuarantine

        return True

    return check(predicate)(func)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Moderation Group Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
@guild_only
@requires_restriction
@allowed_installs(guilds = True, users = False)
class ModerationCommands(
    GroupCog,
    name        = "moderation",
    description = "Moderation commands.",
):
    def __init__(self, bot : Cordex) -> None:
        super().__init__()
        self.bot = bot

    ban        : Group = Group(
        name        = "ban",
        description = "Moderation ban commands",
    )
    lockdown   : Group = Group(
        name        = "lockdown",
        description = "Moderation lockdown commands",
    )
    quarantine : Group = Group(
        name        = "quarantine",
        description = "Moderation quarantine commands",
    )
    timeout    : Group = Group(
        name        = "timeout",
        description = "Moderation timeout commands",
    )
    cases      : Group = Group(
        name        = "cases",
        description = "Moderation case commands",
    )

    @override
    async def cog_app_command_error(self, interaction : Interaction, error : AppCommandError) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        if isinstance(error, UnconfiguredQuarantine):
            await send_bad_operation(
                interaction,
                subtitle = "This server has not configured a quarantine role, so quarantine operations cannot be performed",
            )
            return

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation lockdown add Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @lockdown.command(
        name        = "add",
        description = "Add a channel to lockdown.",
    )
    @bot_has_permissions(manage_channels = True)
    async def cmd_moderation_lockdown_add(self, interaction : Interaction) -> None:
        await run_moderation_lockdown_add(interaction)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation lockdown view Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @lockdown.command(
        name        = "view",
        description = "View all lockdowned channels.",
    )
    async def cmd_moderation_lockdown_view(self, interaction : Interaction) -> None:
        await run_moderation_lockdown_view(interaction)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation lockdown remove Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @lockdown.command(
        name        = "remove",
        description = "Remove a channel from lockdown.",
    )
    @bot_has_permissions(manage_channels = True)
    async def cmd_moderation_lockdown_remove(self, interaction : Interaction) -> None:
        await run_moderation_lockdown_remove(interaction)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation ban add Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @ban.command(
        name        = "add",
        description = "Ban a member from the server.",
    )
    @bot_has_permissions(ban_members = True)
    @describe(target = "The member to ban.")
    async def cmd_moderation_ban_add(self, interaction : Interaction, target : Member) -> None:
        await run_moderation_ban_add(interaction, target)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation ban view Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @ban.command(
        name        = "view",
        description = "View all banned members.",
    )
    @bot_has_permissions(ban_members = True)
    async def cmd_moderation_ban_view(self, interaction : Interaction) -> None:
        await run_moderation_ban_view(interaction)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation ban remove Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @ban.command(
        name        = "remove",
        description = "Remove a ban from a member.",
    )
    @bot_has_permissions(ban_members = True)
    @describe(target = "The member to unban.")
    async def cmd_moderation_ban_remove(self, interaction : Interaction, target : User) -> None:
        await run_moderation_ban_remove(interaction, target)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation kick Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @command(
        name        = "kick",
        description = "Kick a member from the server.",
    )
    @bot_has_permissions(kick_members = True)
    @describe(target = "The member to kick.")
    async def cmd_moderation_kick(self, interaction : Interaction, target : Member) -> None:
        await run_moderation_kick(interaction, target)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation quarantine add Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @quarantine.command(
        name        = "add",
        description = "Add a member to quarantine.",
    )
    @bot_has_permissions(manage_roles = True)
    @describe(target = "The member to place in quarantine.")
    @quarantine_cmd
    async def cmd_moderation_quarantine_add(self, interaction : Interaction, target : Member) -> None:
        await run_moderation_quarantine_add(interaction, target)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation quarantine view Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @quarantine.command(
        name        = "view",
        description = "View all quarantined members.",
    )
    @quarantine_cmd
    async def cmd_moderation_quarantine_view(self, interaction : Interaction) -> None:
        await run_moderation_quarantine_view(interaction)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation quarantine remove Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @quarantine.command(
        name        = "remove",
        description = "Remove a member from quarantine.",
    )
    @bot_has_permissions(manage_roles = True)
    @describe(target = "The member to remove from quarantine.")
    @quarantine_cmd
    async def cmd_moderation_quarantine_remove(self, interaction : Interaction, target : Member) -> None:
        await run_moderation_quarantine_remove(interaction, target)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation timeout add Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @timeout.command(
        name        = "add",
        description = "Add a member to timeout.",
    )
    @bot_has_permissions(moderate_members = True)
    @describe(target = "The member to place in timeout.")
    async def cmd_moderation_timeout_add(self, interaction : Interaction, target : Member) -> None:
        await run_moderation_timeout_add(interaction, target)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation timeout view Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @timeout.command(
        name        = "view",
        description = "View all timed out members.",
    )
    async def cmd_moderation_timeout_view(self, interaction : Interaction) -> None:
        await run_moderation_timeout_view(interaction)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation timeout remove Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @timeout.command(
        name        = "remove",
        description = "Remove a member from timeout.",
    )
    @bot_has_permissions(moderate_members = True)
    @describe(target = "The member to remove from timeout.")
    async def cmd_moderation_timeout_remove(self, interaction : Interaction, target : Member) -> None:
        await run_moderation_timeout_remove(interaction, target)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation purge Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @command(
        name        = "purge",
        description = "Purge messages from a channel or member.",
    )
    @bot_has_permissions(manage_messages = True, read_message_history = True)
    @describe(target = "The member to purge messages from.")
    async def cmd_moderation_purge(self, interaction : Interaction, target : Member | None = None) -> None:
        await run_moderation_purge(interaction, target)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation cases query Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @cases.command(
        name        = "query",
        description = "Query moderation cases with various filters.",
    )
    @choices(
        action_type = [
            Choice(name = action_type.readable(), value = action_type.value)
            for action_type in ActionType
        ],
    )
    @describe(
        action_type = "Filter by action type.",
        moderator   = "Filter by moderator.",
        target      = "Filter by user.",
        channel     = "Filter by channel.",
        expired     = "Filter by expiration.",
        before      = 'Filter cases that occurred before a date of the form "MM/DD/YYYY", "MM/DD/YY", or "MM/DD".',
        after       = 'Filter cases that occurred after a date of the form "MM/DD/YYYY", "MM/DD/YY", or "MM/DD".',
    )
    @rename(action_type = "action-type")
    async def cmd_moderation_cases_query(
        self,
        interaction : Interaction,
        *,
        action_type : str               | None = None,
        moderator   : Member            | None = None,
        target      : User              | None = None,
        channel     : GuildMessageable  | None = None,
        expired     : bool              | None = None,
        before      : Range[str, 3, 10] | None = None,
        after       : Range[str, 3, 10] | None = None,
    ) -> None:
        await run_moderation_cases_query(
            interaction,
            action_type = action_type,
            moderator   = moderator,
            target      = target,
            channel     = channel,
            expired     = expired,
            before      = before,
            after       = after,
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation cases view Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @cases.command(
        name        = "view",
        description = "View a moderation case.",
    )
    @describe(case = "The case to view. Defaults to all cases.")
    async def cmd_moderation_cases_view(self, interaction : Interaction, case : int | None = None) -> None:
        await run_moderation_cases_view(interaction, case)

    @cmd_moderation_cases_view.autocomplete("case")
    async def autocomplete_cmdmoderationcasesview(self, interaction : Interaction, current : str) -> list[Choice[int]]:
        guild = interaction.guild
        if not guild:
            return []

        return [
            Choice(name = f"#{case.id} | {case.action_type.readable()}", value = case.id)
            for case in await CasesManager(interaction.client, guild).get_all_cases()
            if current.lower() in f"#{case.id} | {case.action_type.readable()}".lower()
        ][:25]


async def setup(bot : Cordex) -> None:
    cog = ModerationCommands(bot)
    await bot.add_cog(cog)
