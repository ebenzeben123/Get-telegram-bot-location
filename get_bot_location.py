#!/usr/bin/env python3
"""Get Telegram bot info, including the groups/supergroups and topics it's in.

This script gathers everything the Telegram Bot API exposes about a bot:

  1. Bot identity and profile (getMe, getMyName, getMyDescription,
     getMyShortDescription, getMyCommands).
  2. Webhook info (getWebhookInfo) and the geolocation of the server IP
     Telegram delivers updates to, if a webhook is set.
  3. The chats the bot can currently see via getUpdates: private chats,
     groups, supergroups and channels, plus any forum *topics*
     (message threads) observed in those chats.

Important limitation: the Telegram Bot API has NO method to list every group a
bot belongs to. A bot only learns about a chat (and its topics) when it
receives an update from it. getUpdates returns the recent, pending updates
Telegram still has buffered (roughly the last 24 hours), and only works when no
webhook is set. So the chat/topic list reflects *recent activity the bot has
seen*, not necessarily every chat it has ever joined.

IMPORTANT — the "competing consumer" gotcha:
    getUpdates is a *destructive* read. The first client that fetches an update
    and advances the offset causes Telegram to delete it; it is never served
    again. If your real bot is already running (e.g. in Docker) it is polling
    getUpdates and consuming every update before this script can see it, which
    leaves the buffer empty here. To enumerate chats you must either:
      * stop the running bot instance first, then post a NEW message in the
        group and run this script (optionally with --watch), or
      * log chat.id from inside the running bot itself.

Usage:
    python get_bot_location.py             # reads token from .env / environment
    python get_bot_location.py <token>     # pass the token explicitly
    python get_bot_location.py --watch     # wait for a fresh message and report
                                           # its chat/topic (post in the group
                                           # while this runs)
"""

import json
import os
import sys
import urllib.parse
import urllib.request
import urllib.error

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
GEO_API = "http://ip-api.com/json/{ip}"

# Update fields that can carry a chat and (optionally) a message.
MESSAGE_FIELDS = (
    "message",
    "edited_message",
    "channel_post",
    "edited_channel_post",
    "business_message",
    "edited_business_message",
)
# Update fields that carry a chat but no message body.
CHAT_ONLY_FIELDS = (
    "my_chat_member",
    "chat_member",
    "chat_join_request",
    "message_reaction",
    "message_reaction_count",
)


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
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def telegram_call(token, method, params=None):
    """Call a Telegram Bot API method and return the 'result' payload.

    Returns the parsed 'result' on success. Raises RuntimeError on an API
    error so callers can decide whether the failure is fatal.
    """
    url = TELEGRAM_API.format(token=token, method=method)
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = http_get_json(url)
    if not data.get("ok"):
        raise RuntimeError(data.get("description", json.dumps(data)))
    return data["result"]


def geolocate(ip):
    """Return geolocation details for an IP address."""
    data = http_get_json(GEO_API.format(ip=ip))
    if data.get("status") != "success":
        raise RuntimeError("Geolocation failed: {}".format(data.get("message", data)))
    return data


def show_identity(token):
    """Print bot identity and profile info."""
    me = telegram_call(token, "getMe")
    print("=== Bot identity ===")
    print("Username:    @{}".format(me.get("username")))
    print("Name:        {}".format(me.get("first_name")))
    print("Bot ID:      {}".format(me.get("id")))
    print("Can join groups:          {}".format(me.get("can_join_groups")))
    print("Can read all group msgs:  {}".format(me.get("can_read_all_group_messages")))
    print("Supports inline queries:  {}".format(me.get("supports_inline_queries")))

    # These are best-effort; ignore failures so one missing field isn't fatal.
    for label, method, key in (
        ("Display name", "getMyName", "name"),
        ("Description", "getMyDescription", "description"),
        ("Short description", "getMyShortDescription", "short_description"),
    ):
        try:
            result = telegram_call(token, method)
            value = result.get(key)
            if value:
                print("{}: {}".format(label, value))
        except (RuntimeError, urllib.error.URLError):
            pass

    try:
        commands = telegram_call(token, "getMyCommands")
        if commands:
            print("Commands:")
            for cmd in commands:
                print("  /{} - {}".format(cmd.get("command"), cmd.get("description")))
    except (RuntimeError, urllib.error.URLError):
        pass


