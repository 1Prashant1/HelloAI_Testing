import json, re

def safe_json_from_text(text: str):
    """
    Parse a JSON object out of model text.
    1) Try direct json.loads
    2) Otherwise find the first {...} block (recursive regex) and parse
    """
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r'\{(?:[^{}]|(?R))*\}', text, flags=re.DOTALL)
    if not m:
        return None
    blob = m.group(0)
    try:
        return json.loads(blob)
    except Exception:
        return None
