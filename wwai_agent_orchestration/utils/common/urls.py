"""URL normalization utilities."""


def normalize_brand_url(brand_url: str) -> str:
    """
    Normalize brand URL to handle www/non-www variations consistently.
    Always converts to non-www version for consistency with older logic.
    """
    if brand_url is None or not isinstance(brand_url, str):
        return brand_url
    url = brand_url.rstrip('/')
    if not url.startswith('http://') and not url.startswith('https://'):
        url = 'https://' + url
    if url.startswith('https://www.'):
        normalized_url = url.replace('https://www.', 'https://', 1)
    elif url.startswith('http://www.'):
        normalized_url = url.replace('http://www.', 'https://', 1)
    elif url.startswith('http://'):
        normalized_url = url.replace('http://', 'https://', 1)
    else:
        normalized_url = url
    if not normalized_url.endswith('/'):
        normalized_url = normalized_url + '/'
    return normalized_url
