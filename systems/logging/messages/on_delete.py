from io import BytesIO
from typing import Self, final

from discord import AllowedMentions, Message
from discord import File as DiscordFile
from discord.ext.commands import Cog

from bot import Cordex
from bot.types import GuildMessageable
from bot.ui import Container, File, LayoutView, TextDisplay, VisibleLargeSeparator
from constants import COLOR_RED
from core.utilities import format_now, format_table, is_bot_owner

from ._base import attachments_display, channel_display, clean_and_truncate

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Message Delete Logging
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
class MessageDeleteLogging(Cog):
    """Logs message deletion for guilds with it enabled."""

    def __init__(self, bot : Cordex) -> None:
        super().__init__()
        self.bot = bot

    @Cog.listener("on_message_delete")
    async def _listener_delete_messagedelete(self, message : Message) -> None:
        content     = message.content
        attachments = message.attachments
        author      = message.author
        channel     = message.channel
        guild       = message.guild

        # ⸻ Block bots and the bot itself.

        if author.bot or author == self.bot.user:
            return

        # ⸻ Block non-guild messages.

        if not guild or not isinstance(channel, GuildMessageable):
            return

        # ⸻ Block messages that do not belong to the current guild context.

        log_channel = await self.bot.config(guild).get_messages_delete_logging_channel()
        if log_channel is None or not log_channel.permissions_for(guild.me).send_messages:
            return

        # ⸻ Block evaluations.

        if content.startswith(".eval") and is_bot_owner(author):
            return

        @final
        class DeleteView(LayoutView):
            container = Container[Self](
                TextDisplay(f"# Message Deleted | {format_now("F")}"),
                TextDisplay(
                    format_table(
                        {
                            "Author"  : f"{author.mention} | {author.id}",
                            "Channel" : channel_display(channel),
                        },
                    ),
                ),
                color = COLOR_RED,
            )

            if attachments:
                container.add_items(
                    VisibleLargeSeparator(),
                    TextDisplay(
                        "### Attachments\n"
                       f"{attachments_display(attachments)}",
                    ),
                )

            container.add_items(
                VisibleLargeSeparator(),
                TextDisplay(
                    "### Content\n"
                   f"{clean_and_truncate(content or "[No content, likely an embed or attachment]")}",
                ),
            )

            if len(clean_and_truncate(content)) > 1500:
                container.add_item(File(DiscordFile(BytesIO(content.encode(encoding = "utf-8")), filename = "deleted.txt")))

        await log_channel.send(
            view             = DeleteView(),
            allowed_mentions = AllowedMentions.none(),
        )


async def setup(bot : Cordex) -> None:  # ruff: ignore[undocumented-public-function]
    cog = MessageDeleteLogging(bot)
    await bot.add_cog(cog)
