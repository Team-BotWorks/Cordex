from typing import final

from discord import Member
from discord.app_commands import (
    Choice,
    allowed_installs,
    choices,
    command,
    describe,
    guild_only,
)
from discord.ext.commands import GroupCog

from bot import Cordex, Interaction

from ._base import Scope
from .avatar import run_member_avatar
from .banner import run_member_banner
from .info import run_member_info

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Member Group Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
@guild_only
@allowed_installs(guilds = True, users = False)
class MemberCommands(
    GroupCog,
    name        = "member",
    description = "Member commands.",
):
    def __init__(self) -> None:
        super().__init__()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /member avatar Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @command(
        name        = "avatar",
        description = "View the avatar of a member.",
    )
    @describe(
        member = "The member to view the avatar for. Defaults to yourself.",
        scope  = 'Whether to view the guild avatar or the global avatar of the member. Defaults to "global".',
    )
    @choices(
        scope = [
            Choice(
                name  = "Guild",
                value = "guild",
            ),
            Choice(
                name  = "Global",
                value = "global",
            ),
        ],
    )
    async def cmd_member_avatar(
        self,
        interaction : Interaction,
        member      : Member | None = None,
        *,
        scope       : Scope  | None = "global",
    ) -> None:
        await run_member_avatar(interaction, member, scope)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /member banner Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @command(
        name        = "banner",
        description = "View the banner of a member.",
    )
    @describe(
        member = "The member to view the banner for. Defaults to yourself.",
        scope  = 'Whether to view the guild banner or the global banner of the member. Defaults to "global".',
    )
    @choices(
        scope = [
            Choice(
                name  = "Guild",
                value = "guild",
            ),
            Choice(
                name  = "Global",
                value = "global",
            ),
        ],
    )
    async def cmd_member_member(
        self,
        interaction : Interaction,
        member      : Member | None = None,
        *,
        scope       : Scope  | None = "global",
    ) -> None:
        await run_member_banner(interaction, member, scope)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /member info Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @command(
        name        = "info",
        description = "View information for a member.",
    )
    @describe(
        member = "The member to view information for. Defaults to yourself.",
        scope  = 'Whether to view the guild profile or the global profile of the member. Defaults to "global".',
    )
    @choices(
        scope = [
            Choice(
                name  = "Guild",
                value = "guild",
            ),
            Choice(
                name  = "Global",
                value = "global",
            ),
        ],
    )
    async def cmd_member_info(
        self,
        interaction : Interaction,
        member      : Member | None = None,
        *,
        scope       : Scope  | None = "global",
    ) -> None:
        await run_member_info(interaction, member, scope)


async def setup(bot : Cordex) -> None:
    cog = MemberCommands()
    await bot.add_cog(cog)
