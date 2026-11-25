# MappyTappy

A Discord bot that tracks a friend group's daily [Map Tap](https://maptap.gg) scores. Paste your share text in a channel and the bot logs it, then builds weekly leaderboards, per-level win counts, and an all-time record.

> Unofficial fan project. Not affiliated with Map Tap.

## What it does

- **Reads pasted results automatically.** No typing numbers by hand.
- **Weekly leaderboard** (Monday to Sunday), auto-posted every Sunday at 8 PM.
- **Level wins:** each day, the top scorer at each of the 5 levels earns a win.
- **All-time record:** the best total score ever, with the score at each level.

The bot reacts with a checkmark when a score is saved.

## Example input

```
www.maptap.gg November 25
94🏅 99🔥 97🔥 80🌞 88🎉
Final score: 891
```

## Commands

| Command | What it shows |
|---|---|
| `/leaderboard [last_week]` | Total points for the week, days played, and average |
<img width="447" height="204" alt="image" src="https://github.com/user-attachments/assets/7a04fb31-6142-4a60-aa3d-0c2920219958" />

| `/stats [period]` | Who wins each level most often (All time, This week, Last week) |
<img width="457" height="240" alt="image" src="https://github.com/user-attachments/assets/4b4abb9f-150a-4d33-a953-a1e89053378c" />

| `/record` | Best total score of all time, with the level breakdown |

<img width="333" height="218" alt="image" src="https://github.com/user-attachments/assets/b9a83294-920b-405c-8236-66500d4ff1f3" />


### How scoring works

- Each daily paste is saved once per person per date. A second paste for the same day is ignored.
- Only pastes dated today or up to 2 days back are accepted.
- For level wins, a day counts only if at least 2 people posted. Ties share the win.
- Levels: 1 Beginner, 2 Easy, 3 Medium, 4 Hard, 5 Extreme.

---

## Quick start (beginner friendly)

You will run your own copy of the bot with your own Discord bot account. Your bot is completely separate from anyone else's.

### What you need

