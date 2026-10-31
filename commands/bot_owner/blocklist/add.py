from bot import Context, log
from core.exceptions import send_bad_argument
from core.responses import MessageType, format_send

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# .blocklist add Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


async def run_botowner_blocklist_add(ctx : Context, target_id : int) -> None:
    manager = ctx.bot.blocklist

    target = await manager.resolve(target_id)
    if not target:
        await send_bad_argument(ctx, subtitle = "Target could not be resolved.")
        return

    if await manager.is_blocklisted(target):
        await send_bad_argument(ctx, subtitle = "Target is already blocklisted.")
        return

    try:
        await manager.add(target)
    except Exception:
        log.exception("An exception occured during the blocklist addition")
    else:
        await format_send(ctx, MessageType.success, title = f"blocklisted {target_id}")
