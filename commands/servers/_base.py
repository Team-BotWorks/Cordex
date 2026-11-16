# pyright: reportIncompatibleMethodOverride = false

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from re import IGNORECASE
from re import compile as regex_compile
from re import escape as regex_escape
from typing import Self, cast, final, override
from unicodedata import category as unicode_category
from unicodedata import combining as unicode_combining
from unicodedata import normalize as unicode_normalize

from discord import ButtonStyle, SelectOption

from bot import Interaction
from bot.ui import Button, Confirmation, Label, Modal, Select, TextDisplay
from core.exceptions import send_bad_operation
from core.paginator import NamedPaginator
from core.responses import FormatOverride, MessageType, format_message

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Server Commands Base
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Reset Stuff
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

type ResetCandidate = tuple[str, str, bool]


@final
@dataclass(frozen = True, slots = True)
class ResetHandler:
    candidates : Callable[[str], Sequence[ResetCandidate]]
    apply      : Callable[[Interaction, set[str]], Awaitable[None]]
    refresh    : Callable[[], None]


async def _confirm_reset(
    interaction : Interaction,
    view        : NamedPaginator,
    handler     : ResetHandler,
    keys        : set[str],
    target      : str,
) -> None:
    async def accept(confirmation_interaction : Interaction) -> None:
        await confirmation_interaction.response.defer()

        try:
            await handler.apply(confirmation_interaction, keys)
        except Exception:
            await send_bad_operation(confirmation_interaction, title = f"reset {target}")
            raise
        finally:
            handler.refresh()
            if view.message:
                await view.message.edit(view = view)

        await confirmation_interaction.delete_original_response()

    async def deny(confirmation_interaction : Interaction) -> None:
        await confirmation_interaction.response.defer()
        await confirmation_interaction.delete_original_response()

    confirmation = Confirmation(
        TextDisplay(
            format_message(
                MessageType.warning,
                title    =  "Warning",
                subtitle = f"This will reset {target} to {"its" if len(keys) == 1 else "their"} default state. This cannot be undone!",
                override = FormatOverride(prefix = False),
            ),
        ),
        acceptance_label = "Reset",
        denial_label     = "Cancel",
        on_acceptance    = accept,
        on_denial        = deny,
    )

    await interaction.response.send_message(view = confirmation, ephemeral = True)
    confirmation.message = await interaction.original_response()


@final
class _ResetModal(Modal):
    def __init__(
        self,
        view       : NamedPaginator,
        handler    : ResetHandler,
        category   : str,
        candidates : Sequence[ResetCandidate],
    ) -> None:
        super().__init__(title = f"Reset {category}")
        self.view     = view
        self.handler  = handler
        self.category = category

        self._options = {key : label for key, label, configured in candidates if configured}

        options = [SelectOption(label = label, value = key) for key, label in self._options.items()]
        if len(options) > 1:
            options.append(
                SelectOption(
                    label       = f"All {category} Settings",
                    value       =  "all",
                    description = f"Reset every configured {category.lower()} setting at once.",
                ),
            )

        self._selection = Select[Self](placeholder = "Select what to reset...", options = options)
        self.selection  = Label[Self](
            text        =  "Setting",
            description = f"Choose which {category.lower()} setting to reset to its default.",
            component   = self._selection,
        )

        self.add_item(self.selection)

    @override
    async def on_submit(self, interaction : Interaction) -> None:
        choice = self._selection.values[0]

        keys   = set(self._options) if choice == "all" else {choice}
        target = f"all {self.category.lower()} settings" if choice == "all" else self._options[choice].lower()

        await _confirm_reset(interaction, self.view, self.handler, keys, target)


@final
class ResetButton(Button[NamedPaginator]):
    def __init__(self, category : str, handler : ResetHandler) -> None:
        super().__init__(label = "Reset", style = ButtonStyle.red)
        self.category = category
        self.handler  = handler

    @override
    async def callback(self, interaction : Interaction) -> None:
        if not self.view:
            return

        candidates = self.handler.candidates(self.category)

        if len(candidates) == 1:
            key, label, _ = candidates[0]
            await _confirm_reset(interaction, self.view, self.handler, {key}, label.lower())
            return

        await interaction.response.send_modal(_ResetModal(self.view, self.handler, self.category, candidates))

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Display Name Styles
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


COLOR_PATTERN = regex_compile(r"^[0-9a-fA-F]{6}(?:-[0-9a-fA-F]{6}){0,4}$")

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Biography Stuff
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

