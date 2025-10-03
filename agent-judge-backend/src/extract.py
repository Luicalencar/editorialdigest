from bs4 import BeautifulSoup
from readability import Document
from typing import Optional, Tuple


def extract_meta_and_text(url: str, html: str) -> Tuple[dict, str]:
    soup = BeautifulSoup(html, "lxml")
    title = None
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    og_title = soup.find("meta", attrs={"property": "og:title"}) or soup.find("meta", attrs={"name": "og:title"})
    if og_title and og_title.get("content"):
        title = og_title["content"].strip() or title

    byline = None
    byl_meta = soup.find("meta", attrs={"name": "byl"})
    if byl_meta and byl_meta.get("content"):
        byline = byl_meta["content"].strip()
        if byline.lower().startswith("by "):
            byline = byline[3:].strip()
    if not byline:
        for sel in [
            {"name": "meta", "attrs": {"name": "author"}},
            {"name": "meta", "attrs": {"property": "article:author"}},
        ]:
            m = soup.find(**sel)
            if m and m.get("content"):
                cand = m["content"].strip()
                byline = cand
                break
    if not byline:
        a = soup.find("a", attrs={"rel": "author"})
        if a and a.text:
            byline = a.text.strip()

    thumbnail = None
    for sel in [
        {"name": "meta", "attrs": {"property": "og:image"}},
        {"name": "meta", "attrs": {"name": "og:image"}},
        {"name": "meta", "attrs": {"property": "twitter:image"}},
        {"name": "meta", "attrs": {"name": "twitter:image"}},
    ]:
        m = soup.find(**sel)
        if m and m.get("content"):
            thumbnail = m["content"].strip()
            break

    doc = Document(html)
    content_html = doc.summary(html_partial=True)
    content_soup = BeautifulSoup(content_html, "lxml")
    text = content_soup.get_text("\n", strip=True)

    return {"title": title or "", "author": byline or "", "thumbnail": thumbnail}, text



