from asyncio import gather, sleep
from re import compile as regex_compile
from typing import Self, final

from discord import AllowedMentions, Forbidden, MediaGalleryItem, Message
from discord.abc import Messageable
from discord.ext.commands import Cog

from bot import Cordex
from bot.ui import (
    Container,
    File,
    MediaGallery,
    TextDisplay,
    View,
    VisibleLargeSeparator,
)

MESSAGE_LINK_PATTERN = regex_compile(r"https://discord(?:app)?\.com/channels/(\d+|@me)/(\d+)/(\d+)")

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Preview Handling
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
class _PreviewView(View):
    def __init__(self, message : Message, link : str, names : list[str]) -> None:
        super().__init__()
        container = Container[Self](TextDisplay(f"{message.author.mention}: {link}"), VisibleLargeSeparator())

        if message.content:
            container.add_text(message.content)

        if message.attachments:
            if gallery_items := [
                MediaGalleryItem(attachment.url)
                for attachment in message.attachments
                if attachment.content_type
                and attachment.content_type.startswith(("image/", "video/"))
            ]:
                container.add_item(MediaGallery(*gallery_items))

            if file_items := [File[Self](f"attachment://{name}") for name in names]:
                container.append_items(file_items)

        self.add_item(container)


@final
class Preview(Cog):
    """Provides message previews for Discord message links."""

    def __init__(self, bot : Cordex) -> None:
        super().__init__()
        self.bot = bot

    async def _process_message_preview(self, message : Message) -> None:
        content = message.content
        author  = message.author
        guild   = message.guild

        if author.bot:
            return

        if guild:
            wants_preview = await self.bot.config(guild).get_whether_messages_preview()
            if not wants_preview:
                return

        for i, match in enumerate(MESSAGE_LINK_PATTERN.finditer(content)):
            channel_id = int(match.group(2))
            message_id = int(match.group(3))

            if not isinstance(
                target_channel := self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id),
                Messageable,
            ):
                continue

            try:
                target_message = await target_channel.fetch_message(message_id)
            except Forbidden:
                continue
            else:
                if not target_message.content and not target_message.attachments:  # ⸻ Message has no content or attachments. Perhaps an embed?
                    continue

            files = await gather(
                *(
                    attachment.to_file() for attachment in [
                        attachment for attachment in target_message.attachments
                        if attachment.content_type and
                        not attachment.content_type.startswith(("image/", "video/"))
                    ]
                ),
            )
            view  = _PreviewView(
                target_message,
                match.group(0),
                [file.filename for file in files],
            )
            if i == 0:
                async with message.channel.typing():
                    await sleep(0.5)
                    await message.reply(files = files, view = view, allowed_mentions = AllowedMentions.none())
            else:
                await message.reply(files = files, view = view, allowed_mentions = AllowedMentions.none())

    @Cog.listener("on_message")
    async def _listener_preview_message(self, message : Message) -> None:
        await self._process_message_preview(message)

    @Cog.listener("on_message_edit")
    async def _listener_preview_messageedit(self, _before : Message, after : Message) -> None:
        await self._process_message_preview(after)


async def setup(bot : Cordex) -> None:  # ruff: ignore[undocumented-public-function]
    await bot.add_cog(Preview(bot))
