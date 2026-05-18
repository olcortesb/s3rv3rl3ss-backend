import re
from urllib.request import urlopen


def _clean_cell(text):
    text = re.sub(r'`([^`]*)`', r'\1', text)
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'\*\*([^*]*)\*\*', r'\1', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _short_name(text):
    """Extract just the first sentence or meaningful name from a cell."""
    text = _clean_cell(text)
    # Take first sentence only
    for sep in ['. ', ' This ', ' For ', ' See ', ' Note:']:
        idx = text.find(sep)
        if idx > 0:
            text = text[:idx]
            break
    return text.strip()


def _short_value(text):
    """Clean value cell."""
    return _clean_cell(text)


def _parse_tables(content):
    tables = []
    lines = content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('|') and '|' in line[1:]:
            headers_raw = [c.strip() for c in line.split('|')[1:-1]]
            headers = [_clean_cell(h).lower() for h in headers_raw]
            if i + 1 < len(lines) and lines[i + 1].startswith('| ---'):
                i += 2
                rows = []
                while i < len(lines) and lines[i].startswith('|'):
                    cols = [_clean_cell(c) for c in lines[i].split('|')[1:-1]]
                    rows.append(dict(zip(headers, cols)))
                    i += 1
                if rows:
                    tables.append({"headers": headers, "rows": rows})
                continue
        i += 1
    return tables


def fetch_docs_limits(url):
    try:
        with urlopen(url, timeout=10) as resp:
            content = resp.read().decode('utf-8')
        tables = _parse_tables(content)
        limits = []
        seen = set()
        for table in tables:
            h = table["headers"]
            name_key = next((k for k in h if k in ("resource", "name", "resource or operation", "quota name", "action", "throughput quota name")), None)
            value_key = next((k for k in h if k in ("quota", "default quota", "default", "maximum", "aws default quota value")), None)
            if not name_key or not value_key:
                continue
            for row in table["rows"]:
                name = _short_name(row.get(name_key, ''))
                value = _short_value(row.get(value_key, ''))
                if not name or not value or name.lower() in seen:
                    continue
                seen.add(name.lower())
                limits.append({"name": name, "value": value})
        print(f"[docs] Got {len(limits)} limits from {url.split('/')[-1]}")
        return limits
    except Exception as e:
        print(f"[docs] Error fetching limits from {url}: {e}")
        return None
