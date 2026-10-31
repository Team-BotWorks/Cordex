# pyright: reportImportCycles = false

from collections.abc import Awaitable, Callable
from inspect import getattr_static, getsource
from io import BytesIO
from types import (
    CodeType,
    FrameType,
    FunctionType,
    MethodType,
    ModuleType,
    TracebackType,
)
from typing import TYPE_CHECKING, Self, TypedDict, Unpack, cast, final, override

from discord import AllowedMentions, Embed, File, Member, Message
from discord import Interaction as BaseInteraction
from discord.app_commands import CommandTree, ContextMenu
from discord.ext.commands import Context as BaseContext
from discord.ext.commands.view import StringView

from constants import DENIED_EMOJI
from core.state import (
    is_restrictable,
    is_restriction_required,
)

from .ui import Button, LayoutView, Modal, View, button

type _InspectableObject = (
    ModuleType
    | type
    | MethodType
    | FunctionType
    | TracebackType
    | FrameType
    | CodeType
)
type _Callback = Callable[[Interaction], Awaitable[None]]
type _Check = Callable[[object], bool]

if TYPE_CHECKING:
    from core.responses import FormatOverride, MessageType

    from .bot import Cordex

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Context & Interaction Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


class _ContextKwargs(TypedDict, total = False):
    message : Message
    bot     : Cordex
    view    : StringView


class Context(BaseContext["Cordex"]):
    def __init__(self, **kwargs : Unpack[_ContextKwargs]) -> None:
        super().__init__(**kwargs)

    async def format_send(
        self,
        msg_type     : MessageType,
        /,
        *,
        title        : str,
        subtitle     : str             | None = None,
        footer       : str             | None = None,
        reply        : bool                   = True,
        delete_after : float           | None = None,
        mentions     : AllowedMentions | None = None,
        override     : FormatOverride  | None = None,
    ) -> Message:
        from core.responses import format_message  # ruff: ignore[import-outside-top-level]

        content = format_message(
            msg_type,
            title    = title,
            subtitle = subtitle,
            footer   = footer,
            override = override,
        )

        if reply:
            if delete_after is not None:
                return await self.reply(
                    content          = content,
                    delete_after     = delete_after,
                    allowed_mentions = mentions or AllowedMentions.all(),
                )

            return await self.reply(
                content          = content,
                allowed_mentions = mentions or AllowedMentions.all(),
            )

        if delete_after is not None:
            return await self.send(
                content          = content,
                delete_after     = delete_after,
                allowed_mentions = mentions or AllowedMentions.all(),
            )

        return await self.send(
            content          = content,
            allowed_mentions = mentions or AllowedMentions.all(),
        )

    async def send_file(
        self,
        content      : str | None = None,
        /,
        *,
        file_content : str,
        file_name    : str,
    ) -> Message:
        return await self.send(content = content, file = File(BytesIO(file_content.encode()), filename = file_name))

    async def safe_send(self, content : str) -> Message:
        if len(content) < 2000:
            return await self.send(content)

        return await self.send_file(file_content = content, file_name = "content.txt")

    async def send_button(self, callback : _Callback, /) -> Message:
        @final
        class _ViewButton(View):
            def __init__(self, view_callback : _Callback, /) -> None:
                super().__init__(timeout = None)
                self.callback = view_callback

            @button(label = "Click me!")
            async def btn_basic(self, interaction : Interaction, _button : Button[Self]) -> None:
                try:
                    await self.callback(interaction)
                except Exception as e:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(
                           f"{DENIED_EMOJI} **Error! :[**\n"
                            "```py\n"
                           f"{e}\n"
                            "```",
                            ephemeral = True,
                        )
                    else:
                        await interaction.followup.send(
                           f"{DENIED_EMOJI} **Error! :[**\n"
                            "```py\n"
                           f"{e}\n"
                            "```",
                            ephemeral = True,
                        )

        return await self.send(view = _ViewButton(callback))

    async def send_embed(self, embed : Embed, /) -> Message:
        return await self.send(embed = embed)

    async def send_view(self, view : View | LayoutView, /) -> Message:
        return await self.send(view = view)

    async def send_modal(self, modal : Modal, /) -> Message:
        async def func(interaction : Interaction) -> None:
            await interaction.response.send_modal(modal)

        return await self.send_button(func)

    async def show_attrs(
        self,
        target   : object,
        check    : _Check | None = None,
        /,
        *,
        dunders  : bool          = False,
        privates : bool          = False,
    ) -> Message:
        def _filter(attribute : str) -> bool:
            if attribute.startswith("__") and attribute.endswith("__"):
                return dunders
            if attribute.startswith("_"):
                return privates
            return True

        if check is not None:
            attributes = [
                attribute for attribute in dir(target)
                if _filter(attribute) and
                check(cast("object", getattr_static(target, attribute)))
            ]
        else:
            attributes = [attribute for attribute in dir(target) if _filter(attribute)]

        output = (
            "```py\n"
           f"{",\n".join(attributes)}\n"
            "```"
        )

        if len(output) < 2000:
            return await self.send(output)

        module   = getattr(target, "__module__", "global").replace(".", "/")
        qualname = getattr(target, "__qualname__", "object")
        content  = f"```{module}/{qualname}```"
        filename = f"{module.split('/')[-1]}.py"
        return await self.send_file(content, file_content = ",\n".join(attributes), file_name = filename)

    async def show_def(self, target : _InspectableObject, /) -> Message:
        if isinstance(target, property):
            fget = target.fget
            if not fget:
                error = "Property has no getter method."
                raise TypeError(error)
            target = fget

        source = getsource(target)
        msg    = (
            "```py\n"
           f"{source}\n"
            "```"
        )

        if len(msg) < 2000:
            return await self.send(msg)

        module   = getattr(target, "__module__", "global").replace(".", "/")
        qualname = getattr(target, "__qualname__", "object")
        content  = f"```{module}/{qualname}```"
        filename = f"{module.split('/')[-1]}.py"
        return await self.send_file(content, file_content = source, file_name = filename)


