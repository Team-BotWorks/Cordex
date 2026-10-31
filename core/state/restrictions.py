from dataclasses import dataclass
from typing import overload

from discord import Member
from discord.app_commands import Command, Group
from discord.ext.commands import Cog, GroupCog

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Restriction State
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Restriction Dataclass
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@dataclass(frozen = True, slots = True)
class Restriction:
    """
    Represents a command restriction.

    Parameters
    ----------
    user_ids : `frozenset[int]`
        The IDs of the users allowed to use the command.
    role_ids : `frozenset[int]`
        The IDs of the roles allowed to use the command.
    """

    user_ids : frozenset[int]
    role_ids : frozenset[int]

    def allows(self, member : Member) -> bool:
        """
        Check if a member is allowed to use a command.

        Parameters
        ----------
        member : `Member`
            The member to check.

        Returns
        -------
        `bool`
            Whether the member is allowed to use the command or not.
        """
        if member.id in self.user_ids:
            return True

        return any(role.id in self.role_ids for role in member.roles)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Unrestrictable
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@overload
def unrestrictable[GroupT : Group | Cog, **P, T](target : Command[GroupT, P, T], /) -> Command[GroupT, P, T]: ...

@overload
def unrestrictable[CogT : type[GroupCog]](target : CogT, /) -> CogT: ...


def unrestrictable[
    GroupT : Group | Cog,
    CogT   : type[GroupCog],
    **P,
    T,
](target : Command[GroupT, P, T] | CogT, /) -> Command[GroupT, P, T] | CogT:
    """
    Mark a command or group of commands as unrestrictable.

    Parameters
    ----------
    target : `Command[GroupT, P, T] | GroupCog`
        The command or group of commands to mark as unrestrictable.
    /

    Returns
    -------
    `target : Command[GroupT, P, T] -> Command[GroupT, P, T]`
        The command marked as unrestrictable.
    `target : type[GroupCog] -> CogT`
        The cog with its group of commands marked as unrestrictable.
    """
    if not isinstance(target, Command):
        setattr(target, "__unrestrictable__", True)  # ruff: ignore[set-attr-with-constant]
        return target

    target.extras["unrestrictable"] = True
    return target


def is_restrictable[GroupT : Group | Cog, **P, T](command : Command[GroupT, P, T] | Group, /) -> bool:
    """
    Check if a command is restrictable.

    Parameters
    ----------
    command : `Command[GroupT, P, T] | Group`
        The command to check.
    /

    Returns
    -------
    `bool`
        Whether the command is restrictable or not.
    """
    if isinstance(command, Group):
        return False

    return command.extras.get("unrestrictable", False) is False

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Requires Restriction
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@overload
def requires_restriction[GroupT : Group | Cog, **P, T](target : Command[GroupT, P, T], /) -> Command[GroupT, P, T]: ...

@overload
def requires_restriction[CogT : type[GroupCog]](target : CogT, /) -> CogT: ...


def requires_restriction[
    GroupT : Group | Cog,
    CogT   : type[GroupCog],
    **P,
    T,
](target : Command[GroupT, P, T] | CogT, /) -> Command[GroupT, P, T] | CogT:
    """
    Mark a command or group of commands as requiring restriction.

    Parameters
    ----------
    target : `Command[GroupT, P, T] | GroupCog`
        The command or group of commands to mark as requiring restriction.
    /

    Returns
    -------
    `target : Command[GroupT, P, T] -> Command[GroupT, P, T]`
        The command marked as requiring restriction.
    `target : type[GroupCog] -> CogT`
        The cog with its group of commands marked as requiring restriction.
    """
    if not isinstance(target, Command):
        setattr(target, "__requires_restriction__", True)  # ruff: ignore[set-attr-with-constant]
        return target

    target.extras["requires_restriction"] = True
    return target


def is_restriction_required[GroupT : Group | Cog, **P, T](command : Command[GroupT, P, T] | Group, /) -> bool:
    """
    Check if a command requires restriction.

    Parameters
    ----------
    command : `Command[GroupT, P, T] | Group`
        The command to check.
    /

    Returns
    -------
    `bool`
        Whether the command requires restriction or not.
    """
    if isinstance(command, Group):
        return False

    return command.extras.get("requires_restriction", False) is True
