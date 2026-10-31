from bot import Context
from core.responses import FormatOverride, MessageType

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# .blocklist view Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


async def run_botowner_blocklist_view(ctx : Context) -> None:
    guild = ctx.guild
    if not guild:
        return

    paginator = await ctx.bot.blocklist.view()
    if not paginator:
        await ctx.format_send(
            MessageType.success,
            title    = "Nothing is blocklisted",
            override = FormatOverride(prefix = False),
        )
        return

    await ctx.send(view = paginator)
