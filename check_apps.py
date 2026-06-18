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
            timeout=30,
            allow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        html = response.text.lower()
        final_url = response.url.lower()

        # Definite termination messages
        terminated_keywords = [
            "we're sorry, the requested url was not found",
            "requested url was not found",
            "not found on this server",
            "item not found",
            "error 404"
        ]

        if response.status_code in [404, 410]:
            return False

        if any(keyword in html for keyword in terminated_keywords):
            return False

        # Developer page
        if "play.google.com/store/apps/dev" in final_url:

            # If Google redirected to search or homepage, treat as terminated
            if "search?" in final_url:
                return False

            # If app links exist on the page, developer is live
            if "/store/apps/details?id=" in html:
                return True

            # Otherwise assume terminated
            return False

        # App page
        if "play.google.com/store/apps/details" in final_url:
            return True

        return True

    except Exception as e:
        print(f"Error checking {url}: {e}")
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
