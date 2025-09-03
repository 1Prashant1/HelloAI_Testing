import os, uuid
from openai import OpenAI

def ensure_audio_folder(path: str):
    os.makedirs(path, exist_ok=True)

def _write_silent_mp3(path: str):
    # 1s tiny silent MP3 so Twilio <Play> never fails
    SILENT = bytes.fromhex(
        "4944330300000000000f544954320000000000035465"
        "73740000504f5320000000000000fffb904400000000"
        "00000000000000000000000000000000000000000000"
    )
    with open(path, "wb") as f:
        f.write(SILENT)

def tts_to_mp3(text: str, dest_dir: str) -> str:
    os.makedirs(dest_dir, exist_ok=True)
    out_path = os.path.join(dest_dir, f"{uuid.uuid4().hex}.mp3")
    try:
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("Missing OPENAI_API_KEY")
        client = OpenAI(api_key=key)
        with client.audio.speech.with_streaming_response.create(
            model=os.environ.get("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"),
            voice=os.environ.get("OPENAI_TTS_VOICE", "alloy"),
            input=text
        ) as r:
            r.stream_to_file(out_path)
        return out_path
    except Exception:
        _write_silent_mp3(out_path)
        return out_path
