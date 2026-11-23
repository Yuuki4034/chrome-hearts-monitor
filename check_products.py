
import os
import json
import re
import time
import urllib.request
import urllib.parse
from html.parser import HTMLParser
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = "https://www.chromehearts.com"
STATE_FILE = Path("products.json")

KNOWN_CATEGORIES = {
    "socks", "scents", "intimates",
    "boxers-leggings"
}

EXCLUDED = {
    "cart", "login", "contact", "baccarat",
    "locations.html", "general.html",
    "magazine.html", "privacy.html",
    "terms.html", "disclosure.html"
}

class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = set()

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if not href:
            return

        url = urllib.parse.urljoin(BASE + "/", href)
        p = urllib.parse.urlparse(url)

        if p.hostname not in {
            "www.chromehearts.com",
            "chromehearts.com"
        }:
            return

        clean = BASE + p.path.rstrip("/")
        self.links.add(clean)

def fetch(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=25) as r:
        if r.status != 200:
            raise RuntimeError(f"HTTP {r.status}")
        html = r.read().decode("utf-8", "replace")

    parser = Parser()
    parser.feed(html)
    return parser.links

def is_product(url):
    path = urllib.parse.urlparse(url).path
    return bool(
        re.search(r"/[^/]+/[A-Za-z0-9]+\.html$", path)
    )

def discover_categories(home_links):
    categories = set(KNOWN_CATEGORIES)

    for url in home_links:
        path = urllib.parse.urlparse(url).path.strip("/")
        if (
            path
            and "/" not in path
            and path not in EXCLUDED
            and not path.endswith(".html")
        ):
            categories.add(path)

    return categories

def collect_products():
    home_links = fetch(BASE + "/")
    categories = discover_categories(home_links)

    products = set()
    print("Categories:", sorted(categories))

    for category in sorted(categories):
        url = BASE + "/" + category
        links = fetch(url)
        found = {u for u in links if is_product(u)}
        products.update(found)
        print(f"{category}: {len(found)} products")
        time.sleep(1)

    if not products:
        raise RuntimeError("No products found; state unchanged")

    return products

def notify(new_products):
    token = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
    user_id = os.environ["LINE_USER_ID"]

    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst).strftime("%Y-%m-%d %H:%M")

    for i in range(0, len(new_products), 10):
        batch = new_products[i:i + 10]
        lines = [
            "CHROME HEARTS ALERT",
            f"新商品候補を検出: {len(new_products)}件",
            f"検知時刻: {now} JST",
            ""
        ]

        for url in batch:
            path = urllib.parse.urlparse(url).path
            name = path.split("/")[-2].replace("-", " ")
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
            print("LINE notification:", r.status)

def main():
    current = collect_products()

    if not STATE_FILE.exists():
        print("Initial baseline:", len(current))
        STATE_FILE.write_text(
            json.dumps(sorted(current), indent=2) + "\n"
        )
        return

    previous = set(json.loads(STATE_FILE.read_text()))
    new = sorted(current - previous)

    print("Previous:", len(previous))
    print("Current:", len(current))
    print("New:", len(new))

    if new:
        notify(new)

    # Retain previously seen URLs to avoid repeat alerts.
    combined = previous | current
    STATE_FILE.write_text(
        json.dumps(sorted(combined), indent=2) + "\n"
    )

if __name__ == "__main__":
    main()

