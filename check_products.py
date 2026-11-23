
import urllib.request
import urllib.parse
from html.parser import HTMLParser

BASE = "https://www.chromehearts.com/"

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = set()

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        attributes = dict(attrs)
        href = attributes.get("href")
        if href:
            url = urllib.parse.urljoin(BASE, href)
            if url.startswith(BASE):
                self.links.add(url.split("#")[0])

request = urllib.request.Request(
    BASE,
    headers={"User-Agent": "Mozilla/5.0"}
)

with urllib.request.urlopen(
    request, timeout=30
) as response:
    html = response.read().decode(
        "utf-8", errors="replace"
    )
    print("HTTP status:", response.status)

parser = LinkParser()
parser.feed(html)

print("HTML length:", len(html))
print("Internal links:", len(parser.links))

for link in sorted(parser.links):
    print(link)
