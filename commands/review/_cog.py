from typing import final

from discord.ext.commands import Cog
from discord.ext.commands import command as prefix_command

from bot import Context, Cordex

from .review import ReviewFlags, run_review

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Review Command
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
class ReviewCommand(Cog):
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .review Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @prefix_command(name = "review")
    async def cmd_review(self, ctx : Context, *, flags : ReviewFlags) -> None:
        await run_review(ctx, flags = flags)


async def setup(bot : Cordex) -> None:
    await bot.add_cog(ReviewCommand(bot))
