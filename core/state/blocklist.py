from asyncio import gather as async_gather
from dataclasses import dataclass
from operator import itemgetter
from typing import TYPE_CHECKING, Literal, Self, cast, final, overload

from discord import Forbidden, Guild, Member, NotFound, User
from discord.utils import escape_markdown, escape_mentions

from constants import COLOR_BLACK

if TYPE_CHECKING:
    from bot import Cordex
    from core.paginator import UnnamedPaginator

type Blocklistable = User | Member | Guild
type TargetType    = Literal["user", "guild"]


@final
@dataclass(frozen = True, slots = True)
class Block:
    """
    A single blocklisted target.

    Parameters
    ----------
    target_id : `int`
        The ID of the blocklisted target.
    target_type : `Literal["user", "guild"]`
        Whether the target is a user or a guild.
    target : `User | Guild | None = None`
        The resolved target, or `None` if it could not be resolved (e.g. the bot has left the guild).
    """

    target_id   : int
    target_type : TargetType
    target      : User | Guild | None = None

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # from_target
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @classmethod
    def from_target(cls, target : User | Guild, /) -> Self:
        """
        Build an entry from an already resolved target.

        Parameters
        ----------
        target : `User | Guild`
            The resolved target.
        /

        Returns
        -------
        `BlocklistEntry`
            The entry describing the target.
        """
        return cls(target.id, "guild" if isinstance(target, Guild) else "user", target)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # label
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @property
    def label(self) -> str:
        """A markdown and mention safe display name for the target."""
        if self.target is None:
            return f"Unknown {self.target_type.title()}"

        name = self.target.name if isinstance(self.target, Guild) else f"@{self.target.name}"
        return escape_mentions(escape_markdown(name))

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # summary
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @property
    def summary(self) -> str:
        """A description of the target including its type, name, and ID."""
        return f"{self.target_type} {self.label} ({self.target_id})"

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Blocklist State
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
class BlocklistManager:
    """
    A manager for blocklisting.

    Parameters
    ----------
    bot : `Cordex`
        The bot instance.
    """

    def __init__(self, bot : Cordex) -> None:
        self.bot = bot

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # get
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @overload
    async def get(self, *, by_id : Literal[True]) -> set[tuple[type[User | Guild], int]]: ...

    @overload
    async def get(self, *, by_id : Literal[False] = False) -> set[User | Guild]: ...

    async def get(self, *, by_id : bool = False) -> set[User | Guild] | set[tuple[type[User | Guild], int]]:
        """
        Fetch every blocklisted user/guild found in the database.

        Parameters
        ----------
        *
        by_id : `bool = False`
            Whether to return the types and IDs of the targets over actual user/guild objects or not. This is useful in cases when testing for membership, and it also includes targets that can no longer be resolved.

        Returns
        -------
        `by_id = False -> set[User | Guild]`
            Every blocklisted user/guild found in the database that could still be resolved. Targets such as guilds the bot has left are omitted.
        `by_id = True -> set[tuple[type[User | Guild], int]]`
            Tuples of the type and ID of every blocklisted user/guild found in the database.
        """
        async with self.bot.db.execute(t"SELECT target_id, target_type FROM Blocklists") as cursor:
            rows = await cursor.fetchall()

        if by_id:
            return {
                (User if row[1] == "user" else Guild, cast("int", row[0]))
                for row in rows
            }

        return {
            target for row in rows
            if (target := await self.resolve(cast("int", row[0]), "guild" if row[1] == "guild" else "user"))
        }

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # resolve
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def resolve(self, target_id : int, target_type : TargetType | None = None, /) -> User | Guild | None:
        """
        Resolve an ID into a complete user/guild object.

        Parameters
        ----------
        target_id : `int`
            The ID of the target to resolve.
        target_type : `Literal["user", "guild"] | None = None`
            The known type of the target. Passing it skips lookups that cannot succeed, which saves API calls.
        /

        Returns
        -------
        `User | Guild | None`
            The resolved target if found, otherwise `None`. Guilds the bot is not in cannot be resolved.
        """
        if target_type != "user" and (guild := self.bot.get_guild(target_id)):
            return guild

        if target_type != "guild" and (user := self.bot.get_user(target_id)):
            return user

        if target_type != "user":
            try:
                return await self.bot.fetch_guild(target_id)
            except NotFound, Forbidden:
                pass

        if target_type != "guild":
            try:
                return await self.bot.fetch_user(target_id)
            except NotFound:
                pass

        return None

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # add
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def add(self, target : Blocklistable, /) -> bool:
        """
        Add a target to the blocklist database.

        Parameters
        ----------
        target : `User | Member | Guild`
            The target to blocklist.
        /

        Returns
        -------
        `bool`
            `True` if the target was newly blocklisted, `False` if it was already blocklisted.
        """
        target_type = "guild" if isinstance(target, Guild) else "user"

        async with self.bot.db.execute(t"INSERT INTO Blocklists (target_id, target_type) VALUES ({target.id}, {target_type}) ON CONFLICT DO NOTHING") as cursor:
            added = cursor.rowcount > 0

        await self.bot.db.commit()
        return added

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # view
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def view(self) -> UnnamedPaginator | None:
        """
        Display a paginator (`UnnamedPaginator`) of the blocklist.

        Returns
        -------
        `BlocklistPaginator | None`
            The paginator displaying all blocklists, or `None` if nothing is blocklisted.
        """
        blocks = sorted(await self.get(by_id = True), key = itemgetter(1))
        if not blocks:
            return None

        kinds : list[TargetType] = ["guild" if block[0] is Guild else "user" for block in blocks]
        targets = await async_gather(*(self.resolve(block[1], kind) for block, kind in zip(blocks, kinds, strict = True)))

        blocklist : list[str] = []
        for block, kind, target in zip(blocks, kinds, targets, strict = True):
            entry  = Block(block[1], kind, target)
            suffix = "" if target else " (unavailable)"
            blocklist.append(f"**{entry.label}** | {kind.title()} | `{entry.target_id}`{suffix}")

        from core.paginator import Footer, UnnamedPaginator  # ruff: ignore[import-outside-top-level]

        class BlocklistPaginator(UnnamedPaginator):
            def __init__(self) -> None:
                super().__init__(
                    blocklist,
                    title     = "# Blocklist",
                    footer    = Footer.from_name("Block"),
                    per_page  = 15,
                    color     = COLOR_BLACK,
                    container = True,
                )

        return BlocklistPaginator()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # remove
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def remove(self, target_id : int, /) -> TargetType | None:
        """
        Remove a target from the blocklist database by its ID.

        Parameters
        ----------
        target_id : `int`
            The ID of the target to remove from the blocklist.
        /

        Returns
        -------
        `Literal["user", "guild"] | None`
            The type of the removed target, or `None` if the ID was not blocklisted.
        """
        async with self.bot.db.execute(t"DELETE FROM Blocklists WHERE target_id = {target_id} RETURNING target_type") as cursor:
            row = await cursor.fetchone()

        await self.bot.db.commit()
        if not row:
            return None

        return "guild" if row[0] == "guild" else "user"

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # is_blocklisted
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def is_blocklisted(self, target : Blocklistable, /) -> bool:
        """
        Check whether a target is currently blocklisted.

        Parameters
        ----------
        target : `User | Member | Guild`
            The target to check.
        /

        Returns
        -------
        `bool`
            Whether the target is blocklisted.
        """
        async with self.bot.db.execute(t"SELECT 1 FROM Blocklists WHERE target_id = {target.id} LIMIT 1") as cursor:
            return await cursor.fetchone() is not None
