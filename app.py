import os
import uuid
from flask import Flask, request, send_from_directory, Response, jsonify
from twilio.twiml.voice_response import VoiceResponse
from dotenv import load_dotenv

from ai_core import next_turn, reset_session, register_menu_tools, set_menu_digest
from stt_tts import tts_to_mp3, ensure_audio_folder
from printers.star_mcp import print_order_if_needed
from menu_loader import MenuStore
from tools_menu import MenuTools

load_dotenv()
app = Flask(__name__)

AUDIO_DIR = os.path.join(os.path.dirname(__file__), "static", "audio")
ensure_audio_folder(AUDIO_DIR)

# Load menus & expose tool handles
MENU_STORE = MenuStore(os.path.join(os.path.dirname(__file__), "menus"))
MENU_TOOLS = MenuTools(MENU_STORE)
register_menu_tools(MENU_TOOLS)
set_menu_digest(MENU_TOOLS.build_digest())  # includes ALL categories

@app.get("/healthz")
def healthz():
    return {"ok": True, "categories": MENU_STORE.categories()}

@app.get("/audio/<path:filename>")
def serve_audio(filename):
    return send_from_directory(AUDIO_DIR, filename, mimetype="audio/mpeg")

@app.get("/debug/menu")
def debug_menu():
    return jsonify({"categories": MENU_STORE.categories(), "sample": MENU_STORE.get_any_sample()})

def twiml_play_and_gather(audio_url: str, action: str = "/process") -> Response:
    vr = VoiceResponse()
    with vr.gather(
        input="speech",
        action=action,
        method="POST",
        timeout=6,
        speech_timeout="auto",   # Twilio speech end-of-utterance
    ) as g:
        g.play(audio_url)
    return Response(str(vr), mimetype="text/xml")

def twiml_play_and_hangup(audio_url: str) -> Response:
    vr = VoiceResponse()
    vr.play(audio_url)
    vr.hangup()
    return Response(str(vr), mimetype="text/xml")

@app.route("/voice", methods=["GET", "POST"])
def voice_entry():
    call_sid = request.values.get("CallSid") or str(uuid.uuid4())
    reset_session(call_sid)

    ai = next_turn(call_sid, None)
    audio_path = tts_to_mp3(ai["say"], dest_dir=AUDIO_DIR)
    audio_url = request.url_root.rstrip("/") + "/audio/" + os.path.basename(audio_path)

    if ai.get("end_call"):
        return twiml_play_and_hangup(audio_url)
    return twiml_play_and_gather(audio_url)

@app.post("/process")
def process_turn():
    call_sid = request.values.get("CallSid")
    user_text = request.values.get("SpeechResult", "") or ""

    ai = next_turn(call_sid, user_text)

    # Fire printer best-effort; don’t block the call
    _ = print_order_if_needed(ai)

    audio_path = tts_to_mp3(ai["say"], dest_dir=AUDIO_DIR)
    audio_url = request.url_root.rstrip("/") + "/audio/" + os.path.basename(audio_path)

    if ai.get("end_call"):
        return twiml_play_and_hangup(audio_url)
    return twiml_play_and_gather(audio_url)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), debug=True)
