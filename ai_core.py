import os, json
from typing import Dict, Any, List, Optional
from openai import OpenAI
from pathlib import Path
from utils.json_utils import safe_json_from_text
from order_state import SessionStore, to_printer_payload
_openai_client = None
SESSION = SessionStore()

def get_openai_client() -> OpenAI:
    """Create the OpenAI client on first use (so imports never crash)."""
    global _openai_client
    if _openai_client is None:
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            # Raise a clear error at runtime (boot still succeeds so /healthz works)
            raise RuntimeError("OPENAI_API_KEY is not set in the environment.")
        _openai_client = OpenAI(api_key=key)
    return _openai_client
    
# Set by app.py
MENU_TOOLS = None
CATALOG_DIGEST = ""

def register_menu_tools(menu_tools):
    global MENU_TOOLS
    MENU_TOOLS = menu_tools

def set_menu_digest(digest: str):
    global CATALOG_DIGEST
    CATALOG_DIGEST = digest or ""

def _load_base_prompt_text() -> str:
    p = Path(__file__).parent / "prompts" / "base_system_prompt.txt"
    return p.read_text(encoding="utf-8") if p.exists() else ""

def _load_scenarios_text() -> str:
    # repo copy or uploaded file path you use in testing
    for sp in [
        Path(__file__).parent / "prompts" / "scenarios.txt",
        Path("/mnt/data/Scenarios.txt"),
    ]:
        if sp.exists():
            try:
                return sp.read_text(encoding="utf-8")[:20000]
            except Exception:
                pass
    return ""

def get_system_prompt() -> str:
    parts = []
    parts.append(_load_base_prompt_text())
    scen = _load_scenarios_text()
    if scen:
        parts.append("\n# Conversation Scenarios (authoritative):\n" + scen)
    if CATALOG_DIGEST:
        parts.append("\n# Catalog Digest (ALL categories + item names):\n" + CATALOG_DIGEST)
    parts.append("\n# Tools: Use list_categories/get_category/search_items for exact JSON. Do not invent.")
    return "\n".join(p for p in parts if p)

# OpenAI function-tools
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_categories",
            "description": "List all menu categories.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_category",
            "description": "Get full JSON for a specific category (items/options).",
            "parameters": {
                "type": "object",
                "properties": {"category": {"type": "string"}},
                "required": ["category"]
            }
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_items",
            "description": "Fuzzy search items across ALL categories.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]
            }
        },
    },
]

def _build_messages(call_sid: str, user_text: Optional[str]):
    sess = SESSION.get(call_sid)
    messages: List[Dict[str, Any]] = []
    if not sess["messages"]:
        messages.append({"role": "system", "content": get_system_prompt()})
        messages.append({"role": "user", "content": "__CALL_START__"})
    else:
        messages.extend(sess["messages"])
    if user_text is not None:
        messages.append({"role": "user", "content": user_text})
    return messages[-24:]

def _tool_dispatch(name: str, args_json: str) -> str:
    if not MENU_TOOLS:
        return json.dumps({"error": "menu tools unavailable"})
    try:
        args = json.loads(args_json or "{}")
    except Exception:
        args = {}
    if name == "list_categories":
        return json.dumps(MENU_TOOLS.list_categories())
    if name == "get_category":
        return json.dumps(MENU_TOOLS.get_category(args.get("category")))
    if name == "search_items":
        return json.dumps(MENU_TOOLS.search_items(args.get("query", "")))
    return json.dumps({"error": f"unknown tool {name}"})

def _chat_once(messages: List[Dict[str, Any]]):
    client = get_openai_client()
    return client.chat.completions.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        messages=messages,
        temperature=0.3,
        max_tokens=700,
        tools=TOOLS,
        tool_choice="auto",
    )

def _call_ai_with_tools(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    # up to 3 tool hops
    for _ in range(3):
        resp = _chat_once(messages)
        msg = resp.choices[0].message
        # tool calls?
        if getattr(msg, "tool_calls", None):
            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [tc.model_dump() for tc in msg.tool_calls],
            })
            for tc in msg.tool_calls:
                result = _tool_dispatch(tc.function.name, tc.function.arguments)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": tc.function.name,
                    "content": result,
                })
            continue
        # final content
        text = msg.content or ""
        data = safe_json_from_text(text)
        if not data:
            data = {"say": "Sorry, I didn’t catch that. Delivery or Pickup?", "dialogue_act": "fallback"}
        return data
    return {"say": "Let me confirm—Delivery or Pickup?", "dialogue_act": "ask_delivery_or_pickup"}

def next_turn(call_sid: str, user_text: Optional[str]) -> Dict[str, Any]:
    messages = _build_messages(call_sid, user_text)
    data = _call_ai_with_tools(messages)

    sess = SESSION.get(call_sid)
    sess["messages"] = messages
    if data.get("order"): sess["order"] = data["order"]
    if "delivery" in data and data["delivery"] is not None: sess["delivery"] = data["delivery"]
    if data.get("customer"): sess["customer"] = {**(sess.get("customer") or {}), **data["customer"]}
    if "special_notes" in data: sess["special_notes"] = data.get("special_notes")
    finalize_flag = bool(data.get("finalize") or data.get("print_now"))
    sess["finalize"] = finalize_flag

    printer_payload = to_printer_payload(sess) if finalize_flag else None
    return {
        "say": data.get("say") or "Okay.",
        "end_call": bool(data.get("end_call")),
        "print_now": bool(data.get("print_now")),
        "printer_payload": printer_payload,
    }

def reset_session(call_sid: str):
    SESSION.reset(call_sid)
