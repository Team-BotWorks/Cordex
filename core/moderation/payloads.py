from dataclasses import dataclass

from discord import Member, User

from bot.types import GuildMessageable, GuildMessageableChannel
from core.exceptions import DependentParameterError

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Moderation Action Payloads
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@dataclass
class _BaseRemovePayload:
    moderator : Member
    target    : Member
    reason    : str
    dm_user   : bool


@dataclass
class _BaseAddPayload:
    moderator : Member
    target    : Member
    reason    : str
    dm_user   : bool


@dataclass
class _BaseLockdownPayload:
    moderator : Member
    channel   : GuildMessageableChannel
    reason    : str


@dataclass
class LockdownAddPayload(_BaseLockdownPayload):
    """
    Represents a lockdown add action.

    Parameters
    ----------
    moderator : `Member`
        The moderator responsible for the lockdown add.
    channel : `GuildMessageableChannel`
        The target channel of the lockdown add.
    reason : `str`
        The reason for the lockdown add.
    """


@dataclass
class LockdownRemovePayload(_BaseLockdownPayload):
    """
    Represents a lockdown remove action.

    Parameters
    ----------
    moderator : `Member`
        The moderator responsible for the lockdown remove.
    channel : `GuildMessageableChannel`
        The target channel of the lockdown remove.
    reason : `str`
        The reason for the lockdown remove.
    """


@dataclass
class BanAddPayload(_BaseAddPayload):
    """
    Represents a ban add action.

    Parameters
    ----------
    moderator : `Member`
        The moderator responsible for the ban add.
    target : `Member`
        The target member of the ban add.
    reason : `str`
        The reason for the ban add.
    dm_user : `bool`
        Whether the user will be direct messaged.
    seconds_to_delete : `int`
        The duration in seconds of messages to delete.
    """

    seconds_to_delete : int


@dataclass
class BanRemovePayload:
    """
    Represents a ban remove action.

    Parameters
    ----------
    moderator : `Member`
        The moderator responsible for the ban remove.
    target : `User`
        The target member of the ban remove.
    reason : `str`
        The reason for the ban remove.
    dm_user : `bool`
        Whether the user will be direct messaged.
    """

    moderator : Member
    target    : User
    reason    : str
    dm_user   : bool


@dataclass
class KickPayload(_BaseAddPayload):
    """
    Represents a kick action.

    Parameters
    ----------
    moderator : `Member`
        The moderator responsible for the kick.
    target : `Member`
        The target member of the kick.
    reason : `str`
        The reason for the kick.
    dm_user : `bool`
        Whether the user will be direct messaged.
    """


@dataclass
class TimeoutAddPayload(_BaseAddPayload):
    """
    Represents a timeout add action.

    Parameters
    ----------
    moderator : `Member`
        The moderator responsible for the timeout add.
    target : `Member`
        The target member of the timeout add.
    reason : `str`
        The reason for the timeout add.
    dm_user : `bool`
        Whether the user will be direct messaged.
    length : `int`
        The duration of the timeout in seconds.
    """

    length : int


@dataclass
class TimeoutRemovePayload(_BaseRemovePayload):
    """
    Represents a timeout remove action.

    Parameters
    ----------
    moderator : `Member`
        The moderator responsible for the timeout remove.
    target : `Member`
        The target member of the timeout remove.
    reason : `str`
        The reason for the timeout remove.
    dm_user : `bool`
        Whether the user will be direct messaged.
    """


@dataclass
class QuarantineAddPayload(_BaseAddPayload):
    """
    Represents a quarantine add action.

    Parameters
    ----------
    moderator : `Member`
        The moderator responsible for the quarantine add.
    target : `Member`
        The target member of the quarantine add.
    reason : `str`
        The reason for the quarantine add.
    dm_user : `bool`
        Whether the user will be direct messaged.
    """


@dataclass
class QuarantineRemovePayload(_BaseRemovePayload):
    """
    Represents a quarantine remove action.

    Parameters
    ----------
    moderator : `Member`
        The moderator responsible for the quarantine remove.
    target : `Member`
        The target member of the quarantine remove.
    reason : `str`
        The reason for the quarantine remove.
    dm_user : `bool`
        Whether the user will be direct messaged.
    """


@dataclass
class PurgePayload:
    """
    Represents a purge action.

    Parameters
    ----------
    moderator : `Member`
        The moderator responsible for the purge.
    target : `Member | None`
        The optional target member whose messages will be purged.
    reason : `str`
        The reason for the purge.
    channel : `GuildMessageable`
        The target channel of the purge.
    amount : `int`
        The amount of messages to purge.
    force : `bool`
        Whether the purge will be forced.
        - True: Deletes `amount` messages by the `target` found in the last 1000 messages in the channel.
        - False: Searches `channel` for `amount` messages and deletes any by the `target` (or deletes `amount` messages in the `channel` if no `target`)

        Dependent on the `target` parameter.
    """

    moderator : Member
    target    : Member | None
    reason    : str
    channel   : GuildMessageable
    amount    : int
    force     : bool

    def __post_init__(self) -> None:
        """
        Validate that `target` is passed if `force` is passed.

        Raises
        ------
        DependentParameterError
            `force` was passed without `target`.
        """
        if self.force and not self.target:
            parameter_1 = "force"
            parameter_2 = "target"
            raise DependentParameterError(parameter_1, parameter_2)


Payloads = (
    LockdownAddPayload
    | LockdownRemovePayload
    | BanAddPayload
    | BanRemovePayload
    | KickPayload
    | QuarantineAddPayload
    | QuarantineRemovePayload
    | TimeoutAddPayload
    | TimeoutRemovePayload
    | PurgePayload
)