- **Python 3.9 or newer.** Download it from [python.org](https://www.python.org/downloads/). On Windows, **check the box "Add python.exe to PATH"** on the first installer screen.
- A Discord account and a server where you can add bots.

### 1. Get the code

On this page, click the green **Code** button, then **Download ZIP**. Unzip it somewhere easy to find, like your Desktop.

### 2. Create your Discord bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and click **New Application**. Give it a name.
2. Open the **Installation** tab. Under **Installation Contexts**, you can uncheck **User Install** (only **Guild Install** is needed).
3. Under **Guild Install → Scopes**, add **bot** (keep `applications.commands`). In the **Permissions** box that appears, select **View Channels**, **Send Messages**, **Add Reactions**, and **Embed Links**.
4. Open the **Bot** tab:
   - Turn on **Message Content Intent** under Privileged Gateway Intents and save. Without this, the bot can't read pasted scores.
   - Click **Reset Token** and copy the token. **Treat it like a password and never share it or post it anywhere.**
5. Go back to **Installation**, copy the **Install Link**, open it in your browser, and add the bot to your server.

### 3. Get your channel ID

In Discord, go to **User Settings → Advanced** and turn on **Developer Mode**. Then right-click the channel where scores will be posted and choose **Copy Channel ID**.

### 4. Install the dependencies

Open a terminal (on Windows, search for "Command Prompt") and run:

```
pip install -r requirements.txt
```

If `pip` isn't recognized, try `py -m pip install -r requirements.txt`. You must run this from inside the unzipped folder (use `cd` to move into it).

### 5. Set your environment variables

Environment variables are named settings kept outside the code, so your token never ends up in a file. **Enter each command on its own line**, and set them in the same terminal window you'll use to run the bot.

**Windows (Command Prompt):**
```
set DISCORD_TOKEN=your-token-here
set MAPTAP_CHANNEL_ID=your-channel-id-here
```

**Windows (PowerShell):**
```
$env:DISCORD_TOKEN="your-token-here"
$env:MAPTAP_CHANNEL_ID="your-channel-id-here"
```

**Mac / Linux:**
```
export DISCORD_TOKEN="your-token-here"
export MAPTAP_CHANNEL_ID="your-channel-id-here"
```

These only last while that window stays open. If you close it, set them again.

### 6. Run it

```
python maptap_bot.py
```

If Windows says `python` isn't recognized, use `py maptap_bot.py`. When it works you'll see `Logged in as <your bot name>`. The bot only runs while this window stays open (see hosting below to keep it online all the time).

### 7. Test it

Paste a Map Tap result in your scores channel. The bot should react with a checkmark. Then try `/leaderboard`. If a slash command doesn't appear yet, restart Discord with Ctrl+R.

## Configuration

| Variable | Required | Description |
|---|---|---|
| `DISCORD_TOKEN` | Yes | Your bot token |
| `MAPTAP_CHANNEL_ID` | Yes | Channel where scores are posted and the weekly leaderboard appears |
| `BOT_TZ` | No | Timezone for dates and the weekly post (default `America/New_York`) |
| `DB_PATH` | No | Where the SQLite database is stored (default `maptap.db`) |

## Host it 24/7 (example: Railway)

Running on your own PC means the bot goes offline when you close the window. A hosting service keeps it running.

1. Put your copy of the code in your own GitHub repository (do **not** include your token).
2. Create a project on [Railway](https://railway.com) and deploy from that repository.
3. In the service's **Variables** tab, add `DISCORD_TOKEN` and `MAPTAP_CHANNEL_ID`.
4. Attach a **volume** mounted at `/data`, then add the variable `DB_PATH=/data/maptap.db`. Without a volume, scores are erased every time the bot restarts or redeploys.
5. Set the start command to `python maptap_bot.py`.
6. Check the service's **Deploy Logs** for `Logged in as ...`.

Make sure your bot isn't also running on your PC at the same time, or each score will be processed twice.

Hosting prices change, so check the provider's pricing page.

## Troubleshooting

**The bot is online but ignores pasted scores.**
Check that Message Content Intent is turned on (Developer Portal → Bot tab) and saved, that `MAPTAP_CHANNEL_ID` matches the channel you're posting in, and that the bot has permission to view and react in that channel.

**`PrivilegedIntentsRequired` error when starting.**
Same cause: Message Content Intent is off. Turn it on in the Bot tab and run the bot again.

**`KeyError: 'DISCORD_TOKEN'` (or `MAPTAP_CHANNEL_ID`).**
The variable isn't set in the window you're running the bot from. Set it again (step 5) and rerun.

**Slash commands don't show up.**
Wait a minute and restart Discord (Ctrl+R). Also confirm the bot was invited with the `applications.commands` scope.

**`The system cannot find the path specified` when using `cd`.**
You may have typed two commands on one line. Enter each command separately, and check the folder path in File Explorer.

**`sqlite3.OperationalError: unable to open database file` on a host.**
The database location doesn't exist or isn't writable. Attach a volume at `/data` and set `DB_PATH=/data/maptap.db`. On Railway, if it still fails, you may also need to check the volume's permissions in their docs.

**Leaderboard is empty after a restart or redeploy.**
Your host isn't keeping the database file. Use a persistent volume (see hosting above).

**My score was skipped or says it's outside the accepted window.**
The bot only accepts scores dated today or up to 2 days back. You can change `MAX_DAYS_BACK` near the top of `maptap_bot.py`.

**It says I already have a score logged.**
Each person gets one score per date. The first paste is kept.

**My token was exposed.**
Go to the Developer Portal → Bot tab → **Reset Token** right away and use the new one.

## Security notes

- Never commit your token. Use environment variables.
- The included `.gitignore` keeps `.env`, `maptap.db`, and Python cache files out of Git.
- Scores are stored in a local SQLite file, so there's no external database to manage.

## Limitations

- The bot is designed for one server and one channel per running copy.
- If Map Tap changes its share-text format, the parsing may need to be updated.

## License

MIT
