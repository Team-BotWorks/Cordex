from discord import AllowedMentions, User

from bot import Context, log
from core.exceptions import send_bad_argument
from core.responses import MessageType
from core.state import Block
from core.utilities import is_bot_owner

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# .blocklist add Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


async def run_botowner_blocklist_add(ctx : Context, target_id : int) -> None:
    manager = ctx.bot.blocklist

    target = await manager.resolve(target_id)
    if not target:
        await send_bad_argument(
            ctx,
            subtitle = "Target could not be resolved. If you are trying to blocklisted a guild, guilds can only be blocklisted while the bot is in them.",
        )
        return

    if isinstance(target, User):
        if target.bot:
            them = "me" if target == ctx.bot.user else "bots"
            await send_bad_argument(ctx, subtitle = f"You cannot blocklist {them}.")
            return

        if is_bot_owner(target):
            them = "yourself" if target == ctx.author else "bot owners"
            await send_bad_argument(ctx, subtitle = f"You cannot blocklist {them}.")
            return

    entry = Block.from_target(target)

    try:
        added = await manager.add(target)
    except Exception:
        log.exception("An exception occurred during the blocklist addition")
        raise

    if not added:
        await send_bad_argument(ctx, subtitle = f"The {entry.summary} is already blocklisted.")
        return

    await ctx.format_send(
        MessageType.success,
        title    = f"blocklisted {entry.summary}",
        mentions = AllowedMentions.none(),
    )