def show_webhook_location(token):
    """Print webhook info and geolocate the server IP if one is set.

    Returns True if a webhook is configured (which means getUpdates won't work).
    """
    webhook = telegram_call(token, "getWebhookInfo")
    url = webhook.get("url") or ""
    ip = webhook.get("ip_address")

    print("\n=== Webhook / server location ===")
    if not url:
        print("No webhook is set (the bot uses long polling), so Telegram has")
        print("no server IP to report and there is nothing to geolocate.")
        return False

    print("Webhook URL:   {}".format(url))
    if webhook.get("pending_update_count") is not None:
        print("Pending updates: {}".format(webhook.get("pending_update_count")))
    if not ip:
        print("Webhook is set but Telegram reported no IP address yet.")
        return True

    print("Webhook IP:    {}".format(ip))
    try:
        geo = geolocate(ip)
        print("Location info:")
        print("  Country:  {} ({})".format(geo.get("country"), geo.get("countryCode")))
        print("  Region:   {}".format(geo.get("regionName")))
        print("  City:     {}".format(geo.get("city")))
        print("  ZIP:      {}".format(geo.get("zip")))
        print("  Coords:   {}, {}".format(geo.get("lat"), geo.get("lon")))
        print("  Timezone: {}".format(geo.get("timezone")))
        print("  ISP:      {}".format(geo.get("isp")))
    except (RuntimeError, urllib.error.URLError) as exc:
        print("  Could not geolocate IP: {}".format(exc))
    return True


def _record_chat(chats, chat):
    """Store/merge a chat object into the chats accumulator and return its entry."""
    chat_id = chat.get("id")
    if chat_id is None:
        return None
    entry = chats.setdefault(chat_id, {
        "id": chat_id,
        "type": chat.get("type"),
        "title": chat.get("title"),
        "username": chat.get("username"),
        "is_forum": chat.get("is_forum", False),
        "topics": {},
    })
    # Later updates may carry richer info; fill in anything we didn't have.
    for key in ("type", "title", "username"):
        if not entry.get(key) and chat.get(key):
            entry[key] = chat.get(key)
    if chat.get("is_forum"):
        entry["is_forum"] = True
    return entry


def _record_topic(entry, message):
    """Record a forum topic (message thread) seen in a message, if any."""
    if entry is None:
        return
    thread_id = message.get("message_thread_id")
    if thread_id is None:
        return
    name = entry["topics"].get(thread_id)
    # Service messages tell us the topic's name explicitly.
    created = message.get("forum_topic_created") or message.get("forum_topic_edited")
    if created and created.get("name"):
        name = created.get("name")
    entry["topics"][thread_id] = name


def fetch_updates(token, offset=None, timeout=0):
    """Call getUpdates and return the list of update objects.

    allowed_updates=[] would use defaults (excludes chat_member); pass an
    explicit list so we also catch membership-only updates.
    """
    allowed = json.dumps(list(MESSAGE_FIELDS) + list(CHAT_ONLY_FIELDS))
    params = {
        "limit": 100,
        "timeout": timeout,
        "allowed_updates": allowed,
    }
    if offset is not None:
        params["offset"] = offset
    return telegram_call(token, "getUpdates", params)


def aggregate_chats(updates, chats=None):
    """Fold a list of updates into a chats dict keyed by chat_id."""
    if chats is None:
        chats = {}
    for update in updates:
        for field in MESSAGE_FIELDS:
            msg = update.get(field)
            if not msg:
                continue
            entry = _record_chat(chats, msg.get("chat", {}))
            _record_topic(entry, msg)
        for field in CHAT_ONLY_FIELDS:
            payload = update.get(field)
            if not payload:
                continue
            _record_chat(chats, payload.get("chat", {}))
    return chats


def collect_chats(token):
    """Pull recent updates and aggregate the chats and topics seen.

    Returns a dict keyed by chat_id. Raises RuntimeError on API error.
    """
    return aggregate_chats(fetch_updates(token))


