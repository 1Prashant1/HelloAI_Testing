
# order_state.py
from typing import Dict, Any
import time

__all__ = ["SessionStore", "to_printer_payload"]

class SessionStore:
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def get(self, call_sid: str) -> Dict[str, Any]:
        if call_sid not in self._sessions:
            self._sessions[call_sid] = {
                "messages": [],
                "order": {"items": [], "payment_status": "Not Paid"},
                "delivery": None,  # "Delivery" | "Pickup"
                "customer": {"name": None, "phone": None, "address": None, "postcode": None},
                "special_notes": None,
                "finalize": False,
                "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        return self._sessions[call_sid]

    def reset(self, call_sid: str):
        if call_sid in self._sessions:
            del self._sessions[call_sid]

def to_printer_payload(sess: Dict[str, Any]) -> Dict[str, Any]:
    customer = sess.get("customer") or {}
    order = sess.get("order") or {}
    items = order.get("items") or []

    total = 0.0
    for it in items:
        try:
            price = float(it.get("price") or 0)
            qty = int(it.get("quantity") or 1)
            total += price * qty
        except Exception:
            pass

    payload = {
        "createdAt": sess.get("createdAt"),
        "customer_name": customer.get("name") or "Customer",
        "delivery_type": sess.get("delivery") or "Delivery",
        "delivery_address": customer.get("address") or "",
        "postcode": customer.get("postcode") or "",
        "contact": customer.get("phone") or "",
        "payment_status": order.get("payment_status", "Not Paid"),
        "total_amount": f"{total:.2f}" if total else "",
        "special_notes": sess.get("special_notes") or "",
        "order_breakdown": [],
    }

    for it in items:
        payload["order_breakdown"].append({
            "name": it.get("name"),
            "quantity": int(it.get("quantity") or 1),
            "price": str(it.get("price") or ""),
            "notes": it.get("notes") or "",
        })

    return payload
