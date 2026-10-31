from typing import TYPE_CHECKING, Literal, cast, final, overload

from discord import Guild, Member, NotFound, User

from constants import COLOR_BLACK

if TYPE_CHECKING:
    from bot import Cordex
    from core.paginator import UnnamedPaginator

type Blocklistable = User | Member | Guild

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
        super().__init__()
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
        Fetch every blocklisted user/member/guild found in the database.

        Parameters
        ----------
        *
        by_id : `bool = False`
            Whether to return the IDs of the targets over actual userguild objects or not. This is useful in cases when testing for membership.

        Returns
        -------
        `by_id = False -> set[User | Guild]`
            Every blocklisted user/guild found in the database.
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
            if (target := await self.resolve(cast("int", row[0])))
        }

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # resolve
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def resolve(self, target_id : int, /) -> User | Guild | None:
        """
        Resolve an ID into a complete user/guild object.

        Parameters
        ----------
        target_id : `int`
            The ID of the target to resolve.
        /

        Returns
        -------
        `User | Guild | None`
            The resolved target if found, otherwise `None`.
        """
        target = self.bot.get_guild(target_id) or self.bot.get_user(target_id)
        if not target:
            try:
                target = await self.bot.fetch_guild(target_id)
            except NotFound:
                try:
                    target = await self.bot.fetch_user(target_id)
                except NotFound:
                    return None

        return target

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # add
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def add(self, target : Blocklistable, /) -> None:
        """
        Add a target to the blocklist database.

        Parameters
        ----------
        target : `User | Member | Guild`
            The target to blocklist.
        /
        """
        target_type = "guild" if isinstance(target, Guild) else "user"

        await self.bot.db.execute(t"INSERT INTO Blocklists (target_id, target_type) VALUES ({target.id}, {target_type}) ON CONFLICT DO NOTHING")
        await self.bot.db.commit()

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
        fetched_blocklist = await self.get(by_id = True)
        if not fetched_blocklist:
            return None

        blocklist : list[str] = []
        for block in fetched_blocklist:
            if block[0] is User:
                target_type = "User"
            elif block[0] is Guild:
                target_type = "Guild"
            else:
                target_type = "Unknown"

            blocklist.append(f"**{block[1]} | {target_type}**")

        from core.paginator import Footer, UnnamedPaginator  # ruff: ignore[import-outside-top-level]

        class BlocklistPaginator(UnnamedPaginator):
            def __init__(self) -> None:
                super().__init__(
                    "# Blocklist",
                    blocklist,
                    footer    = Footer("Page {smallest_page} of {biggest_page} | {count} Quarantine{s}"),
                    per_page  = 15,
                    color     = COLOR_BLACK,
                    container = True,
                )

        return BlocklistPaginator()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # remove
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def remove(self, target : Blocklistable, /) -> None:
        """
        Remove a target from the blocklist database.

        Parameters
        ----------
        target : `User | Member | Guild`
            The target to remove from the blocklist.
        /
        """
        target_type = "guild" if isinstance(target, Guild) else "user"

        await self.bot.db.execute(t"DELETE FROM Blocklists WHERE target_id = {target.id} AND target_type = {target_type}")
        await self.bot.db.commit()

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
        return any(target.id == item[1] for item in await self.get(by_id = True))
