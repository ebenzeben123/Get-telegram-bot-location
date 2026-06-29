#!/usr/bin/env python3
"""Get Telegram bot location info.

A Telegram bot doesn't have a location of its own, but if it runs behind a
webhook, Telegram knows the IP address of the server it delivers updates to.
This script:

  1. Validates the bot token with getMe.
  2. Reads the webhook info (getWebhookInfo) to find the server IP address.
  3. Geolocates that IP address using a free public geolocation API.

Usage:
    python get_bot_location.py            # reads token from .env / environment
    python get_bot_location.py <token>    # pass the token explicitly
"""

import json
import os
import sys
import urllib.request
import urllib.error

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
GEO_API = "http://ip-api.com/json/{ip}"


def load_env(path=".env"):
    """Load simple KEY=VALUE pairs from a .env file into os.environ."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def http_get_json(url):
    """Perform a GET request and return the parsed JSON response."""
    req = urllib.request.Request(url, headers={"User-Agent": "get-telegram-bot-location"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def telegram_call(token, method):
    """Call a Telegram Bot API method and return the 'result' payload."""
    url = TELEGRAM_API.format(token=token, method=method)
    data = http_get_json(url)
    if not data.get("ok"):
        raise RuntimeError("Telegram API error: {}".format(data.get("description", data)))
    return data["result"]


def geolocate(ip):
    """Return geolocation details for an IP address."""
    data = http_get_json(GEO_API.format(ip=ip))
    if data.get("status") != "success":
        raise RuntimeError("Geolocation failed: {}".format(data.get("message", data)))
    return data


def main():
    load_env()

    token = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: no bot token provided. Set TELEGRAM_BOT_TOKEN in .env "
              "or pass it as an argument.", file=sys.stderr)
        return 1

    try:
        me = telegram_call(token, "getMe")
        print("Bot:        @{} ({})".format(me.get("username"), me.get("first_name")))
        print("Bot ID:     {}".format(me.get("id")))

        webhook = telegram_call(token, "getWebhookInfo")
        url = webhook.get("url") or ""
        ip = webhook.get("ip_address")

        if not url:
            print("\nNo webhook is set for this bot (it likely uses long polling),")
            print("so Telegram has no server IP to report. Nothing to geolocate.")
            return 0

        print("\nWebhook URL: {}".format(url))
        if not ip:
            print("Webhook is set but Telegram reported no IP address yet.")
            return 0

        print("Webhook IP:  {}".format(ip))

        geo = geolocate(ip)
        print("\nLocation info:")
        print("  Country:  {} ({})".format(geo.get("country"), geo.get("countryCode")))
        print("  Region:   {}".format(geo.get("regionName")))
        print("  City:     {}".format(geo.get("city")))
        print("  ZIP:      {}".format(geo.get("zip")))
        print("  Coords:   {}, {}".format(geo.get("lat"), geo.get("lon")))
        print("  Timezone: {}".format(geo.get("timezone")))
        print("  ISP:      {}".format(geo.get("isp")))
    except urllib.error.URLError as exc:
        print("Network error: {}".format(exc), file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print("Error: {}".format(exc), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