def show_chats(token):
    """Discover and print the chats/groups/supergroups and topics the bot sees."""
    print("\n=== Chats, groups & topics (from recent updates) ===")
    try:
        chats = collect_chats(token)
    except RuntimeError as exc:
        msg = str(exc)
        if "409" in msg or "terminated by other" in msg.lower():
            print("409 Conflict: another process is already calling getUpdates")
            print("for this bot (most likely your live bot, e.g. the Docker")
            print("container). Telegram allows only ONE long-polling consumer at")
            print("a time. Stop the other instance, then run this again.")
        elif "webhook" in msg.lower():
            print("Cannot read updates because a webhook is active. Telegram only")
            print("allows getUpdates OR a webhook, not both. Remove the webhook")
            print("(deleteWebhook) temporarily to enumerate chats/topics this way.")
        else:
            print("Could not fetch updates: {}".format(msg))
        return

    if not chats:
        print("No chats found in the recent update buffer.")
        print("Most common cause: your real bot is already running (e.g. the")
        print("Docker container in the screenshot) and is polling getUpdates. It")
        print("consumes each update before this script can see it, leaving the")
        print("buffer empty here -- getUpdates is a one-time, destructive read.")
        print("")
        print("To get the supergroup id, do ONE of these:")
        print("  1. Stop the running bot instance, then post a NEW message in the")
        print("     group and run:  python get_bot_location.py --watch")
        print("  2. Log chat.id from inside the running bot when it handles a")
        print("     message (it already receives every message).")
        print("")
        print("Note: Telegram only buffers ~24h of updates, and the bot only")
        print("learns about a chat when it receives an update from it.")
        return

    # Group output by chat type for readability.
    order = ["supergroup", "group", "channel", "private"]
    by_type = {}
    for chat in chats.values():
        by_type.setdefault(chat.get("type") or "unknown", []).append(chat)

    for ctype in order + [t for t in by_type if t not in order]:
        bucket = by_type.get(ctype)
        if not bucket:
            continue
        print("\n-- {}{} ({}) --".format(
            ctype, "s" if not ctype.endswith("s") else "", len(bucket)))
        for chat in sorted(bucket, key=lambda c: str(c.get("title") or c.get("id"))):
            title = chat.get("title") or "(no title)"
            username = " @{}".format(chat["username"]) if chat.get("username") else ""
            forum = " [forum]" if chat.get("is_forum") else ""
            print("  {} (id: {}){}{}".format(title, chat.get("id"), username, forum))
            topics = chat.get("topics") or {}
            if topics:
                print("    Topics ({}):".format(len(topics)))
                for thread_id, name in sorted(topics.items()):
                    label = name if name else "(name unknown - no service msg seen)"
                    print("      - {} (topic/thread id: {})".format(label, thread_id))

    print("\nReminder: this lists only chats with activity in Telegram's recent")
    print("update buffer. It is not guaranteed to be every group the bot is in.")


def watch_for_chat(token, rounds=12, timeout=10):
    """Actively long-poll waiting for a fresh message, then report its chat.

    Intended to be run while NO other instance is polling. Post a message in the
    target group/topic while this is running and it will print the chat id.
    """
    print("\n=== Watch mode ===")
    print("Waiting for a fresh update. Post a message in the target group/topic")
    print("now. (Make sure no other bot instance is running, or you'll get a 409")
    print("or the update will be consumed elsewhere.)")
    print("Polling for up to {}s...".format(rounds * timeout))

    offset = None
    chats = {}
    try:
        # Skip whatever is already buffered so we only react to NEW messages,
        # and advance the offset past it.
        backlog = fetch_updates(token, timeout=0)
        if backlog:
            offset = backlog[-1]["update_id"] + 1
    except RuntimeError as exc:
        msg = str(exc)
        if "409" in msg or "terminated by other" in msg.lower():
            print("409 Conflict: another process is polling getUpdates for this")
            print("bot. Stop the running instance (e.g. the Docker container)")
            print("and try --watch again.")
            return
        print("Could not start watching: {}".format(msg))
        return

    for _ in range(rounds):
        try:
            updates = fetch_updates(token, offset=offset, timeout=timeout)
        except RuntimeError as exc:
            msg = str(exc)
            if "409" in msg or "terminated by other" in msg.lower():
                print("409 Conflict mid-watch: another instance grabbed the")
                print("update. Stop the other bot and retry.")
                return
            print("Error while watching: {}".format(msg))
            return
        if updates:
            offset = updates[-1]["update_id"] + 1
            aggregate_chats(updates, chats)
            break

    if not chats:
        print("\nNo message received within the time window. Confirm the bot is")
        print("in the group, no other instance is polling, and try again.")
        return

    print("\nCaptured the following chat(s):")
    for chat in chats.values():
        ctype = chat.get("type")
        title = chat.get("title") or "(no title)"
        username = " @{}".format(chat["username"]) if chat.get("username") else ""
        forum = " [forum]" if chat.get("is_forum") else ""
        print("  {} ({}){} -> id: {}{}".format(title, ctype, username, chat.get("id"), forum))
        for thread_id, name in (chat.get("topics") or {}).items():
            label = name if name else "(name unknown)"
            print("    topic: {} (thread id: {})".format(label, thread_id))


def main():
    load_env()

    args = sys.argv[1:]
    watch = False
    if "--watch" in args:
        watch = True
        args = [a for a in args if a != "--watch"]

    token = args[0] if args else os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: no bot token provided. Set TELEGRAM_BOT_TOKEN in .env "
              "or pass it as an argument.", file=sys.stderr)
        return 1

    try:
        show_identity(token)
        webhook_active = show_webhook_location(token)
        if watch:
            if webhook_active:
                print("\nWatch mode needs long polling, but a webhook is set.")
                print("Run deleteWebhook first, then retry --watch.")
            else:
                watch_for_chat(token)
        elif webhook_active:
            print("\n(Skipping chat enumeration: a webhook is set, so getUpdates")
            print(" is unavailable. See the note below.)")
            show_chats(token)  # will print the webhook-conflict guidance
        else:
            show_chats(token)
    except urllib.error.URLError as exc:
        print("Network error: {}".format(exc), file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print("Error: Telegram API error: {}".format(exc), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
