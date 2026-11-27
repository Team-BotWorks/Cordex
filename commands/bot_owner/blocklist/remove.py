from discord import AllowedMentions, HTTPException

from bot import Context, log
from core.exceptions import send_bad_argument
from core.responses import MessageType
from core.state import Block

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# .blocklist remove Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


async def run_botowner_blocklist_remove(ctx : Context, target_id : int) -> None:
    manager = ctx.bot.blocklist

    try:
        target_type = await manager.remove(target_id)
    except Exception:
        log.exception("An exception occurred during the blocklist removal")
        raise

    if not target_type:
        await send_bad_argument(ctx, subtitle = f"`{target_id}` is not blocklisted.")
        return

    try:
        target = await manager.resolve(target_id, target_type)
    except HTTPException:
        target = None

    entry = Block(target_id, target_type, target)
    await ctx.format_send(
        MessageType.success,
        title    = f"unblocklisted {entry.summary}",
        mentions = AllowedMentions.none(),
    )
