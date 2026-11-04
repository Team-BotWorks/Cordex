from enum import IntEnum, nonmember

from discord import Color

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Constants
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Colors
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


COLOR_BLUE   = Color(0x87acdf)
COLOR_GREEN  = Color(0x3BA562)
COLOR_YELLOW = Color(0xF1B133)
COLOR_ORANGE = Color(0xEE773E)
COLOR_RED    = Color(0xEB3D48)
COLOR_BLACK  = Color(0x000000)
COLOR_GREY   = Color(0xABABAB)
COLOR_WHITE  = Color(0xFFFFFF)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# User IDs
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

FINESTPERFECTIONISM_ID = 1311394031640776716

DEVELOPER_IDS = frozenset({FINESTPERFECTIONISM_ID})

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Server IDs
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

SUPPORT_GUILD_ID = 1537571856964386971

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Role IDs
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

BOTWORKS_ROLE_ID = 1537572167322046514

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Role Mentions
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

BOTWORKS_MENTION = f"<@&{BOTWORKS_ROLE_ID}>"

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Channel IDs
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

BOT_ERRORS_LOG_CHANNEL_ID = 1537572340228038740
BOT_GUILD_LOG_CHANNEL_ID  = 1553792256476053604

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Emoji Strings
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

EMPLOYEE_EMOJI = "<:employee:1526002139388842075>"

DEVELOPER_EMOJI = "<:developer:1528046387143376971>"

BIG_BOT_EMOJI = "<:bot1:1526024929328365611><:bot2:1526024984739446914>"
BOT_EMOJI     = "<:bot:1526025119397318828>"

PARTNER_EMOJI = "<:partner:1526020738019102780>"

OWNER_EMOJI = "<:owner:1526002022384664606>"

BOOSTER_EMOJI = "<:booster:1526003525656514713>"

PARTNERED_SERVER_EMOJI      = "<:partnered_server:1526007129440260278>"
VERIFIED_SERVER_EMOJI       = "<:verified_server:1526007081973448787>"
BOOSTED_GLOBAL_SERVER_EMOJI = "<:boosted_global_server:1526007178035724360>"
BOOSTED_SERVER_EMOJI        = "<:boosted_server:1526007228983939143>"
GLOBAL_SERVER_EMOJI         = "<:global_server:1526007284977762436>"
SERVER_EMOJI                = "<:server:1526006935709548646>"

CATEGORY_EMOJI            = "<:category:1529676328230715534>"
RULES_EMOJI               = "<:rules:1526236777084620811>"
LOCKED_ANNOUNCEMENT_EMOJI = "<:locked_announcement:1526234327975985322>"
ANNOUNCEMENT_EMOJI        = "<:announcement:1526234373916196965>"
ACTIVE_LOCKED_STAGE_EMOJI = "<:locked_active_stage:1526233549794054216>"
ACTIVE_STAGE_EMOJI        = "<:active_stage:1526233499244171276>"
LOCKED_STAGE_EMOJI        = "<:locked_stage:1526233453597687968>"
STAGE_EMOJI               = "<:stage:1526233400686415932>"
ACTIVE_LOCKED_VOICE_EMOJI = "<:active_locked_voice:1526231750534238479>"
ACTIVE_VOICE_EMOJI        = "<:active_voice:1526231806548906004>"
LOCKED_VOICE_EMOJI        = "<:locked_voice:1526231591783895070>"
VOICE_EMOJI               = "<:voice:1526231692132614154>"
LOCKED_FORUM_EMOJI        = "<:locked_forum:1514059599530037329>"
FORUM_EMOJI               = "<:forum:1526229245943218368>"
LOCKED_MEDIA_EMOJI        = "<:locked_media:1526236949059473439>"
MEDIA_EMOJI               = "<:media:1526236896601178284>"
LOCKED_TEXT_EMOJI         = "<:locked_text:1526229560675270888>"
TEXT_EMOJI                = "<:text:1526229652178473013>"
THREAD_EMOJI              = "<:thread:1526251310704230632>"
COG_EMOJI                 = "<:cog:1514059459721429042>"

