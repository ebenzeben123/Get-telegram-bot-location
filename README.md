# Get-telegram-bot-location

A Python script that reports everything the Telegram Bot API exposes about a
bot: its identity/profile, its webhook server location, and the
groups/supergroups/channels and **forum topics** the bot has recently seen.

## What it reports

1. **Bot identity & profile** — username, name, ID, capability flags,
   description, short description, and command list
   (`getMe`, `getMyName`, `getMyDescription`, `getMyShortDescription`,
   `getMyCommands`).
2. **Webhook / server location** — if the bot runs behind a webhook, Telegram
   knows the server's IP. The tool reads `getWebhookInfo` and geolocates that IP.
3. **Chats, groups & topics** — via `getUpdates`, it lists the private chats,
   groups, supergroups and channels the bot can currently see, including each
   chat's ID, type, `@username`, whether it's a forum, and the **topic (message
   thread) IDs and names** observed in it.

## Files

- `get_bot_location.py` — the script (standard library only, no dependencies)
- `.env.example` — copy to `.env` and add your bot token
- `run.bat` — Windows launcher

## Setup

1. Copy `.env.example` to `.env` and set your token:

   ```
   TELEGRAM_BOT_TOKEN=123456789:ABCdef...
   ```

   Get a token from [@BotFather](https://t.me/BotFather).

## Usage

```bash
python get_bot_location.py            # reads TELEGRAM_BOT_TOKEN from .env
python get_bot_location.py <token>    # or pass the token directly
```

On Windows you can just double-click **`run.bat`**.

## Important limitations (please read)

- **There is no Bot API method to list every group a bot belongs to.** Telegram
  does not provide one. A bot only learns about a chat — and its topics — when
  it *receives an update* from that chat.
- This tool discovers chats from `getUpdates`, which returns only the
  **recently buffered updates** (roughly the last 24 hours) that haven't been
  consumed by another poller. So the chat/topic list reflects *recent activity
  the bot has seen*, not necessarily every chat it has ever joined.
- To make a group or topic show up, send (or have someone send) a message in it,
  then run the script again. Forum **topic names** are only known when the bot
  has seen the topic's creation/edit service message; otherwise only the topic
  (thread) ID is shown.
- `getUpdates` and a webhook are mutually exclusive. If a webhook is set, chat
  enumeration is unavailable until you remove it (`deleteWebhook`). The script
  detects this and explains it.
- For the bot to see normal (non-command) group messages at all, **disable
  privacy mode** in @BotFather (`/setprivacy` → Disable) or make the bot an
  admin.
- Geolocation uses the free [ip-api.com](http://ip-api.com) service.
- Requires Python 3.6+.
