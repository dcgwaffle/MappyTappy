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
