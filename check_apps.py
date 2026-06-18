import os
import re
import requests
from notion_client import Client

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["NOTION_DATABASE_ID"].split("/")[-1].split("-")[-1].split("?")[0]

notion = Client(auth=NOTION_TOKEN)

URL_PROPERTY = "URL"
STATUS_PROPERTY = "STATUS"


def normalize_url(url):
    if not url:
        return None
    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url
    return url


def is_google_play_terminated(html, status_code):
    html = html.lower()

    terminated_keywords = [
        "we're sorry, the requested url was not found",
        "requested url was not found",
        "not found on this server",
        "item not found",
        "error 404",
        "404.",
    ]

    if status_code in [404, 410]:
        return True

    return any(word in html for word in terminated_keywords)


def developer_page_has_apps(html):
    html = html.lower()

    app_signals = [
        "/store/apps/details?id=",
        "aria-label=\"install\"",
        "install",
        "contains ads",
        "in-app purchases",
    ]

    return any(signal in html for signal in app_signals)


def is_live(url):
    url = normalize_url(url)

    if not url:
        return None

    try:
        response = requests.get(
            url,
            timeout=25,
            allow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        html = response.text
        final_url = response.url.lower()

        if is_google_play_terminated(html, response.status_code):
            return False

        # Developer page check
        if "play.google.com/store/apps/dev" in final_url:
            return developer_page_has_apps(html)

        # Single app page check
        if "play.google.com/store/apps/details" in final_url:
            return True

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
