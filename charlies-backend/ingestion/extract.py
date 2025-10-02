from bs4 import BeautifulSoup
from readability import Document
from datetime import datetime
from typing import Tuple, Optional

def extract_article_fields(url: str, html: str) -> Tuple[str, str, Optional[str], Optional[str], str, Optional[str]]:
    """
    returns: (title, byline, published_time_iso, og_image, text, section)
    """
    soup = BeautifulSoup(html, "lxml")

    # Title
    title = None
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    # OpenGraph / Twitter
    og_title = soup.find("meta", attrs={"property":"og:title"}) or soup.find("meta", attrs={"name":"og:title"})
    if og_title and og_title.get("content"):
        title = og_title["content"].strip() or title

    # Author
    byline = None
    # Prefer human-readable byline if available
    byl_meta = soup.find("meta", attrs={"name":"byl"})
    if byl_meta and byl_meta.get("content"):
        byline = byl_meta["content"].strip()
        if byline.lower().startswith("by "):
            byline = byline[3:].strip()
    if not byline:
        for sel in [
            {"name":"meta", "attrs":{"name":"author"}},
            {"name":"meta", "attrs":{"property":"article:author"}},
        ]:
            m = soup.find(**sel)
            if m and m.get("content"):
                cand = m["content"].strip()
                # If it's a URL like https://www.nytimes.com/by/john-doe use last path as name-ish
                if cand.startswith("http"):
                    try:
                        from urllib.parse import urlsplit
                        last = urlsplit(cand).path.strip("/").split("/")[-1]
                        byline = last.replace("-", " ").title()
                    except Exception:
                        byline = cand
                else:
                    byline = cand
                break
    # Fallback to visible author link text
    if not byline:
        a = soup.find("a", attrs={"rel":"author"})
        if a and a.text:
            byline = a.text.strip()

    # Publish time
    published = None
    for sel in [
        {"name":"meta","attrs":{"property":"article:published_time"}},
        {"name":"meta","attrs":{"name":"article:published_time"}},
        {"name":"time"}
    ]:
        m = soup.find(**sel)
        if m:
            cand = m.get("content") or m.get("datetime") or m.text
            if cand:
                published = cand.strip(); break

    # Main image
    og_img = None
    for sel in [
        {"name":"meta","attrs":{"property":"og:image"}},
        {"name":"meta","attrs":{"name":"og:image"}},
        {"name":"meta","attrs":{"property":"twitter:image"}},
        {"name":"meta","attrs":{"name":"twitter:image"}}
    ]:
        m = soup.find(**sel)
        if m and m.get("content"):
            og_img = m["content"].strip(); break

    # Section/category
    section = None
    for sel in [
        {"name": "meta", "attrs": {"property": "article:section"}},
        {"name": "meta", "attrs": {"name": "article:section"}},
        {"name": "meta", "attrs": {"property": "og:section"}},
        {"name": "meta", "attrs": {"name": "section"}},
    ]:
        m = soup.find(**sel)
        if m and m.get("content"):
            section = m["content"].strip()
            break

    # Readable text
    doc = Document(html)
    content_html = doc.summary(html_partial=True)
    content_soup = BeautifulSoup(content_html, "lxml")
    text = content_soup.get_text("\n", strip=True)

    return title or "", byline or "", published, og_img, text, section
