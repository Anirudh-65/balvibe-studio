# BalVibe Integrated Text-to-Voice Pipeline

This standalone Progress 2 project runs the pipeline through Hindi voiceover:

```text
Experiment instruction -> Groq storyline -> researcher approval -> Sarvam English-to-Hindi -> Azure Hindi WAVs
```

Only the Groq script provider is included. The default Groq-hosted model is `qwen/qwen3.8-27b`; Ollama and model-comparison experiments are not part of this submission project. The approval gate occurs before translation and speech API requests. The generated English script is shown and saved first.

## Requirements

- Node.js 20 or newer and npm
- Python 3.10 or newer
- A Groq API key, Sarvam API key, and Azure Speech key for a live end-to-end run
- Azure Speech resource region (defaults to `centralindia`)

## Setup on Windows

Open PowerShell in this folder:

```powershell
npm install
Copy-Item .env.example .env
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r voiceover\requirements.txt
```

Put `GROQ_API_KEY`, `SARVAM_API_KEY`, and `AZURE_SPEECH_KEY` into the local `.env` file. Set `AZURE_SPEECH_REGION` if the Speech resource uses a region other than `centralindia`. `.env` is excluded from Git. Do not paste keys into source code, reports, or committed files.

If the Azure key is not in `.env`, the voiceover stage asks for it through a hidden terminal prompt. If the Python launcher command differs on your machine, set `PYTHON_COMMAND` in `.env`, for example `python`.

## Run the Pipeline

```powershell
npm run pipeline -- --instruction "Show six numbers for exactly 2 seconds. Hide one number and ask the child to identify it. Include one practice round and three formal trials, then close." --age 9-11 --duration 300
```

Supported age bands are `4-5`, `6-8`, and `9-11`. Duration must be an integer from 60 to 3600 seconds. The same sample instruction is in `examples/sample-instruction.txt`. After Groq generates the English storyline, inspect it in the terminal and answer `y` at the approval prompt to continue. Any other answer stops before Sarvam and Azure are called; the English JSON remains saved.

For an explicitly pre-reviewed run, add `--approve`. You may set a destination with `--out-dir output/my-experiment`.

## Outputs

Each run writes to its own output directory:

```text
output/run-<timestamp>/
  english-storyline.json
  hindi-storyline.json
  audio/
    scene_001_hi.wav
    scene_002_hi.wav
    audio-metadata.json
  pipeline-result.json
```

`pipeline-result.json` contains the Hindi scene text, original English text, audio path, measured `audioDurationMs`, scene timing, and researcher approval status. WAV duration is measured from the generated PCM file, not estimated from text.

## Offline Checks

These checks do not require API keys and do not call paid or metered services:

```powershell
npm run typecheck
npm test
```

The tests cover storyline schema validation, target-duration reconciliation, one-character consistency, rejection of human character types, and splitting long Sarvam inputs. They do not prove live API credentials, current account quota, translation quality, or Azure voice availability.

## API References

- Groq API: https://console.groq.com/docs
- Sarvam Text Translation: https://docs.sarvam.ai/api-reference/text/translate-text
- Azure Speech SDK: https://learn.microsoft.com/azure/ai-services/speech-service/