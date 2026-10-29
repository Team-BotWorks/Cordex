from io import BytesIO
from typing import Self, final

from discord import AllowedMentions, ButtonStyle, Message
from discord import File as DiscordFile
from discord.ext.commands import Cog
from discord.utils import format_dt, utcnow

from bot import Cordex
from bot.types import GuildMessageable
from bot.ui import (
    Button,
    ButtonSection,
    Container,
    File,
    LayoutView,
    TextDisplay,
    VisibleLargeSeparator,
)
from constants import COLOR_GREY
from core.utilities import format_table, is_bot_owner

from ._base import attachments_display, channel_display, clean_and_truncate

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Message Edit Logging
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
class MessageEditLogging(Cog):
    """Logs message editing for guilds with it enabled."""

    def __init__(self, bot : Cordex) -> None:
        super().__init__()
        self.bot = bot

    @Cog.listener("on_message_edit")
    async def _listener_delete_messageedit(self, before : Message, after : Message) -> None:
        author  = before.author
        guild   = before.guild
        channel = before.channel

        before_content = before.content

        after_content     = after.content
        after_attachments = after.attachments

        # ⸻ Block bots and the bot itself.

        if author.bot or author == self.bot.user:
            return

        # ⸻ Block non-guild messages.

        if not guild or not isinstance(channel, GuildMessageable):
            return

        # ⸻ Block messages that do not belong to the current guild context.

        log_channel = await self.bot.config(guild).get_messages_edit_logging_channel()
        if not log_channel or not log_channel.permissions_for(guild.me).send_messages:
            return

        # ⸻ Block evaluations.

        if (
            before_content.startswith(".eval") or
            after_content.startswith(".eval")
        ) and is_bot_owner(author):
            return

        # ⸻ Edit message logging.

        before_files = [attachment.url for attachment in before.attachments]
        after_files  = [attachment.url for attachment in after.attachments]

        if before_content == after_content and before_files == after_files:
            return

        @final
        class EditView(LayoutView):
            container = Container[Self](
                TextDisplay(f"# Message Edited | {format_dt(after.edited_at or utcnow(), style = "F")}"),
                ButtonSection(
                    format_table(
                        {
                            "Author"  : f"{author.mention} | {author.id}",
                            "Channel" : channel_display(channel),
                        },
                    ),
                    button = Button(label = "Jump to Message", style = ButtonStyle.link, url = after.jump_url),
                ),
                color = COLOR_GREY,
            )

            if after_attachments:
                container.add_items(
                    VisibleLargeSeparator(),
                    TextDisplay(
                        "### Attachments\n"
                       f"{attachments_display(after_attachments)}",
                    ),
                )

            container.add_item(VisibleLargeSeparator())
            container.add_text(
                "### Before\n"
               f"{clean_and_truncate(before_content) or "[No content, likely an embed or attachment]"}",
            )

            if len(clean_and_truncate(before_content)) > 1500:
                container.add_item(File(DiscordFile(BytesIO(before_content.encode(encoding = "utf-8")), filename = "before.txt")))

            container.add_text(
                "### After\n"
               f"{clean_and_truncate(after_content) or "[No content, likely an embed or attachment]"}",
            )

            if len(clean_and_truncate(after_content)) > 1500:
                container.add_item(File(DiscordFile(BytesIO(after_content.encode(encoding = "utf-8")), filename = "after.txt")))

        await log_channel.send(
            view             = EditView(),
            allowed_mentions = AllowedMentions.none(),
        )


async def setup(bot : Cordex) -> None:  # ruff: ignore[undocumented-public-function]
    cog = MessageEditLogging(bot)
    await bot.add_cog(cog)
