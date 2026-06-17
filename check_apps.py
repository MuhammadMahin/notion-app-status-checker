import os
import requests
from notion_client import Client

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["NOTION_DATABASE_ID"].split("/")[-1].split("-")[-1].split("?")[0]

notion = Client(auth=NOTION_TOKEN)

URL_PROPERTY = "URL"
STATUS_PROPERTY = "STATUS"


def is_live(url):
    if not url:
        return None

    if not url.startswith("http"):
        url = "https://" + url

    try:
        response = requests.get(
            url,
            timeout=20,
            allow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        text = response.text.lower()

        if response.status_code == 404:
            return False

        if "we're sorry, the requested url was not found" in text:
            return False

        if "not found" in text and "play.google.com" in url:
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
    results = notion.databases.query(database_id=DATABASE_ID)

    for page in results["results"]:
        props = page["properties"]

        url = props.get(URL_PROPERTY, {}).get("url")

        if not url:
            print("Skipped row: no URL")
            continue

        live = is_live(url)
        status = "LIVE" if live else "Terminated"

        update_status(page["id"], status)

        print(f"{url} -> {status}")


if __name__ == "__main__":
    main()
