# pyright: reportImportCycles = false

from asyncio import to_thread
from collections.abc import Awaitable, Callable
from inspect import getattr_static, getsource
from io import BytesIO
from logging import getLogger as get_logger
from pathlib import Path
from types import (
    CodeType,
    FrameType,
    FunctionType,
    MethodType,
    ModuleType,
    TracebackType,
)
from typing import NotRequired, Self, TypedDict, Unpack, cast, final, override

from aiosqlite import Row
from discord import Color, Embed, File, Guild, Intents, Member, Message, Status, User
from discord import Interaction as BaseInteraction
from discord.app_commands import AppCommand as APICommand
from discord.app_commands import CommandTree, ContextMenu
from discord.ext.commands import Bot, Cog, when_mentioned_or
from discord.ext.commands import Context as BaseContext
from discord.ext.commands.view import StringView
from discord.http import Route

from constants import (
    COLOR_BLACK,
    COLOR_WHITE,
    DENIED_EMOJI,
    DEVELOPER_IDS,
    DisplayNameEffect,
    DisplayNameFont,
)
from core.cog_loader import discover_cogs
from core.state import (
    Config,
    Connection,
    Restriction,
    connect,
    is_restrictable,
    is_restriction_required,
)

from .types import NOT_PASSED, DisplayNameStyle
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

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Bot & Client Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

log = get_logger("Cordex")

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Context and Interaction Classes
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


class _ContextKwargs(TypedDict, total = False):
    message : Message
    bot     : Cordex
    view    : StringView


class _ContextClass(BaseContext["Cordex"]):
    def __init__(self, **kwargs : Unpack[_ContextKwargs]) -> None:
        super().__init__(**kwargs)

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

    type Check = Callable[[object], bool]

    async def show_attrs(
        self,
        target   : object,
        check    : Check | None = None,
        /,
        *,
        tall     : bool  | None = None,
        dunders  : bool         = False,
        privates : bool         = False,
    ) -> Message:
        def _filter(attr : str) -> bool:
            if attr.startswith("__") and attr.endswith("__"):
                return dunders
            if attr.startswith("_"):
                return privates
            return True

        if check is not None:
            attrs = [
                attr for attr in dir(target)
                if _filter(attr) and
                check(cast("object", getattr_static(target, attr)))
            ]
        else:
            attrs = [attr for attr in dir(target) if _filter(attr)]

        if tall is None:
            estimated_length = sum(len(a) for a in attrs) + (2 * (len(attrs) - 1))
            tall = estimated_length > 80

        joiner = ",\n" if tall else ", "

        output = (
            "```py\n"
           f"{joiner.join(attrs)}\n"
            "```"
        )

        if len(output) < 2000:
            return await self.send(output)

        module   = getattr(target, "__module__", "global").replace(".", "/")
        qualname = getattr(target, "__qualname__", "object")
        content  = f"```{module}/{qualname}```"
        filename = f"{module.split('/')[-1]}.py"
        return await self.send_file(content, file_content = joiner.join(attrs), file_name = filename)

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


class _Tree(CommandTree):
    @override
    async def interaction_check(self, interaction : Interaction) -> bool:  # pyright: ignore[reportIncompatibleMethodOverride]
        command = interaction.command
        client  = interaction.client
        guild   = interaction.guild
        user    = interaction.user

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


