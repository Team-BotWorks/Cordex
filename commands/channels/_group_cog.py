from typing import final

from discord import Thread
from discord.abc import GuildChannel
from discord.app_commands import (
    allowed_installs,
    command,
    describe,
    guild_only,
)
from discord.ext.commands import GroupCog

from bot import Cordex, Interaction

from .info import run_channel_info

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
        channel     : GuildChannel | Thread | None = None,
    ) -> None:
        await run_channel_info(interaction, channel)


async def setup(bot : Cordex) -> None:
    await bot.add_cog(ChannelCommands())
