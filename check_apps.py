import os
import requests
from notion_client import Client

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]

notion = Client(auth=NOTION_TOKEN)

URL_PROPERTY = "URL"
STATUS_PROPERTY = "STATUS"

def is_live(url):
    if not url.startswith("http"):
        url = "https://" + url

    try:
        r = requests.get(url, timeout=20, allow_redirects=True, headers={
            "User-Agent": "Mozilla/5.0"
        })

        text = r.text.lower()

        if r.status_code == 404:
            return False

        if "we're sorry, the requested url was not found" in text:
            return False

        if "play.google.com/store/apps/details" in url and "not found" in text:
            return False

        return True

    except Exception:
        return False

def update_status(page_id, status):
    notion.pages.update(
        page_id=page_id,
        properties={
            STATUS_PROPERTY: {
                "select": {
                    "name": status
                }
            }
        }
    )

def main():
    results = notion.data_sources.query(data_source_id=DATABASE_ID)

    for page in results["results"]:
        props = page["properties"]

        url_data = props.get(URL_PROPERTY, {}).get("url")

        if not url_data:
            continue

        status = "LIVE" if is_live(url_data) else "Terminated"

        update_status(page["id"], status)
        print(f"{url_data} -> {status}")

if __name__ == "__main__":
    main()