ACCEPTED_EMOJI      = "<:accepted:1522673221781164275>"
ACCEPTED_NOBG_EMOJI = "<:accepted_nobg:1562634615141826630>"
WARNING_EMOJI       = "<:warning:1514059240967245996>"
DENIED_EMOJI        = "<:denied:1514059386711048264>"
DENIED_NOBG_EMOJI   = "<:denied_nobg:1562633551361343518>"

RIGHTWARDS_ARROW_EMOJI = "<:rightwardsarrow:1530347836087074948>"
LEFTWARDS_ARROW_EMOJI  = "<:leftwardsarrow:1549505368437301358>"
MEMBERS_EMOJI          = "<:members:1546978591332376598>"
MEMBER_EMOJI           = "<:member:1529628347460489266>"
PENCIL_EMOJI           = "<:pencil:1529627235231727697>"
QUERY_EMOJI            = "<:query:1529292799164289196>"
SEARCH_EMOJI           = "<:search:1528860997396201564>"
HORIZONTAL_SETTINGS    = "<:horizontal_settings:1528938420490211459>"
ASTERISK_EMOJI         = "<:asterisk:1545783213501190244>"
MODERATION_EMOJI       = "<:moderation:1528939256557342751>"
COMMAND_EMOJI          = "<:command:1528781249718517951>"
EMOJI_EMOJI            = "<:emoji:1528940345763827775>"
REQUIRED_EMOJI         = "<:required:1558254401985187862>"

GG_SANS_FONT_EMOJI     = "<:gg_sans_font:1543707473662447706>"
TEMPO_FONT_EMOJI       = "<:tempo_font:1543699287366696980>"
SAKURA_FONT_EMOJI      = "<:sakura_font:1543700368976912445>"
JELLYBEAN_FONT_EMOJI   = "<:jellybean_font:1543702658429223022>"
MODERN_FONT_EMOJI      = "<:modern_font:1543704217116737537>"
MEDIEVAL_FONT_EMOJI    = "<:medieval_font:1543705096658096160>"
EIGHTBIT_FONT_EMOJI    = "<:8bit_font:1543701845338226890>"
VAMPYRE_FONT_EMOJI     = "<:vampyre_font:1543706163793891328>"
MONKEY_BARS_FONT_EMOJI = "<:monkey_bars_font:1558977784997482566>"
MAINFRAME_FONT_EMOJI   = "<:mainframe_font:1558978438369648670>"
HEADBANG_FONT_EMOJI    = "<:headbang_font:1558979103267225650>"
JOURNAL_FONT_EMOJI     = "<:journal_font:1558979516368556125>"

PET_CORDEX_EMOJI = "<a:pet_cordex:1526024713078571141>"

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Display Name Enums
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

# ⸻ https://docs.discord.food/resources/user#display-name-style-structure