Context              = _ContextClass
Interaction          = BaseInteraction["Cordex"]
ContextOrInteraction = Interaction | Context

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Cordex Class
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
class Cordex(Bot):
    """The main bot class."""

    def __init__(self) -> None:
        super().__init__(
            chunk_guilds_at_startup = True,
            case_insensitive        = True,
            command_prefix          = when_mentioned_or("."),
            help_command            = None,
            intents                 = Intents.all(),
            status                  = Status.online,
            tree_cls                = _Tree,
        )
        self.version = "0.9.0"

        self.db : Connection

        self._api_commands_cache         : list[APICommand]                   = []
        self._command_restrictions_cache : dict[tuple[int, str], Restriction] = {}

        self.restarting : bool = False

        self.developers : list[User] = []

    @override
    async def add_cog(self, cog : Cog, /) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        await super().add_cog(cog)

        if getattr(cog.__class__, "__requires_restriction__", False):
            for command in cog.walk_app_commands():
                command.extras["requires_restriction"] = True

        if getattr(cog.__class__, "__unrestrictable__", False):
            for command in cog.walk_app_commands():
                command.extras["unrestrictable"] = True

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Configuration
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    def config(self, guild : Guild) -> Config:
        """
        Get the configuration for a guild.

        Parameters
        ----------
        guild : `Guild`
            The guild to get the configuration for.

        Returns
        -------
        `Config`
            The configuration for this guild.
        """
        return Config(self, guild)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Biography
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def get_bio(self, guild : Guild, /) -> str:
        """
        Get the bot's biography for this guild.

        Returns
        -------
        str
            The biography for this guild.
        """
        return cast(
            "TypedDict[{'bio' : str}]",
            await self.http.request(
                route = Route("PATCH", "/guilds/{guild_id}/members/@me", guild_id = guild.id),
                json  = {},
            ),
        )["bio"]

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Name Styles
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def set_name_style(
        self,
        guild  : Guild,
        /,
        *,
        font   : DisplayNameFont   | NOT_PASSED = NOT_PASSED,
        effect : DisplayNameEffect | NOT_PASSED = NOT_PASSED,
        colors : list[Color]       | NOT_PASSED = NOT_PASSED,
    ) -> None:
        """
        Set the bot's display name style for this guild.

        Parameters
        ----------
        guild : `Guild`
            The guild to set the display name style in.
        /
        *
        font : `DisplayNameFont`
            The font to use in the display name style.
        effect : `DisplayNameEffect`
            The effect to use in the display name style.
        colors : `list[Color]`
            The colors to use in the display name style. The gradient, prism, and gummy effects take up to five colors; all else take specifically one.

        Raises
        ------
        ValueError
            - No colors were passed.
            - Too many colors were passed.
        """
        multi_colored = {
            DisplayNameEffect.gradient,
            DisplayNameEffect.prism,
            DisplayNameEffect.gummy,
        }

        current = await self.get_name_style(guild)
        if font is NOT_PASSED:
            font = current.font
        if effect is NOT_PASSED:
            effect = current.effect
        if colors is NOT_PASSED:
            colors = current.colors

        if len(colors) == 0 and effect not in multi_colored:
            error = "0 colors were passed; expected 1"
            raise ValueError(error)

        if len(colors) == 0 and effect in multi_colored:
            error = "0 colors were passed; expected 1 to 5"
            raise ValueError(error)

        if len(colors) > 1 and effect not in multi_colored:
            error = f"{len(colors)} colors were passed; expected 1"
            raise ValueError(error)

        if len(colors) > 5 and effect in multi_colored:
            error = f"{len(colors)} colors were passed; expected 1 to 5"
            raise ValueError(error)

        color_integers = [color.value for color in colors]

        await self.http.request(
            route = Route("PATCH", "/guilds/{guild_id}/members/@me", guild_id = guild.id),
            json  = {
                "display_name_font_id"   : font.value,
                "display_name_effect_id" : effect.value,
                "display_name_colors"    : color_integers,
            },
        )

    async def get_name_style(self, guild : Guild, /) -> DisplayNameStyle:
        """
        Get the bot's display name style for this guild.

        Parameters
        ----------
        guild : `Guild`
            The guild to get the display name style in.
        /

        Returns
        -------
        `DisplayNameStyle`
            The result of the display name style call. Has `font`, `effect`, and `colors` attributes for accessing.

        Raises
        ------
        RuntimeError
            The bot user is `None` (it is impossible for this to be raised).
        """
        if self.user is None:
            raise RuntimeError

        response = cast(
            "TypedDict[{'display_name_styles' : NotRequired[TypedDict[{'font_id' : int, 'effect_id' : int, 'colors' : list[int]}] | None]}]",
            await self.http.request(
                route = Route(
                    "GET", "/guilds/{guild_id}/members/{user_id}",
                    guild_id = guild.id,
                    user_id  = self.user.id,
                ),
            ),
        )

        styles = response.get("display_name_styles")

        if styles is None:
            return DisplayNameStyle(
                font   = DisplayNameFont(11),
                effect = DisplayNameEffect(1),
                colors = [COLOR_WHITE],
            )

        return DisplayNameStyle(
            font   = DisplayNameFont(styles["font_id"]),
            effect = DisplayNameEffect(styles["effect_id"]),
            colors = [Color(color) for color in styles["colors"]],
        )

    async def reset_name_style(self, guild : Guild, /, *, branded : bool = True) -> None:
        """
        Reset the bot's display name style for this guild.

        Parameters
        ----------
        guild : `Guild`
            The guild to reset the display name style in.
        /
        *
        branded : `bool = True`
            Whether to reset the display name style using the branded types: `zilla_slab` font, `gradient` effect, `["FFFFFF", "000000"]` colors
        """
        await self.set_name_style(
            guild,
            font   = DisplayNameFont.zilla_slab if branded else DisplayNameFont.default,
            effect = DisplayNameEffect.gradient if branded else DisplayNameEffect.solid,
            colors = [COLOR_WHITE, COLOR_BLACK] if branded else [COLOR_WHITE],
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Custom Context
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @override
    async def get_context[ContextT : BaseContext[Cordex]](
        self,
        origin : Message        | BaseInteraction,
        *,
        cls    : type[ContextT] | None = None,
    ) -> ContextT | Context:
        return await super().get_context(origin, cls = cls or _ContextClass)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # setup_hook
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @override
    async def setup_hook(self) -> None:
        if self.user:
            log.info("Logging in as %s, %s", self.user.name, self.user.id)

        self.developers = [user for developer_id in DEVELOPER_IDS if (user := await self.fetch_user(developer_id))]

        # ⸻ AIOSQLite

        db_path = Path("data/database.db")
        db_path.parent.mkdir(parents = True, exist_ok = True)

        self.db = await connect(str(db_path))
        self.db.row_factory = Row

        def read_schemas() -> list[str]:
            return [schema.read_text(encoding = "utf-8") for schema in Path("schemas").glob("*.sql")]

        for schema in await to_thread(read_schemas):
            await self.db.executescript(schema)

        await self.db.commit()

        # ⸻ Cogs

        cogs = await to_thread(
            discover_cogs,
            "commands",
            "systems",
            "core",
        )

        for cog in cogs:
            try:
                await self.load_extension(cog)
                log.info("Loaded cog %s", cog)
            except Exception:
                log.exception("Failed to load cog %s", cog)

        # ⸻ Cache

        await self._build_api_commands_cache()
        await self._build_command_restrictions_cache()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Commands Cache
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def _build_api_commands_cache(self) -> None:
        self._api_commands_cache = await self.tree.fetch_commands()

    def get_api_commands_cache(self) -> list[APICommand]:
        """
        Get all Discord-side app commands found in the cache.

        Returns
        -------
        `list[APICommand]`
            All Discord-side app commands found in the cache.
        """
        return self._api_commands_cache

    async def rebuild_api_commands_cache(self) -> None:
        """Rebuild the Discord-side app commands cache."""
        self._api_commands_cache.clear()
        await self._build_api_commands_cache()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Command Restrictions Cache
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def _build_command_restrictions_cache(self) -> None:
        grouped : dict[tuple[int, str], tuple[set[int], set[int]]] = {}

        async with self.db.execute(
            t"SELECT guild_id, command_name, target_type, target_id FROM CommandRestrictions",
        ) as cursor:
            rows = await cursor.fetchall()

        for row in rows:
            guild_id     = cast("int", row[0])
            command_name = cast("str", row[1])
            target_type  = cast("str", row[2])
            target_id    = cast("int", row[3])

            users, roles = grouped.setdefault((guild_id, command_name), (set(), set()))

            if target_type == "role":
                roles.add(target_id)
            else:
                users.add(target_id)

        self._command_restrictions_cache = {
            key : Restriction(frozenset(users), frozenset(roles))
            for key, (users, roles) in grouped.items()
        }

    def get_command_restriction(self, guild : Guild, command_name : str, /) -> Restriction | None:
        """
        Get the restrictions for a command.

        Parameters
        ----------
        guild : `Guild`
            The guild to get the restrictions for.
        command_name : `str`
            The name of the command to get the restrictions for.
        /

        Returns
        -------
        `Restriction | None`
            The restrictions for the command. Possibly `None` if the command is not restricted or the command was not found.
        """
        return self._command_restrictions_cache.get((guild.id, command_name))

    def set_command_restriction(self, guild : Guild, command_name : str, restriction : Restriction | None, /) -> None:
        """
        Set the restrictions for a command.

        Parameters
        ----------
        guild : `Guild`
            The guild to set the restrictions for.
        command_name : `str`
            The name of the command to set the restrictions for.
        /
        """
        key = (guild.id, command_name)

        if restriction is None:
            self._command_restrictions_cache.pop(key, None)
        else:
            self._command_restrictions_cache[key] = restriction

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # close
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @override
    async def close(self) -> None:
        if self.db:
            await self.db.close()

        await super().close()


cordex = Cordex()
