import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import time
import re

# ============================================================
# CONFIGURATION
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN", "PUT_YOUR_BOT_TOKEN_HERE")

PREFIX = "!"

# How long before the bot warns the same user again
WARNING_COOLDOWN = 30

# How long messages stay in the bot's warning cache
CACHE_CLEANUP_TIME = 300

# ============================================================
# INTENTS
# ============================================================

intents = discord.Intents.default()

intents.guilds = True
intents.members = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None
)

# ============================================================
# GAME CONFIGURATION
# ============================================================

GAME_CHANNELS = {

    "nba": {
        "chat": "nba-chat",
        "script": "nba-script",

        "keywords": [
            "nba",
            "2k",
            "2k26",
            "2k25",
            "mycareer",
            "myteam",
            "park",
            "rec",
            "proam",
            "pro am",
            "street kings",
            "jumpshot",
            "jump shot",
            "green window",
            "green",
            "badge",
            "badges",
            "vc",
            "build",
            "cap breaker",
            "cap breakers",
            "shot timing",
            "tempo",
            "zen",
            "cronus"
        ],

        "script_keywords": [
            "script",
            "scripts",
            "script error",
            "script broken",
            "script broke",
            "script isn't working",
            "script isnt working",
            "script not working",
            "fix my script",
            "fix script",
            "fix scripts",
            "error in script",
            "broken script",
            "compile error",
            "compiler error"
        ]
    },

    "fortnite": {
        "chat": "fortnite-chat",
        "script": "fortnite-script",

        "keywords": [
            "fortnite",
            "fort",
            "fn",
            "battle royale",
            "creative",
            "zero build",
            "build mode",
            "vbucks",
            "v-bucks",
            "controller",
            "edit",
            "aim",
            "sensitivity",
            "deadzone"
        ],

        "script_keywords": [
            "script",
            "scripts",
            "script error",
            "script broken",
            "script broke",
            "script isn't working",
            "script isnt working",
            "script not working",
            "fix my script",
            "fix script",
            "fix scripts",
            "error in script",
            "broken script",
            "compile error",
            "compiler error"
        ]
    },

    "siege": {
        "chat": "siege-chat",
        "script": "siege-script",

        "keywords": [
            "siege",
            "r6",
            "r6s",
            "rainbow six",
            "rainbow six siege",
            "operator",
            "operators",
            "ranked",
            "unranked",
            "quick match",
            "recoil",
            "sens",
            "sensitivity",
            "crosshair",
            "aim"
        ],

        "script_keywords": [
            "script",
            "scripts",
            "script error",
            "script broken",
            "script broke",
            "script isn't working",
            "script isnt working",
            "script not working",
            "fix my script",
            "fix script",
            "fix scripts",
            "error in script",
            "broken script",
            "compile error",
            "compiler error"
        ]
    },

    "cod": {
        "chat": "cod-chat",
        "script": "cod-script",

        "keywords": [
            "cod",
            "call of duty",
            "callofduty",
            "warzone",
            "mw3",
            "mw2",
            "mw",
            "black ops",
            "bo6",
            "bo7",
            "zombies",
            "multiplayer",
            "loadout",
            "gunsmith",
            "gulag",
            "resurgence"
        ],

        "script_keywords": [
            "script",
            "scripts",
            "script error",
            "script broken",
            "script broke",
            "script isn't working",
            "script isnt working",
            "script not working",
            "fix my script",
            "fix script",
            "fix scripts",
            "error in script",
            "broken script",
            "compile error",
            "compiler error"
        ]
    }
}

# ============================================================
# ADMIN / MODERATOR CONFIGURATION
# ============================================================

MODERATOR_ROLE_NAMES = [
    "Admin",
    "Moderator",
    "Mod",
    "Owner"
]

# Users who recently received a warning
warning_cache = {}

# Prevent duplicate warnings
recent_warnings = {}

# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def normalize(text: str) -> str:
    """
    Makes message matching easier.
    """

    text = text.lower()

    # Remove punctuation
    text = re.sub(r"[^\w\s]", " ", text)

    # Remove duplicate whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def channel_name(channel):
    """
    Safely gets a channel's name.
    """

    return getattr(channel, "name", "").lower()


def is_moderator(member: discord.Member) -> bool:
    """
    Checks whether a member has a moderator/admin role.
    """

    if member.guild_permissions.administrator:
        return True

    for role in member.roles:

        if role.name.lower() in [
            name.lower()
            for name in MODERATOR_ROLE_NAMES
        ]:
            return True

    return False


def contains_keyword(message_text: str, keyword: str) -> bool:

    keyword = normalize(keyword)

    if not keyword:
        return False

    # Multi-word keywords
    if " " in keyword:
        return keyword in message_text

    # Normal word matching
    words = message_text.split()

    return keyword in words


