import json
import os
import requests

from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

FORUM_URL = (
    "https://forum.fusion-festival.de/viewforum.php?f=82"
)

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("Missing BOT_TOKEN or CHAT_ID environment variables")

STATE_FILE = "state.json"

SEEKING_KEYWORDS = (
    "suche",
    "suchen",
    "gesucht",
    "[suche]",
    "benötige",
    "brauche",
    "brauchen",
    "fehlt",
    "fehlen",
    "kaufen sofort",
    "ohne ticket",
    "ticket gesucht",
)

OFFERING_KEYWORDS = (
    "verkauf",
    "verkaufe",
    "verkaufen",
    "zu verkaufen",
    "abzugeben",
    "abgeben",
    "gebe ab",
    "biete ticket",
    "biete 1",
    "biete 2",
    "biete festiva",
    "biete sonntag",
)


def is_offering_ticket(title):
    t = title.lower()
    if any(keyword in t for keyword in SEEKING_KEYWORDS):
        return False

    bare = "".join(c for c in t if c.isalpha() or c.isspace()).strip()
    if bare in ("ticket", "tickets"):
        return True

    return any(keyword in t for keyword in OFFERING_KEYWORDS)


def load_state():
    try:
        with open(STATE_FILE, "r") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_state(ids):
    with open(STATE_FILE, "w") as f:
        json.dump(list(ids), f)


def send(msg):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": msg,
            "disable_web_page_preview": True,
        },
        timeout=20,
    )


def fetch_topics():
    r = requests.get(
        FORUM_URL,
        headers={
            "User-Agent": "FusionTicketWatcher/1.0"
        },
        timeout=20,
    )

    soup = BeautifulSoup(r.text, "html.parser")

    topics = []

    for a in soup.select("a.topictitle"):
        href = a.get("href", "")
        title = a.text.strip()

        if "t=" not in href:
            continue

        topic_id = href.split("t=")[1].split("&")[0]

        url = "https://forum.fusion-festival.de/" + href.lstrip("./")

        topics.append(
            {
                "id": topic_id,
                "title": title,
                "url": url,
            }
        )

    return topics


def main():
    seen = load_state()

    topics = fetch_topics()

    if not seen:
        save_state({t["id"] for t in topics})
        return

    current = set()

    for topic in topics:
        current.add(topic["id"])

        if topic["id"] not in seen and is_offering_ticket(topic["title"]):
            send(
                "🎫 NEW FUSION TICKET POST\n\n"
                f"{topic['title']}\n\n"
                f"{topic['url']}"
            )

    save_state(current)


if __name__ == "__main__":
    main()