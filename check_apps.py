import os
import requests
from notion_client import Client

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]

notion = Client(auth=NOTION_TOKEN)

URL_PROPERTY = "URL"
STATUS_PROPERTY = "STATUS"


def is_live(url):
    if not url:
        return False

    if not url.startswith("http"):
        url = "https://" + url

    try:
        response = requests.get(
            url,
            timeout=20,
            allow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        html = response.text.lower()

        bad_keywords = [
            "we're sorry, the requested url was not found",
            "requested url was not found",
            "not found on this server",
            "item not found",
            "404"
        ]

        if response.status_code in [404, 410]:
            return False

        for keyword in bad_keywords:
            if keyword in html:
                return False

        # Developer page
        if "play.google.com/store/apps/dev" in response.url.lower():
            if "/store/apps/details?id=" not in html:
                return False

        return True

    except Exception as e:
        print(e)
        return False


def update_status(page_id, status_name):
    notion.pages.update(
        page_id=page_id,
        properties={
            STATUS_PROPERTY: {
                "status": {
                    "name": status_name
                }
            }
        }
    )


def main():
    results = notion.databases.query(database_id=DATABASE_ID)

    for page in results["results"]:
        props = page["properties"]

        print("Properties found:", props.keys())

        if URL_PROPERTY not in props:
            print("URL property not found")
            continue

        url = props[URL_PROPERTY]["url"]

        if not url:
            print("Skipped row: no URL")
            continue

        status = "LIVE" if is_live(url) else "Terminated"

        update_status(page["id"], status)

        print(f"{url} -> {status}")


if __name__ == "__main__":
    main()
