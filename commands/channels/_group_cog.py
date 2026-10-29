from typing import final

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
from bot.types import GuildMessageable, GuildMessageableChannel
from core.state import requires_restriction
from core.utilities import unimplemented

from .compare import run_channel_compare
from .info import run_channel_info
from .permissions import run_channel_permissions

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Channel Group Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
@guild_only
@allowed_installs(guilds = True, users = False)
class ChannelCommands(
    GroupCog,
    name        = "channel",
    description = "Channel commands.",
):
    def __init__(self, bot : Cordex) -> None:
        super().__init__()
        self.bot = bot

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /channel compare Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @requires_restriction
    @command(
        name        = "compare",
        description = "List all differing permissions for two selected channels.",
    )
    @rename(
        channel_1 = "channel-1",
        channel_2 = "channel-2",
    )
    @describe(
        channel_1 = "The first channel to compare. Defaults to the current one.",
        channel_2 = "The second channel to compare. Defaults to the current one.",
    )
    async def cmd_channel_compare(
        self,
        interaction : Interaction,
        channel_1   : GuildMessageableChannel | None = None,
        channel_2   : GuildMessageableChannel | None = None,
    ) -> None:
        await run_channel_compare(interaction, channel_1, channel_2)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /channel info Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @command(
        name        = "info",
        description = "View information for a channel.",
    )
    @describe(channel = "The channel to view information for. Defaults to the current one.")
    async def cmd_channel_info(
        self,
        interaction : Interaction,
        channel     : GuildMessageable | None = None,
    ) -> None:
        await run_channel_info(interaction, channel)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /channel permissions Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @requires_restriction
    @command(
        name        = "permissions",
        description = "List permissions for a selected channel.",
    )
    @rename(permissions_filter = "filter")
    @describe(
        channel            = "The channel to list permissions for. Defaults to the current one.",
        permissions_filter = "Whether to show enabled or disabled permissions. Defaults to both.",
    )
    @choices(
        permissions_filter = [
            Choice(name = "Enabled",  value = "enabled"),
            Choice(name = "Disabled", value = "disabled"),
        ],
    )
    @unimplemented
    async def cmd_channel_permissions(
        self,
        interaction        : Interaction,
        channel            : GuildMessageableChannel | None = None,
        permissions_filter : str                     | None = None,
    ) -> None:
        await run_channel_permissions(interaction, channel, permissions_filter)


async def setup(bot : Cordex) -> None:
    cog = ChannelCommands(bot)
    await bot.add_cog(cog)
