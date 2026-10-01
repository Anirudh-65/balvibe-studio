# Azure Hindi Voiceover

`render_scene_audio.py` reads a translated storyline JSON with `scenes[*].translatedText`, writes one `scene_NNN_hi.wav` per scene, and records measured PCM duration in `audio-metadata.json`. It uses the India Hindi voice `hi-IN-SwaraNeural`, a cheerful SSML style and a 5% slower speaking rate.

Install the SDK from this folder with `py -3 -m pip install -r requirements.txt`. The integrated command invokes this script after translation. Set `AZURE_SPEECH_KEY` and optionally `AZURE_SPEECH_REGION`; if the key is missing, it is requested securely in the terminal. The key is never written to an output file.