import asyncio
import typing
from collections.abc import Awaitable, Callable
from contextlib import redirect_stdout
from io import StringIO
from textwrap import indent
from traceback import format_exc
from typing import cast

import discord
from discord import app_commands
from discord.ext import commands as ext_commands
from discord.utils import format_dt, get, utcnow

import commands
import constants
import core
from bot import Context, ContextOrInteraction, Cordex, Interaction, ui
from bot.types import NOT_PASSED
from constants import (
    ACCEPTED_EMOJI,
    COLOR_BLACK,
    COLOR_BLUE,
    COLOR_GREEN,
    COLOR_GREY,
    COLOR_ORANGE,
    COLOR_RED,
    COLOR_WHITE,
    COLOR_YELLOW,
    DENIED_EMOJI,
    WARNING_EMOJI,
)
from core import exceptions
from core.paginator import NamedPaginator, PageData, UnnamedPaginator
from core.responses import (
    FormatOverride,
    MessageType,
    PunctuationOverride,
    format_message,
    format_send,
)
from core.utilities import (
    codeblock,
    format_command,
    format_now,
    format_table,
    format_values,
    truncate,
)

from .tools import format_dict

type Lambda = Callable[[], Awaitable[object]]

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# .eval Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


async def run_botowner_eval(ctx : Context, body : str) -> None:
    env : dict[str, object] = {
        "Cordex" : Cordex,

        "bot"  : ctx.bot,
        "ctx"  : ctx,
        "tree" : ctx.bot.tree,

        "guild"   : ctx.guild,
        "channel" : ctx.channel,
        "me"      : getattr(ctx.guild, "me", None),
        "author"  : ctx.author,
        "message" : ctx.message,

        "Context"              : Context,
        "Interaction"          : Interaction,
        "ContextOrInteraction" : ContextOrInteraction,

        "commands"    : commands,
        "constants"   : constants,
        "core"        : core,
        "exceptions"  : exceptions,
        "ui"          : ui,
        "asyncio"     : asyncio,
        "typing"      : typing,
        "extcommands" : ext_commands,
        "appcommands" : app_commands,
        "discord"     : discord,
        "dabc"        : discord.abc,
        "dutils"      : discord.utils,
        "dui"         : discord.ui,

        "ACCEPTED_EMOJI" : ACCEPTED_EMOJI,
        "WARNING_EMOJI"  : WARNING_EMOJI,
        "DENIED_EMOJI"   : DENIED_EMOJI,

        "COLOR_BLUE"    : COLOR_BLUE,
        "COLOR_GREEN"   : COLOR_GREEN,
        "COLOR_YELLOW"  : COLOR_YELLOW,
        "COLOR_ORANGE"  : COLOR_ORANGE,
        "COLOR_RED"     : COLOR_RED,
        "COLOR_GREY"    : COLOR_GREY,
        "COLOR_BLACK"   : COLOR_BLACK,
        "COLOR_WHITE"   : COLOR_WHITE,

        "utcnow"         : utcnow,
        "get"            : get,
        "codeblock"      : codeblock,
        "truncate"       : truncate,
        "format_dt"      : format_dt,
        "format_now"     : format_now,
        "format_command" : format_command,
        "format_values"  : format_values,
        "format_message" : format_message,
        "format_send"    : format_send,
        "format_table"   : format_table,
        "format_dict"    : format_dict,

        "select" : ui.select,
        "button" : ui.button,

        "Button"            : ui.Button,
        "Select"            : ui.Select,
        "UserSelect"        : ui.UserSelect,
        "RoleSelect"        : ui.RoleSelect,
        "MentionableSelect" : ui.MentionableSelect,
        "ChannelSelect"     : ui.ChannelSelect,
        "TextInput"         : ui.TextInput,

        "View"            : ui.View,
        "SimpleView"      : ui.SimpleView,
        "InteractiveView" : ui.InteractiveView,
        "Confirmation"    : ui.Confirmation,
        "Modal"           : ui.Modal,

        "Container"     : ui.Container,
        "Section"       : ui.Section,
        "Separator"     : ui.Separator,
        "ActionRow"     : ui.ActionRow,
        "TextDisplay"   : ui.TextDisplay,
        "Thumbnail"     : ui.Thumbnail,
        "MediaGallery"  : ui.MediaGallery,
        "File"          : ui.File,
        "FileUpload"    : ui.FileUpload,
        "Label"         : ui.Label,

        "ButtonSection"    : ui.ButtonSection,
        "ThumbnailSection" : ui.ThumbnailSection,
        "BSec"             : ui.ButtonSection,
        "TSec"             : ui.ThumbnailSection,

        "VisibleLargeSeparator" : ui.VisibleLargeSeparator,
        "VisibleSmallSeparator" : ui.VisibleSmallSeparator,
        "HiddenLargeSeparator"  : ui.HiddenLargeSeparator,
        "HiddenSmallSeparator"  : ui.HiddenSmallSeparator,
        "VLSep"                 : ui.VisibleLargeSeparator,
        "VSSep"                 : ui.VisibleSmallSeparator,
        "HLSep"                 : ui.HiddenLargeSeparator,
        "HSSep"                 : ui.HiddenSmallSeparator,

        "RadioGroup"    : ui.RadioGroup,
        "Checkbox"      : ui.Checkbox,
        "CheckboxGroup" : ui.CheckboxGroup,

        "SeparatorSpacing"    : discord.SeparatorSpacing,
        "MediaGalleryItem"    : discord.MediaGalleryItem,
        "SelectOption"        : discord.SelectOption,
        "ButtonStyle"         : discord.ButtonStyle,
        "TextStyle"           : discord.TextStyle,
        "RadioGroupOption"    : discord.RadioGroupOption,
        "CheckboxGroupOption" : discord.CheckboxGroupOption,
        "SelectDefaultValue"  : discord.SelectDefaultValue,

        "Embed" : discord.Embed,
        "Poll"  : discord.Poll,

        "AllowedMentions" : discord.AllowedMentions,

        "NamedPaginator"   : NamedPaginator,
        "UnnamedPaginator" : UnnamedPaginator,
        "PageData"         : PageData,

        "MessageType"         : MessageType,
        "FormatOverride"      : FormatOverride,
        "PunctuationOverride" : PunctuationOverride,

        "NOT_PASSED" : NOT_PASSED,
    }

    message = ctx.message
    channel = ctx.channel

    body       = "\n".join(body.split("\n")[1 : -1]) if body.startswith("```") else body.strip("` \n")
    stdout     = StringIO()
    to_compile = (
        f"async def func():\n"
        f"{indent(body, "  ")}"
    )

    try:
        exec(to_compile, env)  # ruff: ignore[exec-builtin]
    except Exception as e:
        await message.add_reaction(DENIED_EMOJI)
        async with channel.typing():
            await ctx.send(codeblock(f"{e.__class__.__name__}: {e}"), delete_after = 15)
        return

    func = cast("Lambda", env["func"])

    try:
        with redirect_stdout(stdout):
            ret = await func()
    except Exception:
        value = stdout.getvalue()
        await message.add_reaction(WARNING_EMOJI)
        async with channel.typing():
            await ctx.send(codeblock(f"{value}{format_exc()}"), delete_after = 15)
    else:
        value = stdout.getvalue()
        await message.add_reaction(ACCEPTED_EMOJI)

        if ret is None:
            if value:
                async with channel.typing():
                    await ctx.send(codeblock(value))
        else:
            async with channel.typing():
                await ctx.send(codeblock(f"{value}{ret}"))
