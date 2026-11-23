
import os
import json
import urllib.request
import urllib.error

token = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
user_id = os.environ["LINE_USER_ID"]

url = "https://api.line.me/v2/bot/message/push"

data = {
    "to": user_id,
    "messages": [
        {
            "type": "text",
            "text": "CHROME HEARTS ALERT\nLINE通知の接続テストです！"
        }
    ]
}

request = urllib.request.Request(
    url,
    data=json.dumps(data).encode("utf-8"),
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    },
    method="POST"
)

try:
    with urllib.request.urlopen(request, timeout=20) as response:
        print("LINE API response:", response.status)
        print("テストメッセージ送信完了")
except urllib.error.HTTPError as error:
    print("LINE API error:", error.code)
    print(error.read().decode("utf-8"))
    raise
