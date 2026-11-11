from typing import Self, final

from discord import AllowedMentions, Role

from bot import Interaction
from bot.ui import Container, TextDisplay, View, VisibleLargeSeparator
from constants import COLOR_GREY
from core.exceptions import send_bad_argument

from ._base import format_permission

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /role compare Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


async def run_role_compare(
    interaction : Interaction,
    role_1      : Role,
    role_2      : Role,
) -> None:
    """
    List all differing permissions for two selected roles.

    Parameters
    ----------
    interaction : `Interaction`
        The interaction context to run the command with.
    role_1 : `Role`
        The first role to compare.
    role_2 : `Role`
        The second role to compare.
    """
    await interaction.response.defer()

    if role_1 == role_2:
        await send_bad_argument(interaction, subtitle = {("role-1", "role-2") : "You cannot compare a role with itself."})
        return

    diffs_role_1 : list[str] = []
    diffs_role_2 : list[str] = []

    for (perm_name, value1), (_, value2) in zip(role_1.permissions, role_2.permissions, strict = False):
        if value1 != value2:
            diffs_role_1.append(format_permission(perm_name, value = value1))
            diffs_role_2.append(format_permission(perm_name, value = value2))

    # ⸻ Build the view.

    @final
    class CompareView(View):
        if not diffs_role_1:
            container = Container[Self](
                TextDisplay(f"### Permission Differences for {role_1.mention} and {role_2.mention}"),
                VisibleLargeSeparator(),
                TextDisplay("Roles have identical permissions."),
                color = COLOR_GREY,
            )
        else:
            container = Container[Self](
                TextDisplay(f"### Permission Differences for {role_1.mention} and {role_2.mention}"),
                VisibleLargeSeparator(),
                TextDisplay(
                    f"{role_1.mention}\n"
                    f"{("No permissions." if role_1.permissions.value == 0 else "\n".join(diffs_role_1))}",
                ),
                VisibleLargeSeparator(),
                TextDisplay(
                    f"{role_2.mention}\n"
                    f"{("No permissions." if role_2.permissions.value == 0 else "\n".join(diffs_role_2))}",
                ),
                color = COLOR_GREY,
            )

    await interaction.followup.send(
        view             = CompareView(),
        allowed_mentions = AllowedMentions.none(),
    )
