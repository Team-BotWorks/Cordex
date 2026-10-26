# ruff: file-ignore[private-member-access]
# pyright: reportPrivateUsage = false

from collections.abc import Sequence
from typing import Self, final, override
from warnings import warn

from discord import ButtonStyle, Color, Message

from bot import Interaction
from bot.ui import (
    ActionRow,
    Button,
    ButtonSection,
    Container,
    Item,
    Label,
    LayoutView,
    Modal,
    TextDisplay,
    TextInput,
    VisibleLargeSeparator,
    button,
)
from core.exceptions import (
    DependentParameterError,
    send_bad_operation,
    send_bad_request,
)

__all__ = ["UnnamedPaginator"]

type _ItemsList      = list[Item[UnnamedPaginator]]
type _ItemsOrStrList = Sequence[str | Item[UnnamedPaginator]]
type _TitleButton    = Button[UnnamedPaginator]

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Unnamed Paginator
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
class _PageJumpModal(Modal, title = "Jump to Page"):
    def __init__(self, paginator : UnnamedPaginator) -> None:
        super().__init__()
        self.paginator = paginator

        max_digits = len(str(len(paginator.pages)))

        self._page_input = TextInput[Self](
            placeholder = "ex: 5",
            min_length  = 1,
            max_length  = max_digits,
        )
        self.page_input  = Label[Self](
            text        = "Enter a page number.",
            description = "Enter a positive integer greater than or equal to one.",
            component   = self._page_input,
        )
        self.add_item(self.page_input)

    @override
    async def on_submit(self, interaction : Interaction) -> None:
        try:
            page = int(self._page_input.value) - 1
        except ValueError:
            await send_bad_request(
                interaction,
                title    = "jump to page",
                subtitle = "Please enter a positive integer greater than or equal to one",
            )
            return

        # ⸻ You're already on this page!

        if page == self.paginator.current_page:
            await send_bad_request(
                interaction,
                title    = "jump to page",
                subtitle = "You are already viewing this page",
            )
            return

        # ⸻ Success..?

        if 0 <= page < len(self.paginator.pages):
            await self.paginator._turn(interaction, page)

        # ⸻ Must be within the bounds of 1 and the highest page!

        else:
            await send_bad_request(
                interaction,
                title    =  "jump to page",
                subtitle = f"Please enter a page between 1 and {len(self.paginator.pages)}",
            )


@final
class _PageRow(ActionRow["UnnamedPaginator"]):
    def __init__(self, paginator : UnnamedPaginator) -> None:
        super().__init__()
        self.paginator = paginator

        # ⸻ Remove the first, page, and last buttons if we have 2 pages, and remove only the page button if we have 3 pages.

        if len(paginator.pages) == 2:
            self.remove_item(self.btn_first)
            self.remove_item(self.btn_page)
            self.remove_item(self.btn_last)
        elif len(paginator.pages) == 3:
            self.remove_item(self.btn_page)

        # ⸻ Update.

        self.update_states()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # update_states
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    def update_states(self) -> None:
        current = self.paginator.current_page
        total   = len(self.paginator.pages)

        is_first = (current == 0)
        is_last  = (current == total - 1)

        if total >= 3:
            self.btn_first.disabled = is_first
            self.btn_last.disabled  = is_last

        self.btn_backward.disabled = is_first
        self.btn_forward.disabled  = is_last

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Buttons
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @button(label = "<<")
    async def btn_first(self, interaction : Interaction, _button : Button[UnnamedPaginator]) -> None:
        await self.paginator._turn(interaction, 0)

    @button(label = "<")
    async def btn_backward(self, interaction : Interaction, _button : Button[UnnamedPaginator]) -> None:
        await self.paginator._turn(interaction, self.paginator.current_page - 1)

    @button(label = "...", style = ButtonStyle.green)
    async def btn_page(self, interaction : Interaction, _button : Button[UnnamedPaginator]) -> None:
        await interaction.response.send_modal(_PageJumpModal(self.paginator))

    @button(label = ">")
    async def btn_forward(self, interaction : Interaction, _button : Button[UnnamedPaginator]) -> None:
        await self.paginator._turn(interaction, self.paginator.current_page + 1)

    @button(label = ">>")
    async def btn_last(self, interaction : Interaction, _button : Button[UnnamedPaginator]) -> None:
        await self.paginator._turn(interaction, len(self.paginator.pages) - 1)


@final
class Footer:
    """
    Represents the footer of an UnnamedPaginator.

    Parameters
    ----------
    content : `str | None = "Page {smallest_page} of {biggest_page} | {count} Item{s}"`
        The content of the footer.
        - `{smallest_page}` will be replaced with the smallest page number.
        - `{biggest_page}` will be replaced with the biggest page number.
        - `{count}` will be replaced with the length of the paginator data list.
        - `{s}` will be either 's', or nothing if only one item is provided in the paginator data list, but only if `singularize` is `True`.

    /
    *
    singularize : `bool = True`
        Whether to remove the '{s}' placeholder on `footer` (if any) if only one item is provided in the paginator data list or not. Does nothing if `on_single` is `None`.
    on_single : `str | None = "{count} Item{s}"`
        The footer (or lack thereof) to use when only a single page is present in the paginator.
        - `{count}` will be replaced with the length of the paginator data list.
        - `{s}` will be either 's', or nothing if only one item is provided in the paginator data list, but only if `singularize` is `True`.

    """

    def __init__(
        self,
        content     : str | None = "Page {smallest_page} of {biggest_page} | {count} Item{s}",
        /,
        *,
        singularize : bool       = True,
        on_single   : str | None = None,
    ) -> None:
        super().__init__()
        self.content     = f"-# {content}" if content is not None else None
        self.singularize = singularize
        self.on_single   = f"-# {on_single}" if on_single is not None else None