def find_game(message_text: str):

    """
    Determines which game the message is talking about.
    """

    text = normalize(message_text)

    matches = []

    for game, config in GAME_CHANNELS.items():

        for keyword in config["keywords"]:

            if contains_keyword(text, keyword):

                matches.append(game)

                break

    return matches


def looks_like_script_question(message_text: str):

    """
    Checks whether someone appears to be asking about
    fixing/troubleshooting a script.
    """

    text = normalize(message_text)

    for game, config in GAME_CHANNELS.items():

        for keyword in config["script_keywords"]:

            if contains_keyword(text, keyword):

                return True

    return False


def find_script_game(message_text: str):

    """
    Determines which game a script question belongs to.
    """

    text = normalize(message_text)

    results = []

    for game, config in GAME_CHANNELS.items():

        game_found = False

        for keyword in config["keywords"]:

            if contains_keyword(text, keyword):

                game_found = True
                break

        if game_found:
            results.append(game)

    return results


def get_channel(guild, channel_name_to_find):

    """
    Finds a Discord channel by name.
    """

    target = channel_name_to_find.lower()

    for channel in guild.text_channels:

        if channel.name.lower() == target:

            return channel

    return None


def cooldown_active(user_id: int):

    """
    Prevents the bot from repeatedly warning someone.
    """

    now = time.time()

    last_warning = warning_cache.get(user_id)

    if last_warning is None:
        return False

    return (now - last_warning) < WARNING_COOLDOWN


def set_warning_cooldown(user_id: int):

    warning_cache[user_id] = time.time()


def clean_warning_cache():

    now = time.time()

    expired = []

    for user_id, timestamp in warning_cache.items():

        if (now - timestamp) > CACHE_CLEANUP_TIME:

            expired.append(user_id)

    for user_id in expired:

        del warning_cache[user_id]


# ============================================================
# WARNING EMBEDS
# ============================================================

def create_game_warning(game, target_channel):

    config = GAME_CHANNELS[game]

    embed = discord.Embed(
        title="Wrong Channel",
        description=(
            f"Please keep **{game.upper()}** discussion in "
            f"{target_channel.mention}.\n\n"
            f"Please move your message there so everything "
            f"stays organized."
        ),
        color=discord.Color.orange()
    )

    embed.set_footer(
        text="Server channel manager"
    )

    return embed


