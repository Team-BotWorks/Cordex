from collections.abc import Callable
from operator import eq, ge, gt, le, lt
from typing import Literal

from discord import Member, Role

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Moderation Utilities Base
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# hierarchy
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


def hierarchy(
    actor      : Member,
    comparison : Literal[">", "<", "==", ">=", "<="],
    target     : Member,
    /,
) -> bool:
    # ⸻ Actor vs Themselves

    if actor == target:
        return comparison in {"==", ">=", "<="}

    # ⸻ Actor is Owner

    if actor == actor.guild.owner:
        return comparison in {">", ">="}

    # ⸻ Target is Owner

    if target == target.guild.owner:
        return comparison in {"<", "<="}

    operators : dict[str, Callable[[Role, Role], bool]] = {
        ">"  : gt,
        "<"  : lt,
        "="  : eq,
        ">=" : ge,
        "<=" : le,
    }

    return operators[comparison](actor.top_role, target.top_role)
