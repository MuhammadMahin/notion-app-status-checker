import os
import re
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
        session = requests.Session()

        response = session.get(
            url,
            timeout=30,
            allow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9"
            }
        )

        html = response.text.lower()
        final_url = response.url.lower()

        print(f"Checking: {url}")
        print(f"Final URL: {final_url}")
        print(f"Status code: {response.status_code}")

        if response.status_code in [404, 410]:
            return False

        terminated_keywords = [
            "we're sorry, the requested url was not found",
            "requested url was not found",
            "item not found",
            "not found on this server"
        ]

        if any(keyword in html for keyword in terminated_keywords):
            return False

        if "captcha" in html or "sorry/index" in final_url:
            print("Google blocked request")
            return True

        if "play.google.com/store/apps/dev" in final_url:
            if "/store/apps/details?id=" not in html:
                return False

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

    for i, page in enumerate(results["results"], start=1):

        print(f"\n===== Processing row {i} =====")

        try:
            props = page["properties"]

            if URL_PROPERTY not in props:
                print("URL property not found")
                continue

            url = props[URL_PROPERTY]["url"]

            # Try extracting from COMPANY if URL column is empty
            if not url:
                company_text = ""

                if props["COMPANY"]["title"]:
                    company_text = props["COMPANY"]["title"][0]["plain_text"]

                match = re.search(
                    r'(https?://play\.google\.com/\S+|play\.google\.com/\S+)',
                    company_text
                )

                if match:
                    url = match.group(1)

                    if not url.startswith("http"):
                        url = "https://" + url

                    print(f"Extracted URL from COMPANY: {url}")

            if not url:
                print("Skipped row: no URL found anywhere")
                continue

            status = "LIVE" if is_live(url) else "Terminated"

            try:
                update_status(page["id"], status)
                print(f"{url} -> {status}")

            except Exception as e:
                print(f"Failed updating {url}: {e}")

        except Exception as e:
            print(f"Error processing row {i}: {e}")


if __name__ == "__main__":
    main()