def create_script_warning(game, target_channel):

    embed = discord.Embed(
        title="Script Help",
        description=(
            f"If you're asking for help fixing a **{game.upper()}** "
            f"script, please use {target_channel.mention}.\n\n"
            f"That channel is specifically for script "
            f"troubleshooting and related questions."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="Server channel manager"
    )

    return embed


# ============================================================
# MESSAGE ROUTER
# ============================================================

@bot.event
async def on_message(message):

    # Ignore bots
    if message.author.bot:
        return

    # Ignore DMs
    if not message.guild:
        await bot.process_commands(message)
        return

    # Clean cache occasionally
    clean_warning_cache()

    # Moderators bypass automatic routing
    if isinstance(message.author, discord.Member):

        if is_moderator(message.author):

            await bot.process_commands(message)
            return

    content = normalize(message.content)

    if not content:

        await bot.process_commands(message)
        return

    current_channel = channel_name(message.channel)

    # ========================================================
    # SCRIPT QUESTIONS
    # ========================================================

    if looks_like_script_question(content):

        games = find_script_game(content)

        if len(games) == 1:

            game = games[0]

            target_name = GAME_CHANNELS[game]["script"]

            # Already in correct script channel
            if current_channel == target_name.lower():

                await bot.process_commands(message)
                return

            target_channel = get_channel(
                message.guild,
                target_name
            )

            if target_channel:

                if not cooldown_active(message.author.id):

                    set_warning_cooldown(
                        message.author.id
                    )

                    try:

                        await message.reply(
                            embed=create_script_warning(
                                game,
                                target_channel
                            ),
                            mention_author=False
                        )

                    except discord.Forbidden:

                        pass

                await bot.process_commands(message)
                return

    # ========================================================
    # NORMAL GAME DISCUSSION
    # ========================================================

    games = find_game(content)

    # No recognized game
    if not games:

        await bot.process_commands(message)
        return

    # If multiple games are mentioned, don't automatically
    # move them anywhere because the correct destination
    # could be ambiguous.
    if len(games) > 1:

        await bot.process_commands(message)
        return

    game = games[0]

    correct_channel = GAME_CHANNELS[game]["chat"]

    # Already in correct channel
    if current_channel == correct_channel.lower():

        await bot.process_commands(message)
        return

    # Script channel is also allowed for that game
    script_channel = GAME_CHANNELS[game]["script"]

    if current_channel == script_channel.lower():

        await bot.process_commands(message)
        return

    # Find destination
    target_channel = get_channel(
        message.guild,
        correct_channel
    )

    if target_channel:

        if not cooldown_active(message.author.id):

            set_warning_cooldown(
                message.author.id
            )

            try:

                await message.reply(
                    embed=create_game_warning(
                        game,
                        target_channel
                    ),
                    mention_author=False
                )

            except discord.Forbidden:

                pass

    await bot.process_commands(message)


# ============================================================
# BOT READY
# ============================================================

@bot.event
async def on_ready():

    print("====================================")
    print(f"Logged in as {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print("Channel manager is online.")
    print("====================================")

    try:

        synced = await bot.tree.sync()

        print(
            f"Synced {len(synced)} slash commands."
        )

    except Exception as error:

        print(
            f"Slash command sync error: {error}"
        )


# ============================================================
# HELP COMMAND
# ============================================================

@bot.command()
async def help(ctx):

    embed = discord.Embed(
        title="Server Bot Commands",
        description="Available commands:",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="!channels",
        value="Show the server's game channels.",
        inline=False
    )

    embed.add_field(
        name="!status",
        value="Show bot status.",
        inline=False
    )

    embed.add_field(
        name="/setup",
        value="Show channel setup information.",
        inline=False
    )

    await ctx.send(embed=embed)


# ============================================================
# CHANNEL LIST
# ============================================================

@bot.command()
async def channels(ctx):

    embed = discord.Embed(
        title="Game Channels",
        color=discord.Color.blurple()
    )

    for game, config in GAME_CHANNELS.items():

        chat = get_channel(
            ctx.guild,
            config["chat"]
        )

        script = get_channel(
            ctx.guild,
            config["script"]
        )

        chat_text = (
            chat.mention
            if chat
            else f"`#{config['chat']}`"
        )

        script_text = (
            script.mention
            if script
            else f"`#{config['script']}`"
        )

        embed.add_field(
            name=game.upper(),
            value=(
                f"Chat: {chat_text}\n"
                f"Scripts: {script_text}"
            ),
            inline=False
        )

    await ctx.send(embed=embed)


# ============================================================
# STATUS COMMAND
# ============================================================

@bot.command()
async def status(ctx):

    embed = discord.Embed(
        title="Bot Status",
        color=discord.Color.green()
    )

    embed.add_field(
        name="Status",
        value="Online",
        inline=True
    )

    embed.add_field(
        name="Guilds",
        value=str(len(bot.guilds)),
        inline=True
    )

    embed.add_field(
        name="Users",
        value=str(
            sum(
                guild.member_count or 0
                for guild in bot.guilds
            )
        ),
        inline=True
    )

    await ctx.send(embed=embed)


# ============================================================
# SLASH SETUP COMMAND
# ============================================================

@bot.tree.command(
    name="setup",
    description="Show the recommended server channel setup."
)
async def setup_command(interaction: discord.Interaction):

    embed = discord.Embed(
        title="Recommended Channel Setup",
        description=(
            "Create these text channels so the automatic "
            "routing system can work properly."
        ),
        color=discord.Color.blurple()
    )

    channels_text = ""

    for game, config in GAME_CHANNELS.items():

        channels_text += (
            f"**{game.upper()}**\n"
            f"• `#{config['chat']}`\n"
            f"• `#{config['script']}`\n\n"
        )

    embed.add_field(
        name="Channels",
        value=channels_text,
        inline=False
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# ============================================================
# ADMIN TEST COMMAND
# ============================================================

@bot.command()
@commands.has_permissions(manage_guild=True)
async def test(ctx, game: str = None):

    if not game:

        await ctx.send(
            "Usage: `!test nba`, `!test fortnite`, "
            "`!test siege`, or `!test cod`"
        )

        return

    game = game.lower()

    if game not in GAME_CHANNELS:

        await ctx.send(
            "Unknown game. Use `nba`, `fortnite`, "
            "`siege`, or `cod`."
        )

        return

    config = GAME_CHANNELS[game]

    target = get_channel(
        ctx.guild,
        config["chat"]
    )

    if not target:

        await ctx.send(
            f"Couldn't find `#{config['chat']}`."
        )

        return

    await ctx.send(
        embed=create_game_warning(
            game,
            target
        )
    )


# ============================================================
# ERROR HANDLER
# ============================================================

@test.error
async def test_error(ctx, error):

    if isinstance(
        error,
        commands.MissingPermissions
    ):

        await ctx.send(
            "You need **Manage Server** permission "
            "to use this command."
        )

        return

    print(
        f"Command error: {error}"
    )


# ============================================================
# RUN BOT
# ============================================================

if __name__ == "__main__":

    if TOKEN == "PUT_YOUR_BOT_TOKEN_HERE":

        print(
            "ERROR: Put your Discord bot token "
            "in the DISCORD_TOKEN environment variable."
        )

    else:

        bot.run(TOKEN)