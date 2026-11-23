
import os
import json
import re
import time
import urllib.request
import urllib.parse
import urllib.error
from collections import deque
from html.parser import HTMLParser
from pathlib import Path
from datetime import datetime, timezone, timedelta

BASE = "https://www.chromehearts.com"
HOSTS = {"www.chromehearts.com", "chromehearts.com"}
STATE = Path("products.json")

KNOWN = {"socks", "scents", "intimates", "boxers-leggings"}
EXCLUDED = {
    "cart", "login", "contact", "baccarat",
    "locations", "magazine", "privacy",
    "terms", "general", "disclosure",
    "account", "checkout"
}

MAX_PAGES = 80
MAX_DEPTH = 3
DELAY = 1.0

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
        parsed = urllib.parse.urlparse(url)

        if parsed.hostname not in HOSTS:
            return

        path = parsed.path.rstrip("/") or "/"
        self.urls.add(BASE + path)

def fetch(url):
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=20) as response:
                if response.status != 200:
                    raise RuntimeError(
                        f"HTTP {response.status}"
                    )
                html = response.read().decode(
                    "utf-8", "replace"
                )

            parser = Links()
            parser.feed(html)
            return parser.urls

        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == 2:
                raise RuntimeError(
                    f"Failed to fetch {url}: {exc}"
                ) from exc
            time.sleep(2 * (attempt + 1))

def is_product(url):
    path = urllib.parse.urlparse(url).path
    return bool(re.search(
        r"/[^/]+/[A-Za-z0-9]+\.html$", path
    ))

def is_category(url):
    path = urllib.parse.urlparse(url).path.strip("/")
    if not path:
        return False

    parts = path.split("/")
    if parts[0].lower() in EXCLUDED:
        return False

    if any("." in part for part in parts):
        return False

    return len(parts) <= MAX_DEPTH

def collect():
    home = fetch(BASE + "/")
    categories = {
        BASE + "/" + name for name in KNOWN
    }

    for url in home:
        if is_category(url):
            categories.add(url)

    queue = deque(
        (url, 1) for url in sorted(categories)
    )
    visited = set()
    products = set()

    while queue and len(visited) < MAX_PAGES:
        url, depth = queue.popleft()

        if url in visited:
            continue

        visited.add(url)
        print("Checking:", url, flush=True)

        try:
            links = fetch(url)
        except Exception as exc:
            print("Fetch error:", exc, flush=True)
            raise

        found = {
            link for link in links if is_product(link)
        }
        products.update(found)

        print("Products:", len(found), flush=True)

        if depth < MAX_DEPTH:
            for link in sorted(links):
                if (
                    is_category(link)
                    and link not in visited
                ):
                    queue.append((link, depth + 1))

        time.sleep(DELAY)

    if not products:
        raise RuntimeError("No products found")

    print("Pages checked:", len(visited))
    print("Current products:", len(products))
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
            parts = urllib.parse.urlparse(
                url
            ).path.split("/")
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
        json.dumps(
            sorted(previous | current), indent=2
        ) + "\n"
    )

if __name__ == "__main__":
    if os.environ.get("DRY_RUN") == "1":
        current = collect()
        print("DRY RUN: products found:", len(current))
        print("DRY RUN: no LINE notifications")
        print("DRY RUN: products.json unchanged")
    else:
        main()