BLOCKED_TERMS = frozenset(
    {
        "2g1c",
        "2 girls 1 cup",
        "acrotomophilia",
        "alabama hot pocket",
        "alaskan pipeline",
        "anal",
        "anilingus",
        "anus",
        "apeshit",
        "arsehole",
        "ass",
        "asshole",
        "assmunch",
        "auto erotic",
        "autoerotic",
        "babeland",
        "baby batter",
        "baby juice",
        "ball gag",
        "ball gravy",
        "ball kicking",
        "ball licking",
        "ball sack",
        "ball sucking",
        "bangbros",
        "bangbus",
        "bareback",
        "barely legal",
        "barenaked",
        "bastard",
        "bastardo",
        "bastinado",
        "bbw",
        "bdsm",
        "beaner",
        "beaners",
        "beaver cleaver",
        "beaver lips",
        "bestiality",
        "big black",
        "big breasts",
        "big knockers",
        "big tits",
        "bimbos",
        "birdlock",
        "bitch",
        "bitches",
        "black cock",
        "blonde action",
        "blonde on blonde action",
        "blowjob",
        "blow job",
        "blow your load",
        "blue waffle",
        "blumpkin",
        "bollocks",
        "bondage",
        "boner",
        "boob",
        "boobs",
        "booty call",
        "brown showers",
        "brunette action",
        "bukkake",
        "bulldyke",
        "bullet vibe",
        "bullshit",
        "bung hole",
        "bunghole",
        "busty",
        "butt",
        "buttcheeks",
        "butthole",
        "camel toe",
        "camgirl",
        "camslut",
        "camwhore",
        "carpet muncher",
        "carpetmuncher",
        "chocolate rosebuds",
        "cialis",
        "circlejerk",
        "cleveland steamer",
        "clit",
        "clitoris",
        "clover clamps",
        "clusterfuck",
        "cock",
        "cocks",
        "coprolagnia",
        "coprophilia",
        "cornhole",
        "coon",
        "coons",
        "creampie",
        "cum",
        "cumming",
        "cumshot",
        "cumshots",
        "cunnilingus",
        "cunt",  # codespell:ignore
        "darkie",
        "date rape",
        "daterape",
        "deep throat",
        "deepthroat",
        "dendrophilia",
        "dick",
        "dildo",
        "dingleberry",
        "dingleberries",
        "dirty pillows",
        "dirty sanchez",
        "doggie style",
        "doggiestyle",
        "doggy style",
        "doggystyle",
        "dog style",
        "dolcett",
        "domination",
        "dominatrix",
        "dommes",
        "donkey punch",
        "double dong",
        "double penetration",
        "dp action",
        "dry hump",
        "dvda",
        "eat my ass",
        "ecchi",
        "ejaculation",
        "erotic",
        "erotism",
        "escort",
        "eunuch",
        "fag",
        "faggot",
        "fecal",
        "felch",
        "fellatio",
        "feltch",
        "female squirting",
        "femdom",
        "figging",
        "fingerbang",
        "fingering",
        "fisting",
        "foot fetish",
        "footjob",
        "frotting",
        "fuck",
        "fuck buttons",
        "fuckin",
        "fucking",
        "fucktards",
        "fudge packer",
        "fudgepacker",
        "futanari",
        "gangbang",
        "gang bang",
        "gay sex",
        "genitals",
        "giant cock",
        "girl on",
        "girl on top",
        "girls gone wild",
        "goatcx",
        "goatse",
        "god damn",
        "gokkun",
        "golden shower",
        "goodpoop",
        "goo girl",
        "goregasm",
        "grope",
        "group sex",
        "g-spot",
        "guro",
        "hand job",
        "handjob",
        "hard core",
        "hardcore",
        "hentai",
        "homoerotic",
        "honkey",
        "hooker",
        "horny",
        "hot carl",
        "hot chick",
        "how to kill",
        "how to murder",
        "huge fat",
        "humping",
        "incest",
        "intercourse",
        "jack off",
        "jail bait",
        "jailbait",
        "jelly donut",
        "jerk off",
        "jigaboo",
        "jiggaboo",
        "jiggerboo",
        "jizz",
        "juggs",
        "kike",
        "kinbaku",
        "kinkster",
        "kinky",
        "knobbing",
        "leather restraint",
        "leather straight jacket",
        "lemon party",
        "livesex",
        "lolita",
        "lovemaking",
        "make me come",
        "male squirting",
        "masturbate",
        "masturbating",
        "masturbation",
        "menage a trois",
        "milf",
        "missionary position",
        "mong",
        "motherfucker",
        "mound of venus",
        "mr hands",
        "muff diver",
        "muffdiving",
        "nambla",
        "nawashi",
        "negro",
        "neonazi",
        "nigga",
        "nigger",
        "nig nog",
        "nymphomania",
        "nipple",
        "nipples",
        "nsfw",
        "nsfw images",
        "nude",
        "nudity",
        "nutten",
        "nympho",
        "octopussy",
        "omorashi",
        "one cup two girls",
        "one guy one jar",
        "orgasm",
        "orgy",
        "paedophile",
        "paki",
        "panties",
        "panty",
        "pedobear",
        "pedophile",
        "pegging",
        "penis",
        "phone sex",
        "piece of shit",
        "pikey",
        "pissing",
        "piss pig",
        "pisspig",
        "playboy",
        "pleasure chest",
        "pole smoker",
        "ponyplay",
        "poof",
        "poon",
        "poontang",
        "punany",
        "poop chute",
        "poopchute",
        "porn",
        "porno",
        "pornography",
        "prince albert piercing",
        "pthc",
        "pubes",
        "pussy",
        "queaf",
        "queef",
        "quim",
        "raghead",
        "raging boner",
        "rape",
        "raping",
        "rapist",
        "rectum",
        "reverse cowgirl",
        "rimjob",
        "rimming",
        "rosy palm",
        "rosy palm and her 5 sisters",
        "rusty trombone",
        "sadism",
        "santorum",
        "scat",
        "schlong",
        "scissoring",
        "semen",
        "sex",
        "sexcam",
        "sexo",
        "sexy",
        "sexual",
        "sexually",
        "sexuality",
        "shaved beaver",
        "shaved pussy",
        "shemale",
        "shibari",
        "shit",
        "shitblimp",
        "shitty",
        "shota",
        "shrimping",
        "skeet",
        "slanteye",
        "slut",
        "s&m",
        "smut",
        "snatch",
        "snowballing",
        "sodomize",
        "sodomy",
        "spastic",
        "spic",
        "splooge",
        "splooge moose",
        "spooge",
        "spread legs",
        "spunk",
        "strap on",
        "strapon",
        "strappado",
        "strip club",
        "style doggy",
        "suck",
        "sucks",
        "suicide girls",
        "sultry women",
        "swastika",
        "swinger",
        "tainted love",
        "taste my",
        "tea bagging",
        "threesome",
        "throating",
        "thumbzilla",
        "tied up",
        "tight white",
        "tit",
        "tits",
        "titties",
        "titty",
        "tongue in a",
        "topless",
        "tosser",
        "towelhead",
        "tranny",
        "tribadism",
        "tub girl",
        "tubgirl",
        "tushy",
        "twat",
        "twink",
        "twinkie",
        "two girls one cup",
        "undressing",
        "upskirt",
        "urethra play",
        "urophilia",
        "vagina",
        "venus mound",
        "viagra",
        "vibrator",
        "violet wand",
        "vorarephilia",
        "voyeur",
        "voyeurweb",
        "voyuer",
        "vulva",
        "wank",
        "wetback",
        "wet dream",
        "white power",
        "whore",
        "worldsex",
        "wrapping men",
        "wrinkled starfish",
        "xx",
        "xxx",
        "yaoi",
        "yellow showers",
        "yiffy",
        "zoophilia",
    },
)

