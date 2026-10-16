"""
Render scene audio using Sarvam AI Bulbul v3 TTS.
Replaces the Azure Speech SDK renderer.

Usage:
    python render_sarvam_audio.py <translated-storyline.json> <audio-output-dir> [speaker] [language_code]

Speaker defaults to "shubh" (male). Pass "ritu" for female, etc.
Language defaults to the storyline's language field, or "hi-IN".
"""

import base64
import json
import os
import re
import struct
import sys
import wave
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

TTS_URL = "https://api.sarvam.ai/text-to-speech"
PAUSE_RE = re.compile(
    r"\[PAUSE(?:\s+(\d+(?:\.\d+)?)\s*(?:seconds?|s)?)?\]", re.IGNORECASE
)
MAX_TTS_CHARS = 2400  # Sarvam limit is 2500; keep a small margin


def make_silence_wav(duration_seconds: float, sample_rate: int = 24000) -> bytes:
    """Generate raw WAV bytes of silence for a given duration."""
    num_samples = int(sample_rate * duration_seconds)
    # 16-bit mono PCM silence
    data = b"\x00\x00" * num_samples
    import io
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(data)
    return buf.getvalue()


def sarvam_tts(text: str, api_key: str, language_code: str, speaker: str) -> bytes:
    """Call Sarvam TTS and return decoded WAV bytes."""
    payload = json.dumps({
        "text": text,
        "language_code": language_code,
        "model": "bulbul:v3",
        "speaker": speaker,
        "sample_rate": 24000,
    }).encode("utf-8")

    req = Request(
        TTS_URL,
        data=payload,
        headers={
            "api-subscription-key": api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(req) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Sarvam TTS failed ({e.code}): {error_body}"
        ) from e

    audios = body.get("audios")
    if not audios or not audios[0]:
        raise RuntimeError("Sarvam TTS returned empty audio data.")

    return base64.b64decode(audios[0])


def split_text_for_tts(text: str, max_length: int = MAX_TTS_CHARS) -> list[str]:
    """Split long text into chunks that fit Sarvam's char limit."""
    chunks = []
    remaining = text.strip()
    while len(remaining) > max_length:
        split_at = remaining.rfind(".", 0, max_length)
        if split_at < max_length * 0.5:
            split_at = remaining.rfind(" ", 0, max_length)
        if split_at < 1:
            split_at = max_length
        chunks.append(remaining[:split_at + (1 if remaining[split_at] == "." else 0)].strip())
        remaining = remaining[split_at + (1 if remaining[split_at] == "." else 0):].strip()
    if remaining:
        chunks.append(remaining)
    return chunks


def extract_wav_pcm(wav_bytes: bytes) -> tuple[bytes, int, int, int]:
    """Extract raw PCM data, channels, sample width, and frame rate from WAV bytes."""
    import io
    buf = io.BytesIO(wav_bytes)
    with wave.open(buf, "rb") as wf:
        return wf.readframes(wf.getnframes()), wf.getnchannels(), wf.getsampwidth(), wf.getframerate()


def concatenate_wav_segments(segments: list[bytes]) -> bytes:
    """Concatenate multiple WAV byte segments into a single WAV."""
    if len(segments) == 1:
        return segments[0]

    all_pcm = []
    channels = sample_width = frame_rate = None
    for seg in segments:
        pcm, ch, sw, fr = extract_wav_pcm(seg)
        if channels is None:
            channels, sample_width, frame_rate = ch, sw, fr
        all_pcm.append(pcm)

    combined_pcm = b"".join(all_pcm)
    import io
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(frame_rate)
        wf.writeframes(combined_pcm)
    return buf.getvalue()


def render_scene_text(
    text: str, api_key: str, language_code: str, speaker: str
) -> bytes:
    """Render a single scene's text (with [PAUSE] markers) into a single WAV."""
    segments: list[bytes] = []
    cursor = 0

    for match in PAUSE_RE.finditer(text):
        before = text[cursor : match.start()].strip()
        if before:
            chunks = split_text_for_tts(before)
            for chunk in chunks:
                segments.append(sarvam_tts(chunk, api_key, language_code, speaker))

        pause_seconds = float(match.group(1) or 1)
        segments.append(make_silence_wav(pause_seconds))
        cursor = match.end()

    tail = text[cursor:].strip()
    if tail:
        chunks = split_text_for_tts(tail)
        for chunk in chunks:
            segments.append(sarvam_tts(chunk, api_key, language_code, speaker))

    if not segments:
        raise ValueError("No speakable text found in scene.")

    return concatenate_wav_segments(segments)


def wav_duration_ms(path: Path) -> int:
    with wave.open(str(path), "rb") as audio:
        return round(audio.getnframes() * 1000 / audio.getframerate())


def main() -> int:
    if len(sys.argv) < 3:
        print(
            "Usage: render_sarvam_audio.py <translated-storyline.json> "
            "<audio-output-dir> [speaker] [language_code]"
        )
        return 2

    input_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    speaker = sys.argv[3] if len(sys.argv) > 3 else "shubh"
    override_lang = sys.argv[4] if len(sys.argv) > 4 else None

    output_dir.mkdir(parents=True, exist_ok=True)
    data = json.loads(input_path.read_text(encoding="utf-8"))

    api_key = os.environ.get("SARVAM_API_KEY", "").strip()
    if not api_key:
        print("SARVAM_API_KEY is not set.", file=sys.stderr)
        return 1

    language_code = override_lang or data.get("language", "hi-IN")
    # Map language field values to Sarvam language codes
    lang_map = {
        "hi-IN": "hi-IN",
        "en-US": "en-IN",
        "en-IN": "en-IN",
        "gu-IN": "gu-IN",
    }
    language_code = lang_map.get(language_code, language_code)

    results = []
    all_segments = []
    total = len(data["scenes"])
    for scene in data["scenes"]:
        order = int(scene["sceneOrder"])
        text = scene.get("translatedText", "").strip()
        if not text:
            raise ValueError(f"Scene {order} has no translatedText.")

        lang_suffix = language_code.split("-")[0]
        destination = output_dir / f"scene_{order:03d}_{lang_suffix}.wav"

        print(f"Synthesizing scene {order}/{total} with Sarvam Bulbul v3 ({speaker})...")
        wav_data = render_scene_text(text, api_key, language_code, speaker)
        destination.write_bytes(wav_data)

        results.append({
            "sceneOrder": order,
            "audioFile": str(destination.resolve()),
            "audioDurationMs": wav_duration_ms(destination),
        })
        print(f"  -> {destination.name} ({results[-1]['audioDurationMs']}ms)")
        
        # Keep track of all segments to combine later
        all_segments.append(wav_data)

    # Combine all scenes into a single audio file
    if all_segments:
        combined_wav_data = concatenate_wav_segments(all_segments)
        combined_destination = output_dir / f"combined_storyline_{lang_suffix}.wav"
        combined_destination.write_bytes(combined_wav_data)
        print(f"\nCreated combined audio: {combined_destination.name}")
        results.append({
            "sceneOrder": 0, # Use 0 to denote the combined file
            "audioFile": str(combined_destination.resolve()),
            "audioDurationMs": wav_duration_ms(combined_destination),
        })

    meta_path = output_dir / "audio-metadata.json"
    meta_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nCreated {len(results)} WAV scene files in {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
