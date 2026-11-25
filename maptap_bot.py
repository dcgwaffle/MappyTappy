import os
import re
import sqlite3
import datetime as dt
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands, tasks

# ---- Config (set these as environment variables) ----
TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID = int(os.environ["MAPTAP_CHANNEL_ID"])  # channel for scores + weekly post
TZ = ZoneInfo(os.getenv("BOT_TZ", "America/New_York"))
DB_PATH = os.getenv("DB_PATH", "maptap.db")
MAX_DAYS_BACK = 2  # accept pastes for today or up to 2 days ago

# ---- Parsing ----
DATE_RE = re.compile(r"maptap\.gg\S*\s+([A-Za-z]+)\s+(\d{1,2})", re.IGNORECASE)
FINAL_RE = re.compile(r"final score:\s*(\d+)", re.IGNORECASE)


def parse_share(text: str, today: dt.date):
    """Return (date, final_score, rounds_list) or None if text isn't a Map Tap share."""
    date_m = DATE_RE.search(text)
    final_m = FINAL_RE.search(text)
    if not (date_m and final_m):
        return None

    month, day = date_m.group(1), int(date_m.group(2))
    game_date = None
    for fmt in ("%B", "%b"):
        try:
            month_num = dt.datetime.strptime(month, fmt).month
            game_date = dt.date(today.year, month_num, day)
            break
        except ValueError:
            continue
    if game_date is None:
        return None
    # Handle the new-year boundary (e.g. pasting "December 31" on Jan 1)
    if game_date > today + dt.timedelta(days=1):
        game_date = game_date.replace(year=today.year - 1)

    # Round scores sit between the date line and the "Final score" line
    between = text[date_m.end():final_m.start()]
    rounds = [int(n) for n in re.findall(r"\d+", between)]

    return game_date, int(final_m.group(1)), rounds


