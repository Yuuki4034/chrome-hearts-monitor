
import os
import json
import re
import time
import urllib.request
import urllib.parse
from html.parser import HTMLParser
from pathlib import Path
from datetime import datetime, timezone, timedelta

BASE = "https://www.chromehearts.com"
STATE = Path("products.json")

KNOWN = {
    "socks", "scents", "intimates",
    "boxers-leggings"
}

EXCLUDED = {
    "cart", "login", "contact", "baccarat",
    "locations", "magazine", "privacy",
    "terms", "general", "disclosure"
}

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = set()

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return

        href = dict(attrs).get("href")
        if not href:
            return

        url = urllib.parse.urljoin(BASE + "/", href)
        p = urllib.parse.urlparse(url)

        if p.hostname not in (
            "www.chromehearts.com",
            "chromehearts.com"
        ):
            return

        self.urls.add(BASE + p.path.rstrip("/"))

def fetch(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(req, timeout=25) as r:
        if r.status != 200:
            raise RuntimeError(f"HTTP {r.status}")
        html = r.read().decode("utf-8", "replace")

    parser = Links()
    parser.feed(html)
    return parser.urls

def is_product(url):
    path = urllib.parse.urlparse(url).path
    return bool(re.search(
        r"/[^/]+/[A-Za-z0-9]+\.html$", path
    ))

def collect():
    home = fetch(BASE + "/")
    categories = set(KNOWN)

    for url in home:
        path = urllib.parse.urlparse(url).path.strip("/")
        if (
            path
            and "/" not in path
            and "." not in path
            and path not in EXCLUDED
        ):
            categories.add(path)

    products = set()

    for category in sorted(categories):
        url = BASE + "/" + category
        print("Checking:", url, flush=True)

        links = fetch(url)
        found = {u for u in links if is_product(u)}
        products.update(found)

        print("Products:", len(found), flush=True)
        time.sleep(1)

    if not products:
        raise RuntimeError("No products found")

    return products

def send_line(urls):
    token = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
    user_id = os.environ["LINE_USER_ID"]

    now = datetime.now(
        timezone(timedelta(hours=9))
    ).strftime("%Y-%m-%d %H:%M")

    for start in range(0, len(urls), 10):
        batch = urls[start:start + 10]

        lines = [
            "CHROME HEARTS ALERT",
            f"新商品候補: {len(urls)}件",
            f"検知: {now} JST",
            ""
        ]

        for url in batch:
            parts = urllib.parse.urlparse(url).path.split("/")
            name = parts[-2].replace("-", " ")
            lines.append(f"{name}\n{url}\n")

        payload = {
            "to": user_id,
            "messages": [{
                "type": "text",
                "text": "\n".join(lines)[:4900]
            }]
        }

        req = urllib.request.Request(
            "https://api.line.me/v2/bot/message/push",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=25) as r:
            print("LINE:", r.status)

def main():
    current = collect()
    print("Current products:", len(current))

    if not STATE.exists():
        STATE.write_text(
            json.dumps(sorted(current), indent=2) + "\n"
        )
        print("Baseline created. No notification.")
        return

    previous = set(json.loads(STATE.read_text()))
    new = sorted(current - previous)

    print("New products:", len(new))

    if new:
        send_line(new)

    STATE.write_text(
        json.dumps(sorted(previous | current), indent=2)
        + "\n"
    )

if __name__ == "__main__":
    main()
