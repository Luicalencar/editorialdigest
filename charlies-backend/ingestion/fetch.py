import httpx, os
from typing import Optional, Tuple
from utils.logging import get_logger

log = get_logger(__name__)

async def head_if_supported(client: httpx.AsyncClient, url: str):
    try:
        r = await client.head(url, timeout=15)
        return r
    except Exception:
        return None

async def get_with_cache_headers(client: httpx.AsyncClient, url: str, etag: Optional[str], last_modified: Optional[str]):
    headers = {}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified
    r = await client.get(url, headers=headers, timeout=25)
    return r