# ---- Database ----
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS scores (
               user_id INTEGER NOT NULL,
               game_date TEXT NOT NULL,
               final_score INTEGER NOT NULL,
               rounds TEXT,
               PRIMARY KEY (user_id, game_date)
           )"""
    )
    return conn


def save_score(user_id, game_date, final_score, rounds):
    with db() as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO scores VALUES (?, ?, ?, ?)",
            (user_id, game_date.isoformat(), final_score, ",".join(map(str, rounds))),
        )
        return cur.rowcount == 1  # False if that day was already logged


def week_bounds(today: dt.date, weeks_ago: int = 0):
    start = today - dt.timedelta(days=today.weekday()) - dt.timedelta(weeks=weeks_ago)
    return start, start + dt.timedelta(days=6)  # Monday .. Sunday


def build_leaderboard(start: dt.date, end: dt.date) -> discord.Embed:
    with db() as conn:
        rows = conn.execute(
            """SELECT user_id, SUM(final_score), COUNT(*), AVG(final_score)
               FROM scores WHERE game_date BETWEEN ? AND ?
               GROUP BY user_id ORDER BY SUM(final_score) DESC""",
            (start.isoformat(), end.isoformat()),
        ).fetchall()

    embed = discord.Embed(
        title=f"🗺️ Map Tap Leaderboard: {start:%b %d} to {end:%b %d}",
        color=discord.Color.blurple(),
    )
    if not rows:
        embed.description = "No scores logged this week yet."
        return embed

    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, (user_id, total, days, avg) in enumerate(rows):
        rank = medals[i] if i < 3 else f"`{i + 1}.`"
        lines.append(f"{rank} <@{user_id}>: **{total}** pts ({days} days, avg {avg:.0f})")
    embed.description = "\n".join(lines)
    return embed


# ---- Bot ----
intents = discord.Intents.default()
intents.message_content = True  # also enable this in the Developer Portal
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def setup_hook():
    await bot.tree.sync()
    weekly_post.start()


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or message.channel.id != CHANNEL_ID:
        return

    today = dt.datetime.now(TZ).date()
    parsed = parse_share(message.content, today)
    if not parsed:
        return

    game_date, final_score, rounds = parsed
    if game_date > today or (today - game_date).days > MAX_DAYS_BACK:
        await message.reply(
            f"That score is dated {game_date:%b %d}, which is outside the accepted window, so I skipped it.",
            mention_author=False,
        )
        return

    if save_score(message.author.id, game_date, final_score, rounds):
        await message.add_reaction("✅")
    else:
        await message.reply(
            f"You already have a score logged for {game_date:%b %d}.",
            mention_author=False,
        )


@bot.tree.command(name="leaderboard", description="Show the Map Tap weekly leaderboard")
@app_commands.describe(last_week="Show last week instead of this week")
async def leaderboard(interaction: discord.Interaction, last_week: bool = False):
    today = dt.datetime.now(TZ).date()
    start, end = week_bounds(today, 1 if last_week else 0)
    await interaction.response.send_message(embed=build_leaderboard(start, end))


LEVEL_NAMES = ["Beginner", "Easy", "Medium", "Hard", "Extreme"]


def build_stats(start, end, label: str) -> discord.Embed:
    """For each level, count how many days each player had the top score among
    everyone who posted that day. start=None means all time."""
    with db() as conn:
        if start is None:
            rows = conn.execute("SELECT user_id, game_date, rounds FROM scores").fetchall()
        else:
            rows = conn.execute(
                "SELECT user_id, game_date, rounds FROM scores WHERE game_date BETWEEN ? AND ?",
                (start.isoformat(), end.isoformat()),
            ).fetchall()

    # Group valid entries by day
    by_day = {}
    for user_id, game_date, rounds_str in rows:
        try:
            rounds = [int(x) for x in (rounds_str or "").split(",")]
        except ValueError:
            continue
        if len(rounds) != 5:
            continue
        by_day.setdefault(game_date, []).append((user_id, rounds))

    # wins[level][user_id] = number of days that user had the top score
    wins = [dict() for _ in range(5)]
    for entries in by_day.values():
        if len(entries) < 2:  # need at least 2 players to compare
            continue
        for lvl in range(5):
            top = max(r[lvl] for _, r in entries)
            for user_id, r in entries:
                if r[lvl] == top:  # ties: everyone tied gets the win
                    wins[lvl][user_id] = wins[lvl].get(user_id, 0) + 1

    embed = discord.Embed(
        title=f"📊 Map Tap Level Wins ({label})",
        color=discord.Color.green(),
    )
    lines = []
    for lvl in range(5):
        if not wins[lvl]:
            continue
        top_count = max(wins[lvl].values())
        leaders = [uid for uid, c in wins[lvl].items() if c == top_count]
        names = ", ".join(f"<@{uid}>" for uid in leaders)
        lines.append(f"**Level {lvl + 1} ({LEVEL_NAMES[lvl]}):** {top_count} - {names}")

    embed.description = (
        "\n".join(lines) if lines else "No days with 2+ players logged yet."
    )
    embed.set_footer(text="Counts days a player had the top score at that level among everyone who posted that day.")
    return embed


@bot.tree.command(name="stats", description="Show who wins each level most often")
@app_commands.describe(period="Time range (default: all time)")
@app_commands.choices(
    period=[
        app_commands.Choice(name="All time", value="all"),
        app_commands.Choice(name="This week", value="week"),
        app_commands.Choice(name="Last week", value="last"),
    ]
)
async def stats(interaction: discord.Interaction, period: app_commands.Choice[str] = None):
    value = period.value if period else "all"
    today = dt.datetime.now(TZ).date()
    if value == "all":
        embed = build_stats(None, None, "All time")
    else:
        start, end = week_bounds(today, 1 if value == "last" else 0)
        label = "Last week" if value == "last" else "This week"
        embed = build_stats(start, end, label)
    await interaction.response.send_message(embed=embed)


def build_record() -> discord.Embed:
    """All-time best total score, with who got it, when, and the score at each level."""
    with db() as conn:
        top_row = conn.execute("SELECT MAX(final_score) FROM scores").fetchone()
        top = top_row[0] if top_row else None
        rows = (
            conn.execute(
                "SELECT user_id, game_date, rounds FROM scores "
                "WHERE final_score = ? ORDER BY game_date",
                (top,),
            ).fetchall()
            if top is not None
            else []
        )

    embed = discord.Embed(title="🏆 All-Time Best Score", color=discord.Color.gold())
    if not rows:
        embed.description = "No scores logged yet."
        return embed

    blocks = []
    for user_id, game_date, rounds_str in rows:
        date_text = f"{dt.date.fromisoformat(game_date):%b %d, %Y}"
        header = f"**{top}** - <@{user_id}> on {date_text}"
        try:
            rounds = [int(x) for x in (rounds_str or "").split(",")]
        except ValueError:
            rounds = []
        if len(rounds) == 5:
            levels = "\n".join(
                f"Level {i + 1} ({LEVEL_NAMES[i]}): {score}" for i, score in enumerate(rounds)
            )
            blocks.append(f"{header}\n{levels}")
        else:
            blocks.append(header)

    embed.description = "\n\n".join(blocks)
    return embed


@bot.tree.command(name="record", description="Show the best score of all time")
async def record(interaction: discord.Interaction):
    await interaction.response.send_message(embed=build_record())


# Posts every Sunday at 8:00 PM in the configured timezone
@tasks.loop(time=dt.time(hour=20, minute=0, tzinfo=TZ))
async def weekly_post():
    today = dt.datetime.now(TZ).date()
    if today.weekday() != 6:  # 6 = Sunday
        return
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        start, end = week_bounds(today)
        await channel.send(embed=build_leaderboard(start, end))


bot.run(TOKEN)
