from typing import Self, final

from discord import AllowedMentions, Guild, TextChannel
from discord.ext.commands import Cog

from bot import Cordex
from bot.ui import (
    Container,
    LayoutView,
    TextDisplay,
    Thumbnail,
    ThumbnailSection,
)
from constants import BOT_GUILD_LOG_CHANNEL_ID, COLOR_GREEN
from core.utilities import format_now, format_table

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Guild Join Logging
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
class GuildJoinLogging(Cog):
    """Logs when the bot is added to a guild."""

    def __init__(self, bot : Cordex) -> None:
        super().__init__()
        self.bot = bot

    @Cog.listener("on_guild_join")
    async def _listener_guild_guildjoin(self, guild : Guild) -> None:
        owner = guild.owner or await self.bot.fetch_user(guild.owner_id) if guild.owner_id else None
        if not owner:
            return

        info = format_table(
            {
                "Owner"          : f"{owner.mention} | {owner.id}",
                "Members"        : len(guild.members),
                "Current Guilds" : len(self.bot.guilds),
                "Current Users"  : len(self.bot.users),
            },
        )

        @final
        class JoinView(LayoutView):
            container = Container[Self](TextDisplay(f"# Joined Guild | {format_now("F")}"), color = COLOR_GREEN)

            if guild.icon:
                container.add_item(ThumbnailSection(info, thumbnail = Thumbnail[Self](guild.icon.url)))
            else:
                container.add_text(info)

        if not isinstance(
            log_channel := self.bot.get_channel(BOT_GUILD_LOG_CHANNEL_ID) or await self.bot.fetch_channel(BOT_GUILD_LOG_CHANNEL_ID),
            TextChannel,
        ):
            return

        await log_channel.send(
            view             = JoinView(),
            allowed_mentions = AllowedMentions.none(),
        )


async def setup(bot : Cordex) -> None:  # ruff: ignore[undocumented-public-function]
    await bot.add_cog(GuildJoinLogging(bot))
