import os, requests
from typing import Dict, Any

PRINTER_SERVER_URL = os.environ.get("PRINTER_SERVER_URL", "https://mc-print3-server.onrender.com/print")
PRINTER_MAC = os.environ.get("PRINTER_MAC", "00:11:62:34:17:d1")

def print_order_if_needed(ai_result: Dict[str, Any]) -> Dict[str, Any]:
    if not ai_result.get("print_now"):
        return {"skipped": True}
    payload = ai_result.get("printer_payload")
    if not payload:
        return {"skipped": True}

    body = {"printerMAC": PRINTER_MAC, "orderSummary": payload}
    try:
        r = requests.post(PRINTER_SERVER_URL, json=body, timeout=10)
        return {"ok": r.ok, "status": r.status_code, "data": r.text}
    except Exception as e:
        return {"ok": False, "error": str(e)}
