import os
import re
import requests
from notion_client import Client

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["NOTION_DATABASE_ID"].split("/")[-1].split("-")[-1].split("?")[0]

notion = Client(auth=NOTION_TOKEN)

STATUS_PROPERTY = "STATUS"


def normalize_url(url):
    if not url:
        return None
    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url
    return url


def extract_url_from_text(text):
    if not text:
        return None
    match = re.search(r"(https?://play\.google\.com/[^\s,]+|play\.google\.com/[^\s,]+)", text)
    return match.group(1) if match else None


def get_text_from_property(prop):
    if not prop:
        return ""

    prop_type = prop.get("type")

    if prop_type == "title":
        return " ".join([x.get("plain_text", "") for x in prop.get("title", [])])

    if prop_type == "rich_text":
        return " ".join([x.get("plain_text", "") for x in prop.get("rich_text", [])])

    if prop_type == "url":
        return prop.get("url") or ""

    return ""


def get_url_from_page(props):
    for name in ["URL", "Url", "url", "LINK", "Link", "link"]:
        prop = props.get(name)
        if prop:
            text = get_text_from_property(prop)
            found = extract_url_from_text(text) or text
            if found and "play.google.com" in found:
                return normalize_url(found)

    for prop in props.values():
        text = get_text_from_property(prop)
        found = extract_url_from_text(text)
        if found:
            return normalize_url(found)

    return None


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

    return any(keyword in html for keyword in terminated_keywords)


def developer_page_has_apps(html):
    html = html.lower()

    app_signals = [
        "/store/apps/details?id=",
        "aria-label=\"install\"",
        "contains ads",
        "in-app purchases",
    ]

    return any(signal in html for signal in app_signals)


def is_live(url):
    url = normalize_url(url)

    try:
        response = requests.get(
            url,
            timeout=25,
            allow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        html = response.text
        final_url = response.url.lower()

        if is_google_play_terminated(html, response.status_code):
            return False

        if "play.google.com/store/apps/dev" in final_url:
            return developer_page_has_apps(html)

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

        url = get_url_from_page(props)

        if not url:
            print("Skipped row: no Google Play URL found")
            continue

        status = "LIVE" if is_live(url) else "Terminated"

        update_status(page["id"], status)
        print(f"{url} -> {status}")


if __name__ == "__main__":
    main()
