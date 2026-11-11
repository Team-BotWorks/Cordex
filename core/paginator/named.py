# ruff: file-ignore[private-member-access]
# pyright: reportPrivateUsage = false

from dataclasses import dataclass
from typing import Self, final, override
from warnings import warn

from discord import (
    Color,
    Emoji,
    PartialEmoji,
    SelectOption,
)

from bot import Interaction
from bot.types import NOT_PASSED
from bot.ui import (
    ActionRow,
    Container,
    InteractiveView,
    Item,
    Select,
    TextDisplay,
    VisibleLargeSeparator,
)
from core.exceptions import DependentParameterError, send_bad_operation

__all__ = ["NamedPaginator", "PageData"]


@dataclass(slots = True)
class PageData:
    """
    A page to be used in a NamedPaginator.

    Parameters
    ----------
    name : `str`
        The name of the page. Displayed as the label of the page's select option.
    content : `list[str | Item[NamedPaginator]]`
        The content of the page.
    emoji : `str | Emoji | PartialEmoji | None = None`
        The emoji displayed on the page's select option.
    description : `str | None = None`
        The description displayed under the page's select option.
    """

    name        : str
    content     : list[str | Item[NamedPaginator]]
    emoji       : str | Emoji | PartialEmoji | None = None
    description : str                        | None = None


type _ItemsList = list[Item[NamedPaginator]]

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Named Paginator
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
class _PageSelect(Select["NamedPaginator"]):
    def __init__(self, paginator : NamedPaginator) -> None:
        super().__init__(
            options = [
                SelectOption(
                    label       = page.name,
                    value       = str(index),
                    description = page.description,
                    emoji       = page.emoji,
                    default     = index == paginator.current_page,
                )
                for index, page in enumerate(paginator.pages)
            ],
        )
        self.paginator = paginator
        self.callback = self._on_select

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # _on_select
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def _on_select(self, interaction : Interaction) -> None:
        await self.paginator._turn(interaction, int(self.values[0]))


class NamedPaginator(InteractiveView):
    """
    Paginate a list of pages cleanly using a select dropdown.

    Parameters
    ----------
    data : `list[PageData]`
        The list of pages.
    /
    *
    color : `Color | None = None`
        The color of the container. Dependent on the `container` parameter.
    container : `bool = False`
        Whether the paginator should be in a Container.
    force : `bool = False`
        Whether multiple strings passed into data will be concatenated with newlines instead of TextDisplays.
    timeout : `int | None = 600`
        The amount of seconds to pass before timing out, disabling all buttons and selects. If `None`, the paginator will never time out.

    Raises
    ------
    ValueError
        You passed only one page, or more than 25 pages.
    DependentParameter
        You passed `color` without passing `container`.
    """

    def __init__(
        self,
        data      : list[PageData],
        /,
        *,
        color     : Color            | None = None,
        container : bool                    = False,
        force     : bool                    = False,
        timeout   : int | NOT_PASSED | None = NOT_PASSED,
    ) -> None:
        super().__init__(timeout = timeout if timeout is not NOT_PASSED else 600)
        self._data      : list[PageData] = data
        self._color     : Color            | None = color
        self._container : bool                    = container
        self._force     : bool                    = force
        self._timeout   : int | NOT_PASSED | None = timeout

        # ⸻ data must contain more than one page.

        if len(data) == 1:
            error = "data must contain more than one page"
            raise ValueError(error)

        if len(data) > 25:
            error = "data cannot contain more than 25 pages"
            raise ValueError(error)

        self._pages       : list[PageData] = data or [PageData("No content available.", ["No content available."])]
        self.current_page : int            = 0

        self._above_items : _ItemsList = []
        self._over_items  : _ItemsList = []
        self._under_items : _ItemsList = []
        self._below_items : _ItemsList = []

        # ⸻ color is dependent on container.

        if color and not container:
            parameter_1 = "color"
            parameter_2 = "container"
            raise DependentParameterError(parameter_1, parameter_2)

        # ⸻ Render.

        self._render()

    @property
    def pages(self) -> list[PageData]:
        """The pages in the paginator."""
        return self._pages

    @pages.setter
    def pages(self, value : list[PageData]) -> None:
        if len(value) > 25:
            error = "pages cannot contain more than 25 pages"
            raise ValueError(error)

        self._pages = value
        self._render()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # on_timeout
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @override
    async def on_timeout(self) -> None:
        # ⸻ timeout without self.message.

        if self._timeout is not NOT_PASSED and not self.message:
            warn(
                "timeout was passed but there is no message to edit.",
                category   = UserWarning,
                stacklevel = 2,
            )

        if self.timeout is not None:
            await super().on_timeout()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # add_above
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    def add_above(self, *items : Item[Self]) -> None:
        """
        Add items above the paginator.

        Parameters
        ----------
        *items : `Item[Self]`
            The items to add above the paginator.
        """
        self._above_items.extend(items)
        self._render()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # add_over
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    def add_over(self, *items : Item[Self]) -> None:
        """
        Add items over the title of the paginator.

        Parameters
        ----------
        *items : `Item[Self]`
            The items to add over the title of the paginator.
        """
        self._over_items.extend(items)
        self._render()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # add_under
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    def add_under(self, *items : Item[Self]) -> None:
        """
        Add items under the footer of the paginator.

        Parameters
        ----------
        *items : `Item[Self]`
            The items to add under the footer of the paginator.
        """
        self._under_items.extend(items)
        self._render()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # add_below
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    def add_below(self, *items : Item[Self]) -> None:
        """
        Add items below the paginator.

        Parameters
        ----------
        *items : `Item[Self]`
            The items to add below the paginator.
        """
        self._below_items.extend(items)
        self._render()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # _render
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    def _render(self) -> None:
        self.clear_items()

        # ⸻ Add all items above.

        self.append_items(self._above_items)

        page = self.pages[self.current_page]

        page_items : _ItemsList = []

        if self._force:
            page_items = [
                TextDisplay(item)
                if isinstance(item, str) else item
                for item in page.content
            ]
        else:
            accumulated : list[str] = []

            for item in page.content:
                if isinstance(item, str):
                    accumulated.append(item)
                else:
                    if accumulated:
                        page_items.append(TextDisplay("\n".join(accumulated)))
                        accumulated.clear()
                    page_items.append(item)

            if accumulated:
                page_items.append(TextDisplay("\n".join(accumulated)))

        items : _ItemsList = [*self._over_items, *page_items, VisibleLargeSeparator()]

        if len(self.pages) >= 2:
            items.append(ActionRow(_PageSelect(self)))

        items.extend(self._under_items)

        # ⸻ Add all items to the container if chosen or directly to the view if not.

        if self._container:
            self.add_item(Container(*items, color = self._color))
        else:
            self.append_items(items)

        # ⸻ Add all items below.

        self.append_items(self._below_items)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # turn
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def _turn(self, interaction : Interaction, target : int) -> None:
        if 0 <= target < len(self.pages):
            previous_page = self.current_page

            self.current_page = target
            self._render()

            try:
                if interaction.response.is_done():
                    await interaction.edit_original_response(view = self)
                else:
                    await interaction.response.edit_message(view = self)
            except Exception:
                self.current_page = previous_page
                self._render()

                await send_bad_operation(interaction, title = "turn page")
                raise