class UnnamedPaginator(LayoutView):
    """
    Paginate a list of data cleanly using <<, <, page jump, >, and >> buttons.

    Parameters
    ----------
    title : `str`
        The title of the paginator.
    data : ItemsOrStrList`
        The data to paginate.
    /
    *
    footer : `Footer | None = None`
        The footer of the paginator.
    per_page : `int = 5`
        The amount of data to display per page. Defaults to 5.
    color : `Color | None = None`
        The color of the container. Dependent on the `container` parameter.
    container : `bool = False`
        Whether the paginator should be in a Container.
    force : `bool = False`
        Whether multiple strings passed into data will be concatenated with newlines instead of `TextDisplay`s.
    timeout : `int | None = 600`
        The amount of seconds to pass before timing out, disabling all buttons and selects. If None, the paginator will never time out.

    Raises
    ------
    DependentParameter
        You passed `color` without passing `container`.
    """

    def __init__(
        self,
        title     : str,
        data      : _ItemsOrStrList,
        /,
        *,
        footer    : Footer | None = None,
        per_page  : int           = 5,
        color     : Color  | None = None,
        container : bool          = False,
        force     : bool          = False,
        timeout   : int    | None = 600,
    ) -> None:
        super().__init__(timeout = timeout)
        self.message : Message | None = None

        self._title     : str             = title
        self._data      : _ItemsOrStrList = data
        self._footer    : Footer | None   = footer if footer is not None else Footer()
        self._per_page  : int             = per_page
        self._color     : Color  | None   = color
        self._container : bool            = container
        self._force     : bool            = force

        self.pages        : list[_ItemsOrStrList] = [
            data[i : i + per_page]
            for i in range(0, len(data), per_page)
        ] or [["No content available."]]
        self.current_page : int                   = 0
        self._page_row    : _PageRow | None       = _PageRow(self) if len(self.pages) >= 2 else None

        self._above_items  : _ItemsList          = []
        self._over_items   : _ItemsList          = []
        self._under_items  : _ItemsList          = []
        self._below_items  : _ItemsList          = []
        self._title_button : _TitleButton | None = None

        # ⸻ color is dependent on container.

        if color and not container:
            parameter_1 = "color"
            parameter_2 = "container"
            raise DependentParameterError(parameter_1, parameter_2)

        # ⸻ Render.

        self._render()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # on_timeout
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @override
    async def on_timeout(self) -> None:

        # ⸻ timeout without self.message.

        if self.timeout and not self.message:
            warn(
                "timeout was passed but there is no message to edit.",
                category   = UserWarning,
                stacklevel = 2,
            )

        if self.timeout is not None:
            await super().on_timeout()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # _get_footer
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    def _get_footer(self) -> str | None:
        if not self._footer:
            return None

        if len(self.pages) == 1:
            if self._footer.on_single is None:
                return None
            footer = self._footer.on_single
        else:
            if self._footer.content is None:
                return None
            footer = self._footer.content

        footer = footer.replace("{smallest_page}", str(self.current_page + 1))
        footer = footer.replace("{biggest_page}", str(len(self.pages)))
        footer = footer.replace("{count}", str(len(self._data)))
        if self._footer.singularize:
            footer = footer.replace("{s}", "s" if len(self._data) > 1 else "")
        return footer

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
    # set_title_button
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    def set_title_button(self, button : _TitleButton | None, /) -> None:
        """
        Set the accessory button in the title.

        Parameters
        ----------
        button : `TitleButton | None`
            The button to put in the title, or no button if `None`.
        /
        """
        self._title_button = button
        self._render()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # update_data
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    def update_data(self, title : str, data : _ItemsOrStrList) -> None:
        """
        Update the paginator's data then re-render it.

        Parameters
        ----------
        title : str
            The paginator's new title.
        data : ItemsOrStrList
            The paginator's new data.
        """
        self._title       = title
        self._data        = data
        self.current_page = 0

        self.pages = [
            data[i:i + self._per_page]
            for i in range(0, len(data), self._per_page)
        ] or [["No content available."]]

        self._page_row = _PageRow(self) if len(self.pages) >= 2 else None

        self._render()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # _render
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    def _render(self) -> None:
        self.clear_items()

        # ⸻ Add all items above.

        self.append_items(self._above_items)

        page_items : _ItemsList = []

        if self._force:
            page_items = [
                TextDisplay(item)
                if isinstance(item, str) else item
                for item in self.pages[self.current_page]
            ]
        else:
            accumulated : list[str] = []

            for item in self.pages[self.current_page]:
                if isinstance(item, str):
                    accumulated.append(item)
                else:
                    if accumulated:
                        page_items.append(TextDisplay("\n".join(accumulated)))
                        accumulated.clear()
                    page_items.append(item)

            if accumulated:
                page_items.append(TextDisplay("\n".join(accumulated)))

        title_button = self._title_button

        title_item : Item[Self | UnnamedPaginator] = (
            ButtonSection(self._title, button = title_button)
            if title_button is not None else
            TextDisplay(self._title)
        )

        show_footer = self._footer is not None
        footer_text = self._get_footer() if show_footer else None

        items : _ItemsList = [
            *self._over_items,
            title_item,
            VisibleLargeSeparator(),
            *page_items,
        ]

        if show_footer and footer_text is not None:
            items.append(VisibleLargeSeparator())
            items.append(TextDisplay(footer_text))

        if self._page_row:
            self._page_row.update_states()
            items.append(self._page_row)

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
                await interaction.response.edit_message(view = self)
            except Exception:
                self.current_page = previous_page
                self._render()
                await send_bad_operation(interaction, title = "turn page")
                raise
