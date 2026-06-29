# Get-telegram-bot-location

A simple Python script that reports location info for a Telegram bot.

A bot has no location of its own, but when it runs behind a **webhook**,
Telegram knows the IP address of the server it delivers updates to. This tool
validates the bot token, reads the webhook info, and geolocates that server IP.

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

## Notes

- If the bot uses long polling instead of a webhook, Telegram has no server IP
  to report and there is nothing to geolocate.
- Geolocation uses the free [ip-api.com](http://ip-api.com) service.
- Requires Python 3.6+.
