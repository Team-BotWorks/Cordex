from typing import final

from discord import Role
from discord.app_commands import (
    Choice,
    allowed_installs,
    choices,
    command,
    describe,
    guild_only,
    rename,
)
from discord.ext.commands import GroupCog

from bot import Cordex, Interaction
from core.state import requires_restriction

from .compare import run_role_compare
from .info import run_role_info
from .members import PersonFilter, RoleFilter, run_role_members
from .permissions import PermissionsFilter, run_role_permissions

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Role Group Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
@guild_only
@allowed_installs(guilds = True, users = False)
class RoleCommands(
    GroupCog,
    name        = "role",
    description = "Role commands.",
):
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /role compare Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @requires_restriction
    @command(
        name        = "compare",
        description = "List all differing permissions for two selected roles.",
    )
    @rename(
        role_1 = "role-1",
        role_2 = "role-2",
    )
    @describe(
        role_1 = "The first role to compare.",
        role_2 = "The second role to compare.",
    )
    async def cmd_role_compare(
        self,
        interaction : Interaction,
        role_1      : Role,
        role_2      : Role,
    ) -> None:
        await run_role_compare(interaction, role_1, role_2)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /role info Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @command(
        name        = "info",
        description = "View information for a role.",
    )
    @describe(role = "The role to view information for.")
    async def cmd_role_info(
        self,
        interaction   : Interaction,
        role          : Role,
    ) -> None:
        await run_role_info(interaction, role)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /role members Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @command(
        name        = "members",
        description = "List members based on role possession and human/bot filtering.",
    )
    @describe(
        role          = "The role to view members or the lack thereof for.",
        role_filter   = "Whether to check who has or who doesn't have the role selected. Defaults to \"member of\".",
        person_filter = "Whether to show humans or bots. Defaults to both.",
    )
    @rename(
        role_filter   = "role-filter",
        person_filter = "person-filter",
    )
    @choices(
        role_filter = [
            Choice(name = "Member of",       value = "In"),
            Choice(name = "Not a Member of", value = "Not In"),
        ],
        person_filter = [
            Choice(name = "Humans", value = "Humans"),
            Choice(name = "Bots",   value = "Bots"),
        ],
    )
    async def cmd_role_members(
        self,
        interaction   : Interaction,
        role          : Role,
        role_filter   : RoleFilter   = "In",
        person_filter : PersonFilter = "Both",
    ) -> None:
        await run_role_members(interaction, role, role_filter, person_filter)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /role permissions Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @requires_restriction
    @command(
        name        = "permissions",
        description = "List permissions for a selected role.",
    )
    @rename(permissions_filter = "filter")
    @describe(
        role               = "The role to list permissions for.",
        permissions_filter = "Whether to show enabled or disabled permissions. Defaults to both.",
    )
    @choices(
        permissions_filter = [
            Choice(name = "Enabled",  value = "Enabled"),
            Choice(name = "Disabled", value = "Disabled"),
        ],
    )
    async def cmd_role_permissions(
        self,
        interaction        : Interaction,
        role               : Role,
        permissions_filter : PermissionsFilter = "Both",
    ) -> None:
        await run_role_permissions(interaction, role, permissions_filter)


async def setup(bot : Cordex) -> None:
    cog = RoleCommands()
    await bot.add_cog(cog)