class Tree(CommandTree):
    @override
    async def interaction_check(self, interaction : Interaction) -> bool:  # pyright: ignore[reportIncompatibleMethodOverride]
        command   = interaction.command
        client    = interaction.client
        blocklist = client.blocklist
        guild     = interaction.guild
        user      = interaction.user

        # ⸻ Blocklisting

        if not guild:
            if await blocklist.is_blocklisted(user):
                await interaction.response.send_message(
                   f"{DENIED_EMOJI} **Failed to run command!**\n"
                    "You have been blocklisted from using this bot and all of its features.\n"
                    "-# Bad request. Contact support if this was a mistake.",
                    ephemeral = True,
                )
                return False
            return True

        if await blocklist.is_blocklisted(guild):
            await interaction.response.send_message(
               f"{DENIED_EMOJI} **Failed to run command!**\n"
                "This guild has been blocklisted from using this bot and all of its features.\n"
                "-# Bad request. Contact support if this was a mistake.",
                ephemeral = True,
            )
            return False

        # ⸻ Restrictions

        if isinstance(command, ContextMenu | None):
            return True

        if not guild or not isinstance(user, Member):
            return True

        if not is_restrictable(command):
            return True

        if user == guild.owner:
            return True

        restriction = client.get_command_restriction(guild, command.qualified_name)
        if restriction is None:
            if is_restriction_required(command):
                await interaction.response.send_message(
                   f"{DENIED_EMOJI} **Failed to run command!**\n"
                    "This command requires restriction, but none have been configured.\n",
                    ephemeral = True,
                )
                return False
            return True

        if restriction.allows(user):
            return True

        await interaction.response.send_message(
           f"{DENIED_EMOJI} **Failed to run command!**\n"
            "You are not authorized to run this command.\n"
            "-# Bad request.",
            ephemeral = True,
        )
        return False


Interaction          = BaseInteraction["Cordex"]
ContextOrInteraction = Interaction | Context
