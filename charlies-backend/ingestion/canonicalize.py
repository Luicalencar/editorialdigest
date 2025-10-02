from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

STRIP_PARAMS = {"utm_source","utm_medium","utm_campaign","utm_term","utm_content","ref"}

def canonicalize_url(url: str) -> str:
    parts = urlsplit(url)
    qs = [(k,v) for (k,v) in parse_qsl(parts.query, keep_blank_values=True) if k not in STRIP_PARAMS]
    clean_qs = urlencode(qs, doseq=True)
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme, parts.netloc, path, clean_qs, ""))

