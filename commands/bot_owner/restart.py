from asyncio import sleep
from os import execv
from sys import argv, executable, stderr, stdout

from discord import CustomActivity, DiscordException, Status

from bot import Context, log
from constants import COG_EMOJI
from core.exceptions import send_bad_operation
from core.responses import MessageType
from core.utilities import codeblock

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# .restart Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


async def run_botowner_restart(ctx : Context) -> None:
    bot = ctx.bot

    if bot.restarting:
        await send_bad_operation(
            ctx,
            title    = "restart bot",
            subtitle = "A restart is already in progress",
        )
        return

    bot.restarting = True

    await ctx.send(
       f"{COG_EMOJI} **Restarting bot.**\n"
        "Restarting bot...",
    )

    log.info("Attempting a restart.")

    try:
        await bot.change_presence(
            status   = Status.idle,
            activity = CustomActivity(name = "Restarting..."),
        )
        await sleep(1)
    except Exception:
        log.info("Couldn't set presence while restarting. Continuing...")

    try:
        for handler in log.handlers:
            if hasattr(handler, "flush"):
                handler.flush()

        stdout.flush()
        stderr.flush()
    except Exception:
        log.exception("Couldn't flush logs. Continuing...")

    try:
        await bot.close()
    except Exception:
        log.exception("Received fatal error during restart.")

    try:
        execv(  # ruff: ignore[start-process-with-no-shell]
            executable,
            [executable, *argv[1:]],
        )

    except (OSError, DiscordException) as e:
        log.exception("Received fatal error during restart")
        bot.restarting = False

        if not bot.is_closed():
            await ctx.format_send(
                MessageType.error,
                title    = "restart bot",
                subtitle = codeblock(e),
            )
            await bot.change_presence(status = Status.online)
