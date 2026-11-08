from dataclasses import dataclass, field
from enum import StrEnum
from typing import Self, final

from discord import AllowedMentions, Interaction, Message
from discord.abc import Messageable

from bot import ContextOrInteraction
from constants import ACCEPTED_EMOJI, DENIED_EMOJI, WARNING_EMOJI

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Response Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

type _SendTarget = ContextOrInteraction | Messageable


class MessageType(StrEnum):
    """
    Represents the message types for formatting.

    Attributes
    ----------
    success : `str`
        The 'success' message type. Uses a checkmark emoji and prefixes the title with "Successfully".
    warning : `str`
        The 'warning' message type. Uses an exclamation mark emoji and prefixes the title with "Failed to".
    error : `str`
        The 'error' message type. Uses an x-cross emoji and prefixes the title with "Failed to".
    """

    success = "success"
    warning = "warning"
    error   = "error"

    @property
    def emoji(self) -> str:
        """The emoji for this message type."""
        return {
            MessageType.success : ACCEPTED_EMOJI,
            MessageType.warning : WARNING_EMOJI,
            MessageType.error   : DENIED_EMOJI,
        }[self]

    @property
    def prefix(self) -> str:
        """The prefix for this message type."""
        match self:
            case MessageType.success:
                return "Successfully"
            case MessageType.warning | MessageType.error:
                return "Failed to"


@final
@dataclass(kw_only = True)
class PunctuationOverride:
    """
    Override punctuation suffixing behavior for message titles, subtitles, and footers.

    Parameters
    ----------
    *
    title : `bool | None = None`
        Whether the title should have punctuation forcefully suffixed to it or not (or automatically if `None` or not passed).
    subtitle : `bool | None = None`
        Whether the subtitle should have punctuation forcefully suffixed to it or not (or automatically if `None` or not passed).
    footer : `bool | None = None`
        Whether the footer should have punctuation forcefully suffixed to it or not (or automatically if `None` or not passed).
    """

    title    : bool | None = None
    subtitle : bool | None = None
    footer   : bool | None = None

    @classmethod
    def all_true(cls) -> Self:
        """
        Force all punctuation behavior to be enabled, meaning that the formatter will always suffix punctuation.

        Returns
        -------
        `Self`
            A new `PunctuationOverride` instance with all overrides set to `True`.
        """
        return cls(title = True, subtitle = True, footer = True)

    @classmethod
    def all_false(cls) -> Self:
        """
        Force all punctuation behavior to be disabled, meaning that the formatter will never suffix punctuation.

        Returns
        -------
        `Self`
            A new `PunctuationOverride` instance with all overrides set to `False`.
        """
        return cls(title = False, subtitle = False, footer = False)


@final
@dataclass(kw_only = True)
class FormatOverride:
    """
    Override formatting options for formatted messages.

    Parameters
    ----------
    *
    prefix : `bool = True`
        Whether the title of the formatter should have the MessageType's prefix prefixed to it or not.
    emoji : `bool = True`
        Whether the emoji of the formatter should have the MessageType's emoji added to it or not.
    punctuation : `PunctuationOverride | None = None`
        The punctuation rules to apply to the formatter.
    """

    prefix      : bool                = True
    emoji       : bool                = True
    punctuation : PunctuationOverride = field(default_factory = PunctuationOverride)


# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Internal Builders
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


def _apply_punctuation(text : str, default : str, *, setting : bool | None) -> str:
    if setting is False:
        return text

    if setting is True:
        return text + default

    if text.endswith((".", "?", "!", ",")):
        return text

    return text + default


def _build_title(msg_type : MessageType, title : str, config : FormatOverride) -> str:
    prefix       = msg_type.prefix if config.prefix else ""
    emoji        = f"{msg_type.emoji} " if config.emoji else ""
    default_punc =  "!" if msg_type in {MessageType.warning, MessageType.error} else "."
    clean_title  = _apply_punctuation(title, default_punc, setting = config.punctuation.title)

    if prefix:
        return f"{emoji}**{prefix} {clean_title}**"
    return f"{emoji}**{clean_title}**"


def _build_subtitle(subtitle : str | None, config : FormatOverride) -> str | None:
    if subtitle is None:
        return None

    setting = config.punctuation.subtitle
    if setting is None and subtitle.endswith("```"):
        setting = False

    return _apply_punctuation(subtitle, ".", setting = setting)


def _build_footer(footer : str | None, config : FormatOverride) -> str | None:
    if footer is None:
        return None
    return _apply_punctuation(footer, ".", setting = config.punctuation.footer)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Message Builders
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


def format_message(
    msg_type : MessageType,
    /,
    *,
    title    : str,
    subtitle : str            | None = None,
    footer   : str            | None = None,
    override : FormatOverride | None = None,
) -> str:
    """
    Format a message with an emoji corresponding to `msg_type`, a bolded title, and context-aware suffixed punctuation for `title`, `subtitle`, and `footer`.

    Parameters
    ----------
    msg_type : `MessageType`
        The type of the message.
    /
    *
    title : `str`
        The title of the message, prefixed with either "Successfully" or "Failed to".
    subtitle : `str | None = None`
        The subtitle of the message.
    footer : `str | None = None`
        The footer of the message.
    override : `FormatOverride | None = None`
        The overrides to apply to the format.

    Returns
    -------
    `str`
        The formatted message.
    """
    config = override or FormatOverride()
    lines : list[str] = [_build_title(msg_type, title, config)]

    subtitle_text = _build_subtitle(subtitle, config)
    if subtitle_text:
        lines.append(subtitle_text)

    footer_text = _build_footer(footer, config)
    if footer_text:
        lines.append(f"-# {footer_text}")

    return "\n".join(lines)


async def format_send(
    target    : _SendTarget,
    msg_type  : MessageType,
    /,
    *,
    title     : str,
    subtitle  : str             | None = None,
    footer    : str             | None = None,
    ephemeral : bool                   = True,
    mentions  : AllowedMentions | None = None,
    override  : FormatOverride  | None = None,
) -> Message | None:
    """
    Format and then send a message with an emoji corresponding to `msg_type`, a bolded title, and context-aware suffixed punctuation for `title`, `subtitle`, and `footer`.

    Parameters
    ----------
    target : `Context | Interaction | Messageable`
        The target of the message.
    msg_type : `MessageType`
        The type of the message.
    /
    *
    title : `str`
        The title of the message, prefixed with either "Successfully" or "Failed to".
    subtitle : `str | None = None`
        The subtitle of the message.
    footer : `str | None = None`
        The footer of the message.
    ephemeral : `bool = True`
        Whether the sent message should be ephemeral. Does nothing if `target` is not `Interaction`.
    mentions : `AllowedMentions | None = None`
        The mentions allowed in this message.
    override : `FormatOverride | None = None`
        The overrides to apply to the format.

    Returns
    -------
    `Message | None`
        The formatted and sent message. Possibly `None` if `target` is `Interaction`.
    """
    content = format_message(
        msg_type,
        title    = title,
        subtitle = subtitle,
        footer   = footer,
        override = override,
    )

    if isinstance(target, Interaction):
        if target.response.is_done():
            return await target.followup.send(
                content          = content,
                ephemeral        = ephemeral,
                allowed_mentions = mentions or AllowedMentions.all(),
            )

        await target.response.send_message(
            content          = content,
            ephemeral        = ephemeral,
            allowed_mentions = mentions or AllowedMentions.all(),
        )
        return await target.original_response()

    return await target.send(
        content          = content,
        allowed_mentions = mentions or AllowedMentions.all(),
    )
