# BalVibe Studio

BalVibe Studio is a researcher-facing MVP for creating educational experiment
videos through the voiceover and timing-dataset stage. Researchers provide an
experiment protocol, review and approve a gamified storyline and its script,
then generate a translation, scene audio, and timing-ready dataset.

## Current workflow

```text
Researcher instructions and optional story direction
  -> generated storyline flow
  -> researcher review, edit, and approval
  -> script and dialogue generation from the approved flow
  -> researcher review, edit, and approval
  -> translation with Sarvam or BHASHINI / ULCA
  -> scene and combined WAV voiceover with Azure Speech or Sarvam Bulbul v3
  -> timing-ready JSON dataset
  -> continuous scene visuals & Gemini Imagen prompts
  -> Remotion descriptor & FFmpeg deterministic MP4 video composition
```

The storyline and script stages carry one setting and the experiment task
through the scenes. The prompts guide the model to preserve that continuity,
and the generated scene records carry the approved setting. Researchers should
still review the generated narration and visuals before using them in a study.

## Features

- Groq-powered storyline and script generation, with researcher approval gates.
- Editable storyline flow and per-scene narration.
- Translation with Sarvam Translate or BHASHINI / ULCA.
- Voiceover with Microsoft Azure Speech or Sarvam Bulbul v3.
- Scene visual generation with 3D animation assets and Gemini Imagen prompt synthesis.
- Composition & Muxing with Remotion + FFmpeg: sequences scene images, synced subtitles, and narration audio into an MP4 video.
- Media Storage Local Filesystem Abstraction: clean interface for local campus disk storage and future S3/MinIO deployment.
- Interactive in-browser video player with MP4 and Remotion JSON export.
- SQLite persistence for runs, media, and scene metadata.

## Requirements

- Python 3.11 or newer.
- API credentials for the live providers you intend to use. Demo mode requires
  no provider credentials.

## Run locally

From the repository root, create and activate a virtual environment, then
install the dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On macOS or Linux, activate with:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Create a `.env` file in the repository root. For live mode, add the credentials
for the providers you will use:

```dotenv
BALVIBE_DEMO_MODE=false
BALVIBE_DATA_DIR=./data
GROQ_API_KEY=replace-with-your-groq-key
GROQ_MODEL=qwen/qwen3.8-27b

SARVAM_API_KEY=replace-with-your-sarvam-key
BHASHINI_USER_ID=replace-with-your-bhashini-user-id
BHASHINI_API_KEY=replace-with-your-bhashini-key
AZURE_SPEECH_KEY=replace-with-your-azure-speech-key
AZURE_SPEECH_REGION=centralindia
```

Only credentials for providers you use are needed. Do not commit `.env`, put
provider keys in frontend code, or share keys in screenshots or logs.

Start the app:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>. The API health endpoint is
<http://127.0.0.1:8000/api/health>.

### Demo mode

To run the UI and deterministic local pipeline without provider calls, set:

```dotenv
BALVIBE_DEMO_MODE=true
```

Demo mode produces synthetic audio for testing the workflow; it is not a
substitute for live translation or speech synthesis. Restart the server after
changing environment variables.

## Deploy on Render

The repository includes a Render Blueprint in [`render.yaml`](render.yaml).
Connect the repository in Render and create the Blueprint service, or configure
a Python web service with:

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Health check path:** `/api/health`

Set the provider credentials as Render environment variables. Keep
`BALVIBE_DEMO_MODE` set to `false` for live provider calls. The included
Blueprint uses `/tmp/balvibe` for data on the free web-service plan; its database
and generated files are ephemeral and may be lost when the service restarts.
Do not rely on that storage for durable research data.

## Data layout

`BALVIBE_DATA_DIR` contains the SQLite database and generated run artifacts:

```text
data/
  balvibe.db
  runs/
    run-xxxxxxxxxxxx/
      dataset_azure.json
      dataset_sarvam.json
      audio/
        azure/
          scene_001_hi_azure.wav
          combined_hi_azure.wav
        sarvam/
          scene_001_hi_sarvam.wav
          combined_hi_sarvam.wav
```

Files are created as each provider is used. The dataset records each scene's
audio file, measured duration, timeline positions, and frame positions.

## API overview

The interactive API documentation is available at `/docs` while the service is
running.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Health and provider-configuration status (does not test API credentials with the provider) |
| `GET` | `/api/config` | Available languages, translation providers, and voices |
| `GET` | `/api/runs` | List recent runs |
| `POST` | `/api/generate-storyline` | Generate a storyline-flow draft |
| `PUT` | `/api/runs/{id}/storyline-flow` | Save storyline-flow edits |
| `POST` | `/api/runs/{id}/approve-storyline` | Approve and lock the storyline flow |
| `POST` | `/api/runs/{id}/unlock-storyline` | Unlock the storyline flow for edits |
| `POST` | `/api/runs/{id}/generate-script` | Generate script and dialogues from the approved flow |
| `PUT` | `/api/runs/{id}/storyline` | Save script edits |
| `POST` | `/api/runs/{id}/approve` | Approve and lock the script |
| `POST` | `/api/runs/{id}/unlock-script` | Unlock the script for edits |
| `POST` | `/api/runs/{id}/translate` | Translate an approved script |
| `POST` | `/api/runs/{id}/voiceover` | Synthesize scene audio and create a timing dataset |
| `GET` | `/api/runs/{id}` | Retrieve a run |
| `GET` | `/api/runs/{id}/dataset` | Download the generated dataset |
| `GET` | `/api/runs/{id}/audio/{provider}/{filename}` | Retrieve a generated WAV file |

The legacy `POST /api/generate-script` endpoint remains available for callers
that need to create a storyline and script in one request.

## Test

Run the automated tests from the repository root:

```bash
python -m unittest discover -s tests -v
```

The tests use deterministic demo settings and cover storyline validation,
approval gates, translation-provider behavior, both TTS output contracts,
timing continuity, and persistence. They do not verify that live external API
credentials work.

## Provider notes

- Groq generates structured JSON using the configured `GROQ_MODEL`.
- Sarvam translation uses `sarvam-translate:v1`; pause markers are preserved
  around translated text.
- BHASHINI uses the ULCA Pipeline Config and Dhruva Pipeline Compute APIs.
- Azure speech uses 24 kHz, 16-bit mono PCM WAV output and SSML breaks for
  `[PAUSE ...]` markers.
- Sarvam Bulbul v3 uses native WAV output; pause markers are implemented by
  inserting PCM silence between synthesized segments.
- Supported Azure voices and language options are returned by `/api/config`.

## Scope and limitations

BalVibe Studio supports the full demonstration path through scene images,
motion keyframes, and deterministic MP4 video rendering. Generated content
still requires researcher review, including checking that narration stays
faithful to the approved protocol and storyline. The current SQLite and
local-file storage setup is intended for development and prototyping, not
durable multi-user production storage. The free Render deployment has less
memory than a local development machine and is intended for the loaded sample;
long or high-resolution renders may exceed its memory limit.