class DisplayNameFont(IntEnum):
    """
    Represents the available display name style fonts a Discord user can have.

    `bangers`, `bio_rhyme`, `compagnon`, and `ribes` are not available for both bot and human users as they are deprecated; they are only listed here for consistency.

    Attributes
    ----------
    cherry_bomb : `int`
        Sakura font.
    chicle : `int`
        Jellybean font.
    museo_moderno : `int`
        Modern font.
    neo_castel : `int`
        Medieval font.
    pixelify : `int`
        8Bit font.
    sinistre : `int`
        Vampyre font.
    default : `int`
        Discord's GG Sans font.
    zilla_slab : `int`
        Tempo font.
    playpen_sans : `int`
        Monkey Bars font.
    orbitron : `int`
        Mainframe font.
    new_rocker : `int`
        Headbang font.
    kalam : `int`
        Journal font.
    """

    # bangers = 1

    # bio_rhyme = 2

    cherry_bomb = 3
    """Sakura font."""

    chicle = 4
    """Jellybean font."""

    # compagnon = 5

    museo_moderno = 6
    """Modern font."""

    neo_castel = 7
    """Medieval font."""

    pixelify = 8
    """8Bit font."""

    # ribes = 9

    sinistre = 10
    """Vampyre font."""

    default = 11
    """Discord's GG Sans font."""

    zilla_slab = 12
    """Tempo font."""

    playpen_sans = 13
    """Monkey Bars font."""

    orbitron = 14
    """Mainframe font."""

    new_rocker = 15
    """Headbang font."""

    kalam = 16
    """Journal font."""

    FONT_OPTIONS = nonmember(
        [
            ("GG Sans",     "default",       "Discord's GG Sans font.", GG_SANS_FONT_EMOJI),
            ("Tempo",       "zilla_slab",    "Tempo font.",             TEMPO_FONT_EMOJI),
            ("Sakura",      "cherry_bomb",   "Sakura font.",            SAKURA_FONT_EMOJI),
            ("Jellybean",   "chicle",        "Jellybean font.",         JELLYBEAN_FONT_EMOJI),
            ("Modern",      "museo_moderno", "Modern font.",            MODERN_FONT_EMOJI),
            ("Medieval",    "neo_castel",    "Medieval font.",          MEDIEVAL_FONT_EMOJI),
            ("8Bit",        "pixelify",      "8Bit font.",              EIGHTBIT_FONT_EMOJI),
            ("Vampyre",     "sinistre",      "Vampyre font.",           VAMPYRE_FONT_EMOJI),
            ("Monkey Bars", "playpen_sans",  "Monkey Bars font.",       MONKEY_BARS_FONT_EMOJI),
            ("Mainframe",   "orbitron",      "Mainframe font.",         MAINFRAME_FONT_EMOJI),
            ("Headbang",    "new_rocker",    "Headbang font.",          HEADBANG_FONT_EMOJI),
            ("Journal",     "kalam",         "Journal font.",           JOURNAL_FONT_EMOJI),
        ],
    )

    @property
    def display_name(self) -> str:
        """The name of the font in Discord."""
        return next(option[0] for option in self.FONT_OPTIONS if option[1] == self.name)

    @property
    def description(self) -> str:
        """The description of the font."""
        return next(option[2] for option in self.FONT_OPTIONS if option[1] == self.name)

    @property
    def emoji(self) -> str:
        """The emoji representation of the font."""
        return next(option[3] for option in self.FONT_OPTIONS if option[1] == self.name)


class DisplayNameEffect(IntEnum):
    """
    Represents the available display name style effects a Discord user can have.

    `glow` is not available for both bot and human users; it is only listed here for consistency.

    Attributes
    ----------
    solid : `int`
        Solid effect. Takes one color along side it.
    gradient : `int`
        Gradient effect. Takes up to five colors along side it.
    neon : `int`
        Neon effect. Takes one color along side it.
    toon : `int`
        Toon effect. Takes one color along side it.
    pop : `int`
        Pop effect. Takes one color along side it.
    prism : `int`
        Prism effect. Takes up to five colors along side it.
    gummy : `int`
        Gummy effect. Takes up to five colors along side it.
    """

    solid = 1
    """Solid effect. Takes one color along side it."""

    gradient = 2
    """Gradient effect. Takes two colors along side it."""

    neon = 3
    """Neon effect. Takes one color along side it."""

    toon = 4
    """Toon effect. Takes one color along side it."""

    pop = 5
    """Pop effect. Takes one color along side it."""

    # glow = 6

    prism = 7
    """Prism effect. Takes five colors along side it."""

    gummy = 8
    """Gummy effect. Takes five colors along side it."""

    EFFECT_OPTIONS = nonmember(
        [
            ("Solid",    "solid",    "1 color with no effect."),
            ("Gradient", "gradient", "1-5 colors with a static gradient."),
            ("Neon",     "neon",     "1 color with a neon glow."),
            ("Toon",     "toon",     "1 color with a subtle vertical gradient and stroke around the name."),
            ("Pop",      "pop",      "1 color with a colored dropshadow."),
            ("Prism",    "prism",    "1-5 colors with a horizontally-moving gradient."),
            ("Gummy",    "gummy",    "1-5 colors that squash and stretch."),
        ],
    )

    @property
    def display_name(self) -> str:
        """The name of the effect in Discord."""
        return next(option[0] for option in self.EFFECT_OPTIONS if option[1] == self.name)

    @property
    def description(self) -> str:
        """The description of the effect."""
        return next(option[2] for option in self.EFFECT_OPTIONS if option[1] == self.name)
