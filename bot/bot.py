# pyright: reportImportCycles = false

from asyncio import to_thread
from importlib import import_module
from logging import getLogger as get_logger
from pathlib import Path
from pkgutil import walk_packages
from typing import TYPE_CHECKING, NotRequired, TypedDict, cast, final, override

from aiosqlite import Row
from discord import Color, Guild, Intents, Message, Status, User
from discord import Interaction as BaseInteraction
from discord.app_commands import AppCommand as APICommand
from discord.ext.commands import Bot, Cog, when_mentioned_or
from discord.ext.commands import Context as BaseContext
from discord.http import Route

from constants import (
    COLOR_BLACK,
    COLOR_WHITE,
    DEVELOPER_IDS,
    DisplayNameEffect,
    DisplayNameFont,
)
from core.state import (
    Config,
    Connection,
    Restriction,
    connect,
)

from .context import Context, Tree
from .types import NOT_PASSED, DisplayNameStyle

if TYPE_CHECKING:
    from core.state import BlocklistManager

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Bot & Client Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

PACKAGE_NAMES = ["commands", "core", "systems"]

log = get_logger("Cordex")

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
            tree_cls                = Tree,
        )
        self.version = "0.9.0"

        self.db : Connection

        self.blocklist : BlocklistManager

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

    def config(self, guild : Guild, /) -> Config:
        """
        Get the configuration for a guild.

        Parameters
        ----------
        guild : `Guild`
            The guild to get the configuration for.
        /

        Returns
        -------
        `Config`
            The configuration for this guild.
        """
        return Config(self, guild)

    async def delete_configs(self, *guild_ids : int) -> None:
        """
        Delete configurations for guilds.

        Parameters
        ----------
        *guild_ids : `int`
            The IDs of the guilds to delete the configuration for.
        /
        """
        await self.db.execute(t"DELETE FROM Config WHERE guild_id IN {guild_ids}")
        await self.db.commit()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Biography
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def get_bio(self, guild : Guild, /) -> str:
        """
        Get the bot's biography for this guild.

        Returns
        -------
        `str`
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
        return await super().get_context(origin, cls = cls or Context)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # setup_hook
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @override
    async def setup_hook(self) -> None:
        if self.user:
            log.info("Logging in as %s, %s", self.user.name, self.user.id)

        self.developers = [user for developer_id in DEVELOPER_IDS if (user := await self.fetch_user(developer_id))]

        from core.state import BlocklistManager  # ruff: ignore[import-outside-top-level]
        self.blocklist = BlocklistManager(self)

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

        seen : set[str] = set()

        for package_name in PACKAGE_NAMES:
            try:
                package = import_module(package_name)
            except Exception:
                log.exception("Failed to import package %s", package_name)
                continue

            modules_to_check = [package_name] + [info.name for info in walk_packages(package.__path__, f"{package.__name__}.")]

            for name in modules_to_check:
                if name in seen or name.endswith("._base"):
                    continue

                try:
                    module = import_module(name)
                except Exception:
                    log.exception("Failed to import module %s", name)
                    continue

                if callable(getattr(module, "setup", None)):
                    seen.add(name)

        cogs = sorted(seen)

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
