from bot import Context, log
from core.exceptions import send_bad_argument
from core.responses import MessageType

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# .blocklist remove Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


async def run_botowner_blocklist_remove(ctx : Context, target_id : int) -> None:
    manager = ctx.bot.blocklist

    target = await manager.resolve(target_id)
    if not target:
        await send_bad_argument(ctx, subtitle = "Target could not be resolved.")
        return

    if not await manager.is_blocklisted(target):
        await send_bad_argument(ctx, subtitle = "Target is not blocklisted.")
        return

    try:
        await manager.remove(target)
    except Exception:
        log.exception("An exception occured during the blocklist removal")
    else:
        await ctx.format_send(MessageType.success, title = f"unblocklisted {target_id}")
