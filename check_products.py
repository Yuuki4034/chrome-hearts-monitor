
import urllib.request
import urllib.parse
import urllib.error
from html.parser import HTMLParser

BASE = "https://www.chromehearts.com"

CATEGORIES = [
    "/socks",
    "/scents",
    "/intimates",
    "/boxers-leggings",
]

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = set()

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return

        href = dict(attrs).get("href")
        if not href:
            return

        url = urllib.parse.urljoin(BASE, href)
        parsed = urllib.parse.urlparse(url)

        if parsed.netloc == "www.chromehearts.com":
            clean = urllib.parse.urlunparse(
                parsed._replace(query="", fragment="")
            )
            self.links.add(clean)

def get_links(path):
    url = BASE + path
    print(f"\nChecking: {url}")

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    try:
        with urllib.request.urlopen(
            request, timeout=20
        ) as response:
            html = response.read().decode(
                "utf-8", errors="replace"
            )
            print("HTTP:", response.status)
            print("HTML length:", len(html))

        parser = LinkParser()
        parser.feed(html)

        category_prefix = url.rstrip("/") + "/"

        product_candidates = sorted(
            link for link in parser.links
            if link.startswith(category_prefix)
        )

        print("Internal links:", len(parser.links))
        print("Product candidates:",
              len(product_candidates))

        for link in product_candidates[:30]:
            print("CANDIDATE:", link)

        if not product_candidates:
            print("No product links found under category path")

    except urllib.error.HTTPError as error:
        print("HTTP ERROR:", error.code)
    except Exception as error:
        print("ERROR:", type(error).__name__, str(error))

for category in CATEGORIES:
    get_links(category)
