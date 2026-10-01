import getpass
import html
import json
import os
import re
import sys
import wave
from pathlib import Path

PAUSE_RE = re.compile(r"\[PAUSE(?:\s+(\d+(?:\.\d+)?)\s*(?:seconds?|s)?)?\]", re.IGNORECASE)


def to_ssml(text: str) -> str:
    parts = []
    cursor = 0
    for match in PAUSE_RE.finditer(text):
        spoken = text[cursor:match.start()].strip()
        if spoken:
            parts.append(html.escape(spoken))
        seconds = float(match.group(1) or 1)
        milliseconds = max(100, round(seconds * 1000))
        parts.append(f'<break time="{milliseconds}ms"/>')
        cursor = match.end()
    tail = text[cursor:].strip()
    if tail:
        parts.append(html.escape(tail))
    return (
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
        'xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="hi-IN">'
        '<voice name="hi-IN-SwaraNeural"><mstts:express-as style="cheerful">'
        '<prosody rate="-5%">' + " ".join(parts) +
        "</prosody></mstts:express-as></voice></speak>"
    )


def wav_duration_ms(path: Path) -> int:
    with wave.open(str(path), "rb") as audio:
        return round(audio.getnframes() * 1000 / audio.getframerate())


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: render_scene_audio.py <translated-storyline.json> <audio-output-dir>")
        return 2
    try:
        import azure.cognitiveservices.speech as speechsdk
    except ImportError:
        print("Azure Speech SDK missing. Install voiceover/requirements.txt", file=sys.stderr)
        return 1

    input_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    output_dir.mkdir(parents=True, exist_ok=True)
    data = json.loads(input_path.read_text(encoding="utf-8"))
    key = os.environ.get("AZURE_SPEECH_KEY") or getpass.getpass("Azure Speech key: ").strip()
    if not key:
        print("No Azure Speech key supplied.", file=sys.stderr)
        return 1
    region = os.environ.get("AZURE_SPEECH_REGION", "centralindia")
    config = speechsdk.SpeechConfig(subscription=key, region=region)
    config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm
    )

    results = []
    for scene in data["scenes"]:
        order = int(scene["sceneOrder"])
        text = scene.get("translatedText", "").strip()
        if not text:
            raise ValueError(f"Scene {order} has no translatedText.")
        destination = output_dir / f"scene_{order:03d}_hi.wav"
        audio_config = speechsdk.audio.AudioOutputConfig(filename=str(destination))
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=config, audio_config=audio_config)
        print(f"Synthesizing Hindi scene {order}/{len(data['scenes'])}...")
        result = synthesizer.speak_ssml_async(to_ssml(text)).get()
        if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
            details = speechsdk.SpeechSynthesisCancellationDetails.from_result(result)
            raise RuntimeError(f"Scene {order} failed ({details.reason}): {details.error_details}")
        results.append({
            "sceneOrder": order,
            "audioFile": str(destination.resolve()),
            "audioDurationMs": wav_duration_ms(destination),
        })

    (output_dir / "audio-metadata.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Created {len(results)} Hindi WAV scene files in {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())