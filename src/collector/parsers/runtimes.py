from datetime import date
from urllib.request import urlopen

RUNTIMES_URL = "https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.md"

MONTHS = {'Jan':'01','Feb':'02','Mar':'03','Apr':'04','May':'05','Jun':'06',
          'Jul':'07','Aug':'08','Sep':'09','Oct':'10','Nov':'11','Dec':'12'}


def _parse_date(text):
    try:
        parts = text.replace(',', '').split()
        if len(parts) == 3 and parts[0] in MONTHS:
            return f"{parts[2]}-{MONTHS[parts[0]]}-{parts[1].zfill(2)}"
    except Exception:
        pass
    return None


def fetch_runtimes():
    try:
        with urlopen(RUNTIMES_URL, timeout=10) as resp:
            content = resp.read().decode('utf-8')
        runtimes = []
        in_table = False
        today = date.today().isoformat()
        for line in content.split('\n'):
            if '| Name | Identifier |' in line:
                in_table = True
                continue
            if in_table and line.startswith('| ---'):
                continue
            if in_table and line.startswith('|'):
                cols = [c.strip() for c in line.split('|')[1:-1]]
                if len(cols) >= 4:
                    name = cols[0].strip()
                    identifier = cols[1].replace('`', '').strip()
                    eol_str = cols[3].strip()
                    if not name or not identifier:
                        continue
                    eol_date = _parse_date(eol_str)
                    status = 'deprecated' if eol_date and eol_date < today else 'active'
                    entry = {"name": name, "identifier": identifier, "status": status}
                    if eol_date:
                        entry["eol"] = eol_date
                    runtimes.append(entry)
            elif in_table and not line.startswith('|'):
                break
        print(f"[runtimes] Got {len(runtimes)} runtimes from docs")
        return runtimes
    except Exception as e:
        print(f"[runtimes] Error fetching: {e}")
        return None