BLOCKED_PATTERN = regex_compile(
    "^(?:"
    + "|".join(regex_escape(term) for term in sorted(BLOCKED_TERMS))
    + ")(?:s|es|ed|er|ers|ing|y|ty)?$",
)
MENTION_PATTERN = regex_compile(r"@(?:everyone|here)|<(?:@[!&]?|#)\d+>", IGNORECASE)
LINK_PATTERN    = regex_compile(
    r"https?://|www\.|discord\.gg|discord(?:app)?\.com/invite"
    r"|\b[a-z0-9-]+\.(?:com|net|org|io|gg|xyz|co|me|ly|tv)\b",
    IGNORECASE,
)
WORD_PATTERN    = regex_compile(r"[^\W_]+")
REPEAT_PATTERN  = regex_compile(r"(.)\1{2,}")
LEET_TABLE      = str.maketrans("013457@$", "oieastas")


def _normalize_words(text : str) -> list[str]:
    decomposed = unicode_normalize("NFKD", text)
    cleaned    = "".join(
        character for character in decomposed
        if not unicode_combining(character) and unicode_category(character) != "Cf"
    )
    words      = cast("list[str]", WORD_PATTERN.findall(cleaned.casefold().translate(LEET_TABLE)))

    merged : list[str] = []
    run    : list[str] = []

    for word in words:
        if len(word) == 1:
            run.append(word)
            continue

        if run:
            merged.append("".join(run))
            run = []

        merged.append(word)

    if run:
        merged.append("".join(run))

    return [REPEAT_PATTERN.sub(r"\1", word) for word in merged]


def find_violation(text : str) -> str | None:
    if MENTION_PATTERN.search(text):
        return "Biographies cannot contain mentions."

    if LINK_PATTERN.search(text):
        return "Biographies cannot contain links or invites."

    if any(BLOCKED_PATTERN.match(word) for word in _normalize_words(text)):
        return "Biographies cannot contain inappropriate language."

    return None
