from asyncio import AbstractEventLoop, get_running_loop
from secrets import randbelow
from sys import exc_info
from traceback import format_exception
from typing import final, override

from discord import AllowedMentions, Guild, Member, TextChannel, User
from discord import Interaction as BaseInteraction
from discord.app_commands import (
    AppCommandError,
    BotMissingPermissions,
    CommandOnCooldown,
)
from discord.ext.commands import Cog, MissingRequiredArgument
from discord.ext.commands import CommandError as PrefixCommandError
from discord.ext.commands import CommandNotFound as PrefixCommandNotFound

from bot import Context, ContextOrInteraction, Cordex, Interaction
from bot.ui import Container, LayoutView, TextDisplay, VisibleLargeSeparator
from constants import (
    BOT_ERRORS_LOG_CHANNEL_ID,
    BOTWORKS_MENTION,
    COLOR_RED,
)
from core.exceptions import (
    BadEnvironmentDMsOnly,
    BadEnvironmentGuildOnly,
    BadPermissionsCommand,
    BadPermissionsPrefixCommand,
    UnconfiguredQuarantine,
    UnimplementedCommand,
    send_bad_argument,
    send_bad_environment_dmsonly,
    send_bad_environment_guildonly,
    send_bad_operation,
    send_bad_permissions_command,
    send_unimplemented_command,
)
from core.responses import FormatOverride, MessageType, PunctuationOverride, format_send
from core.utilities import codeblock, format_command, format_now, format_table

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Errors Logging
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
class ErrorLogger(Cog):
    """Logs when Cordex errors."""

    def __init__(self, bot : Cordex) -> None:
        super().__init__()
        self.bot = bot
        self.bot.tree.error(self._command_error_handler)

    @override
    async def cog_load(self) -> None:
        loop = get_running_loop()
        loop.set_exception_handler(self._loop_exception_handler)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Central Error Sender
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def _send_error(
        self,
        *,
        title     : str,
        user      : User | Member        | None = None,
        guild     : Guild                | None = None,
        context   : ContextOrInteraction | None = None,
        error     : str                  | None = None,
        traceback : str                  | None = None,
    ) -> None:
        if not isinstance(
            channel := self.bot.get_channel(BOT_ERRORS_LOG_CHANNEL_ID) or await self.bot.fetch_channel(BOT_ERRORS_LOG_CHANNEL_ID),
            TextChannel,
        ):
            return

        view = LayoutView()

        container = Container[view](
            TextDisplay(
                f"# {title}\n"
                f"{BOTWORKS_MENTION}, an unexpected exception has occurred.",
            ),
            color = COLOR_RED,
        )

        if traceback:
            container.add_item(
                TextDisplay(
                    f"## Traceback\n"
                    f"{codeblock(traceback[:2000])}",
                ),
            )

        if user:
            table = format_table(
                {
                    "User"     : user.mention,
                    "Username" : user.name,
                    "User ID"  : user.id,
                },
            )

            container.add_items(
                VisibleLargeSeparator(),
                TextDisplay(
                    "## User\n"
                   f"{table}",
                ),
            )

        if guild:
            table = format_table(
                {
                    "Guild Name" : guild.name,
                    "Guild ID"   : guild.id,
                },
            )

            container.add_items(
                VisibleLargeSeparator(),
                TextDisplay(
                    "## Guild\n"
                   f"{table}",
                ),
            )

        if context:
            if isinstance(context, BaseInteraction):
                interaction = context
                if command := interaction.command:
                    qualified_name = command.qualified_name
                    command_id     = interaction.command_id

                    table = format_table(
                        {
                            "Command"      : format_command(qualified_name),
                            "Command Name" : f"/{qualified_name}",
                            "Command ID"   : command_id,
                        },
                    )

                    container.add_items(
                        VisibleLargeSeparator(),
                        TextDisplay(
                            "## Command\n"
                           f"{table}",
                        ),
                    )
            if isinstance(context, Context):
                ctx = context
                if command := ctx.command:
                    table = format_table({"Command" : command.qualified_name})

                    container.add_items(
                        VisibleLargeSeparator(),
                        TextDisplay(
                            "## Command\n"
                           f"{table}",
                        ),
                    )

        if error:
            container.add_items(
                VisibleLargeSeparator(),
                TextDisplay(
                    "## Error\n"
                   f"{codeblock(error)}",
                ),
            )

        container.add_items(
            VisibleLargeSeparator(),
            TextDisplay(f"{format_now()} | {format_now("R")}"),
        )

        view.add_item(container)

        await channel.send(
            view             = view,
            allowed_mentions = AllowedMentions(users = False, roles = True),
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Discord Event Errors
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @Cog.listener("on_error")
    async def _error_handler(
        self,
        event     : str,
        *_args    : str,
        **_kwargs : int,
    ) -> None:
        exception_type, exception, traceback = exc_info()

        if exception is None:
            await self._send_error(
                title  =  "Bot Event Error",
                error  = f"{event}: Unknown exception",
            )
            return

        traceback = "".join(format_exception(exception_type, exception, traceback))

        await self._send_error(
            title     =  "Bot Event Error",
            error     = f"{event}: {exception}",
            traceback = traceback,
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Command Errors
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def _command_error_handler(
        self,
        interaction : Interaction,
        error       : AppCommandError,
    ) -> None:
        if isinstance(error, BadPermissionsCommand):
            if randbelow(10) == 0:
                await format_send(
                    interaction,
                    MessageType.error,
                    title     = "I'm sorry, Dave,",
                    subtitle  = "I'm afraid I can't do that",
                    footer    = "You are not authorized to run this command — Bad request",
                    override  = FormatOverride(prefix = False),
                    ephemeral = False,
                )
            else:
                await send_bad_permissions_command(interaction)
            return

        if isinstance(error, CommandOnCooldown):
            await format_send(
                interaction,
                MessageType.error,
                title    =  "run command",
                subtitle = f"This command is on cooldown. Retry in {error.retry_after:2f}s",
                footer   =  "Too many requests",
            )

        if isinstance(error, BadEnvironmentGuildOnly):
            await send_bad_environment_guildonly(interaction)
            return

        if isinstance(error, BadEnvironmentDMsOnly):
            await send_bad_environment_dmsonly(interaction)
            return

        if isinstance(error, UnimplementedCommand):
            await send_unimplemented_command(interaction)
            return

        if isinstance(error, UnconfiguredQuarantine):
            return

        if isinstance(error, BotMissingPermissions):
            if len(missing_permissions := error.missing_permissions) > 1:
                s     = "s"
                count = "several"
            else:
                s     = ""
                count = "a"

            await format_send(
                interaction,
                MessageType.error,
                title    = "run command",
                subtitle = (
                    f"This command requires {count} permission{s} to run that I lack:\n"
                    f"{"\n".join(f"`{permission.replace("_", " ").title()}`" for permission in missing_permissions)}"
                ),
                override = FormatOverride(punctuation = PunctuationOverride(subtitle = False)),
            )
            return

        await send_bad_operation(interaction)

        traceback = "".join(format_exception(type(error), error, error.__traceback__))

        await self._send_error(
            title     = "Command Error",
            user      = interaction.user,
            guild     = interaction.guild,
            context   = interaction,
            error     = str(error),
            traceback = traceback,
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Prefix Command Errors
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @Cog.listener("on_command_error")
    async def _prefix_command_error_handler(self, ctx : Context, error : PrefixCommandError) -> None:
        if isinstance(error, PrefixCommandNotFound):
            return

        if isinstance(error, MissingRequiredArgument):
            await send_bad_argument(ctx, subtitle = {error.param.name : "This is a required argument that was omitted."})
            return

        if isinstance(error, BadPermissionsPrefixCommand):
            return

        await send_bad_operation(ctx)

        traceback = "".join(format_exception(type(error), error, error.__traceback__))

        await self._send_error(
            title     = "Prefix Command Error",
            user      = ctx.author,
            guild     = ctx.guild,
            error     = str(error),
            traceback = traceback,
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Loop Exception Errors
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    def _loop_exception_handler(
        self,
        loop    : AbstractEventLoop,
        context : dict[str, object],
    ) -> None:
        if loop.is_closed():
            return

        exception   = context.get("exception")
        message     = context.get("message")
        message_str = str(message) or "No message"

        traceback = "".join(
            format_exception(
                type(exception),
                exception,
                exception.__traceback__,
            ),
        ) if isinstance(exception, BaseException) else message_str

        loop.create_task(
            self._send_error(
                title     = "Asyncio Event Loop Error",
                error     = message_str,
                traceback = traceback,
            ),
        )


async def setup(bot : Cordex) -> None:  # ruff: ignore[undocumented-public-function]
    cog = ErrorLogger(bot)
    await bot.add_cog(cog)
