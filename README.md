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
<img width="447" height="204" alt="image" src="https://github.com/user-attachments/assets/6850d9f9-b02f-41a2-9414-df612386317c" />

| `/stats [period]` | Who wins each level most often (All time, This week, Last week) |
<img width="457" height="240" alt="image" src="https://github.com/user-attachments/assets/1a61ea05-b68a-4985-9eb5-2474d35a070a" />

| `/record` | Best total score of all time, with the level breakdown |

<img width="333" height="218" alt="image" src="https://github.com/user-attachments/assets/7670edd2-fa26-4b24-94bc-1e7b9f17c5d7" />


### How scoring works

- Each daily paste is saved once per person per date. A second paste for the same day is ignored.
- Only pastes dated today or up to 2 days back are accepted.
- For level wins, a day counts only if at least 2 people posted. Ties share the win.
- Levels: 1 Beginner, 2 Easy, 3 Medium, 4 Hard, 5 Extreme.

## Setup

You need your own Discord bot, since tokens are private to each bot.

### 1. Create the Discord application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and create an application.
2. Under **Installation**, choose Guild Install, add the `bot` and `applications.commands` scopes, and grant View Channels, Send Messages, Add Reactions, and Embed Links.
3. Under **Bot**, enable **Message Content Intent** and copy the bot token. Keep it secret.
4. Use the install link to add the bot to your server.

### 2. Configure

Set these environment variables:

| Variable | Required | Description |
|---|---|---|
| `DISCORD_TOKEN` | Yes | Your bot token |
| `MAPTAP_CHANNEL_ID` | Yes | Channel where scores are posted and the weekly leaderboard appears |
| `BOT_TZ` | No | Timezone for dates and the weekly post (default `America/New_York`) |
| `DB_PATH` | No | Where the SQLite database is stored (default `maptap.db`) |

### 3. Run locally

```
pip install -r requirements.txt
python maptap_bot.py
```

### 4. Host it 24/7 (example: Railway)

1. Deploy this repository to Railway.
2. Add the environment variables above.
3. Attach a volume mounted at `/data` and set `DB_PATH=/data/maptap.db`, so scores survive restarts.
4. Set the start command to `python maptap_bot.py`.

## Notes

- Never commit your token. Use environment variables.
- Scores are stored in a local SQLite file, so there's no external database to manage.

## License

MIT
