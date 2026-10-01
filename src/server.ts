/**
 * BalVibe Pipeline – Express API Server
 *
 * Wraps the existing CLI pipeline into HTTP endpoints so the
 * frontend can drive each step independently.
 *
 * Endpoints:
 *   POST /api/generate-script     → Groq English storyline
 *   POST /api/save-script         → Save edited English storyline
 *   POST /api/translate           → Sarvam translation (any supported lang)
 *   POST /api/voiceover           → Sarvam Bulbul v3 TTS
 *   GET  /api/audio/:runId/:file  → Serve generated WAV files
 *   GET  /api/runs                → List all pipeline runs
 */

import "dotenv/config";
import express from "express";
import cors from "cors";
import { spawn } from "node:child_process";
import { mkdir, readFile, writeFile, readdir, stat } from "node:fs/promises";
import { existsSync } from "node:fs";
import { resolve, join } from "node:path";
import { fileURLToPath } from "node:url";
import { GroqScriptGenerator } from "./providers/groqScriptGenerator.js";
import { AgeBandSchema, type Storyline, type HindiStoryline } from "./types.js";
import { assertDurationSeconds } from "./scriptPipeline.js";

const __dirname = fileURLToPath(new URL(".", import.meta.url));
const OUTPUT_ROOT = resolve(__dirname, "..", "output");

const app = express();
app.use(cors());
app.use(express.json({ limit: "5mb" }));

// ─── Serve the frontend ────────────────────────────────────────────────
const frontendDir = resolve(__dirname, "..", "frontend");
app.use(express.static(frontendDir));

// ─── Helper: translate a single text chunk via Sarvam ──────────────────
const TRANSLATE_URL = "https://api.sarvam.ai/translate";
const PAUSE_PATTERN = /(\[PAUSE(?:\s+\d+(?:\.\d+)?\s*(?:seconds?|s)?)?\])/gi;
const MAX_INPUT_CHARS = 1800;

function splitForSarvam(text: string, maxLength = MAX_INPUT_CHARS): string[] {
  const chunks: string[] = [];
  let remaining = text.trim();
  while (remaining.length > maxLength) {
    let splitAt = remaining.lastIndexOf(".", maxLength);
    if (splitAt < Math.floor(maxLength * 0.55)) splitAt = remaining.lastIndexOf(" ", maxLength);
    if (splitAt < 1) splitAt = maxLength;
    chunks.push(remaining.slice(0, splitAt + (remaining[splitAt] === "." ? 1 : 0)).trim());
    remaining = remaining.slice(splitAt + (remaining[splitAt] === "." ? 1 : 0)).trim();
  }
  if (remaining) chunks.push(remaining);
  return chunks;
}

async function translateText(text: string, apiKey: string, targetLang: string): Promise<string> {
  const chunks = splitForSarvam(text);
  const translated: string[] = [];
  for (const input of chunks) {
    const response = await fetch(TRANSLATE_URL, {
      method: "POST",
      headers: { "api-subscription-key": apiKey, "content-type": "application/json" },
      body: JSON.stringify({
        input,
        source_language_code: "en-IN",
        target_language_code: targetLang,
        model: "sarvam-translate:v1",
        mode: "formal",
      }),
    });
    const body = await response.json() as { translated_text?: string; error?: { message?: string } };
    if (!response.ok) {
      throw new Error(`Sarvam translation failed (${response.status}): ${body.error?.message || JSON.stringify(body)}`);
    }
    if (!body.translated_text) throw new Error("Sarvam returned an empty translated_text field.");
    translated.push(body.translated_text);
  }
  return translated.join(" ");
}

async function translateKeepingPauses(text: string, apiKey: string, targetLang: string): Promise<string> {
  // If target is English, no translation needed
  if (targetLang === "en-IN" || targetLang === "en-US") return text;

  const output: string[] = [];
  let previousIndex = 0;
  for (const match of text.matchAll(PAUSE_PATTERN)) {
    const index = match.index ?? 0;
    const before = text.slice(previousIndex, index).trim();
    if (before) output.push(await translateText(before, apiKey, targetLang));
    output.push(match[0]);
    previousIndex = index + match[0].length;
  }
  const after = text.slice(previousIndex).trim();
  if (after) output.push(await translateText(after, apiKey, targetLang));
  return output.join(" ");
}

// ─── Language mapping ──────────────────────────────────────────────────
const LANG_MAP: Record<string, { sarvamTranslateCode: string; sarvamTTSCode: string; label: string }> = {
  "en": { sarvamTranslateCode: "en-IN", sarvamTTSCode: "en-IN", label: "English" },
  "hi": { sarvamTranslateCode: "hi-IN", sarvamTTSCode: "hi-IN", label: "Hindi" },
  "bn": { sarvamTranslateCode: "bn-IN", sarvamTTSCode: "bn-IN", label: "Bengali" },
  "gu": { sarvamTranslateCode: "gu-IN", sarvamTTSCode: "gu-IN", label: "Gujarati" },
  "kn": { sarvamTranslateCode: "kn-IN", sarvamTTSCode: "kn-IN", label: "Kannada" },
  "ml": { sarvamTranslateCode: "ml-IN", sarvamTTSCode: "ml-IN", label: "Malayalam" },
  "mr": { sarvamTranslateCode: "mr-IN", sarvamTTSCode: "mr-IN", label: "Marathi" },
  "od": { sarvamTranslateCode: "od-IN", sarvamTTSCode: "od-IN", label: "Odia" },
  "pa": { sarvamTranslateCode: "pa-IN", sarvamTTSCode: "pa-IN", label: "Punjabi" },
  "ta": { sarvamTranslateCode: "ta-IN", sarvamTTSCode: "ta-IN", label: "Tamil" },
  "te": { sarvamTranslateCode: "te-IN", sarvamTTSCode: "te-IN", label: "Telugu" }
};

// ─── 1. Generate English Script ────────────────────────────────────────
app.post("/api/generate-script", async (req, res) => {
  try {
    const { instruction, age, duration } = req.body as {
      instruction: string; age: string; duration: number;
    };
    if (!instruction?.trim()) {
      res.status(400).json({ error: "instruction is required." });
      return;
    }
    const ageResult = AgeBandSchema.safeParse(age || "6-8");
    if (!ageResult.success) {
      res.status(400).json({ error: "age must be one of: 4-5, 6-8, 9-11." });
      return;
    }
    const dur = assertDurationSeconds(duration || 60);

    const runId = `run-${new Date().toISOString().replace(/[:.]/g, "-")}`;
    const outputDir = join(OUTPUT_ROOT, runId);
    await mkdir(outputDir, { recursive: true });

    console.log(`[API] Generating ${ageResult.data} English storyline (${dur}s)...`);
    const storyline = await new GroqScriptGenerator().generateScript(instruction, ageResult.data, dur);
    const filePath = join(outputDir, "english-storyline.json");
    await writeFile(filePath, JSON.stringify(storyline, null, 2), "utf8");

    res.json({ runId, storyline });
  } catch (error: any) {
    console.error("[API] generate-script error:", error);
    res.status(500).json({ error: error.message || "Script generation failed." });
  }
});

// ─── 2. Save edited script ────────────────────────────────────────────
app.post("/api/save-script", async (req, res) => {
  try {
    const { runId, storyline } = req.body as { runId: string; storyline: Storyline };
    if (!runId || !storyline) {
      res.status(400).json({ error: "runId and storyline are required." });
      return;
    }
    const outputDir = join(OUTPUT_ROOT, runId);
    await mkdir(outputDir, { recursive: true });
    const filePath = join(outputDir, "english-storyline.json");
    await writeFile(filePath, JSON.stringify(storyline, null, 2), "utf8");
    res.json({ success: true, message: "English storyline saved." });
  } catch (error: any) {
    console.error("[API] save-script error:", error);
    res.status(500).json({ error: error.message || "Save failed." });
  }
});

// ─── 3. Translate ──────────────────────────────────────────────────────
app.post("/api/translate", async (req, res) => {
  try {
    const { runId, storyline, language } = req.body as {
      runId: string; storyline: Storyline; language: string;
    };
    if (!runId || !storyline || !language) {
      res.status(400).json({ error: "runId, storyline, and language are required." });
      return;
    }
    const langConfig = LANG_MAP[language];
    if (!langConfig) {
      res.status(400).json({ error: `Unsupported language: ${language}` });
      return;
    }
    const apiKey = process.env.SARVAM_API_KEY;
    if (!apiKey) {
      res.status(500).json({ error: "SARVAM_API_KEY is missing from server .env." });
      return;
    }
    const outputDir = join(OUTPUT_ROOT, runId);
    await mkdir(outputDir, { recursive: true });

    console.log(`[API] Translating to ${langConfig.label}...`);
    const scenes: Array<any> = [];
    for (let i = 0; i < storyline.scenes.length; i++) {
      const scene = storyline.scenes[i];
      let translatedText: string;
      if (language === "en") {
        translatedText = scene.audioScript;
      } else {
        translatedText = await translateKeepingPauses(scene.audioScript, apiKey, langConfig.sarvamTranslateCode);
      }
      scenes.push({ ...scene, translatedText });
      console.log(`  Translated scene ${i + 1}/${storyline.scenes.length}`);
    }

    const translatedStoryline = {
      ...storyline,
      language: langConfig.sarvamTranslateCode,
      scenes,
    };

    const filePath = join(outputDir, `${language}-storyline.json`);
    await writeFile(filePath, JSON.stringify(translatedStoryline, null, 2), "utf8");

    res.json({ runId, translatedStoryline });
  } catch (error: any) {
    console.error("[API] translate error:", error);
    res.status(500).json({ error: error.message || "Translation failed." });
  }
});

// ─── 4. Voiceover (Sarvam Bulbul v3) ──────────────────────────────────
function runPython(script: string, args: string[]): Promise<string> {
  const command = process.env.PYTHON_COMMAND || (process.platform === "win32" ? "python" : "python3");
  return new Promise((resolve, reject) => {
    let stdout = "";
    let stderr = "";
    const child = spawn(command, [script, ...args], {
      env: { ...process.env },
      cwd: join(__dirname, ".."),
    });
    child.stdout?.on("data", (d) => { stdout += d.toString(); });
    child.stderr?.on("data", (d) => { stderr += d.toString(); });
    child.once("error", reject);
    child.once("close", (code) => {
      if (code === 0) resolve(stdout);
      else reject(new Error(`Python exited with ${code}. stderr: ${stderr}\nstdout: ${stdout}`));
    });
  });
}

app.post("/api/voiceover", async (req, res) => {
  try {
    const { runId, translatedStoryline, speaker, language } = req.body as {
      runId: string;
      translatedStoryline: any;
      speaker: string;
      language: string;
    };
    if (!runId || !translatedStoryline) {
      res.status(400).json({ error: "runId and translatedStoryline are required." });
      return;
    }
    const langConfig = LANG_MAP[language || "hi"];
    if (!langConfig) {
      res.status(400).json({ error: `Unsupported language: ${language}` });
      return;
    }
    const outputDir = join(OUTPUT_ROOT, runId);
    await mkdir(outputDir, { recursive: true });

    // Write the translated storyline to disk for the Python script
    const translatedPath = join(outputDir, `${language}-storyline.json`);
    await writeFile(translatedPath, JSON.stringify(translatedStoryline, null, 2), "utf8");

    const audioDir = join(outputDir, "audio");
    const rendererPath = resolve(__dirname, "..", "voiceover", "render_sarvam_audio.py");

    console.log(`[API] Starting Sarvam voiceover (${speaker}, ${langConfig.sarvamTTSCode})...`);
    await runPython(rendererPath, [
      translatedPath,
      audioDir,
      speaker || "shubh",
      langConfig.sarvamTTSCode,
    ]);

    const metadataPath = join(audioDir, "audio-metadata.json");
    const audioMetadata = JSON.parse(await readFile(metadataPath, "utf8")) as Array<{
      sceneOrder: number; audioFile: string; audioDurationMs: number;
    }>;

    // Build result with relative audio URLs
    const metadataByScene = new Map(audioMetadata.map((item) => [item.sceneOrder, item]));
    const resultScenes = translatedStoryline.scenes.map((scene: any) => {
      const audio = metadataByScene.get(scene.sceneOrder);
      if (!audio) throw new Error(`Audio metadata missing for scene ${scene.sceneOrder}.`);
      const fileName = audio.audioFile.split(/[/\\]/).pop();
      return {
        ...scene,
        audioFile: `/api/audio/${runId}/${fileName}`,
        audioDurationMs: audio.audioDurationMs,
      };
    });
    
    // Retrieve the combined audio file
    let combinedAudio = null;
    const combinedData = metadataByScene.get(0);
    if (combinedData) {
      combinedAudio = `/api/audio/${runId}/${combinedData.audioFile.split(/[/\\]/).pop()}`;
    }

    const pipelineResult = {
      ...translatedStoryline,
      scenes: resultScenes,
      combinedAudio,
      approvedByResearcher: true,
    };

    const resultPath = join(outputDir, "pipeline-result.json");
    await writeFile(resultPath, JSON.stringify(pipelineResult, null, 2), "utf8");

    res.json({ runId, pipelineResult });
  } catch (error: any) {
    console.error("[API] voiceover error:", error);
    res.status(500).json({ error: error.message || "Voiceover generation failed." });
  }
});

// ─── 5. Serve audio files ──────────────────────────────────────────────
app.get("/api/audio/:runId/:file", async (req, res) => {
  const filePath = join(OUTPUT_ROOT, req.params.runId, "audio", req.params.file);
  if (!existsSync(filePath)) {
    res.status(404).json({ error: "Audio file not found." });
    return;
  }
  res.sendFile(filePath);
});

// ─── 6. List runs ─────────────────────────────────────────────────────
app.get("/api/runs", async (_req, res) => {
  try {
    if (!existsSync(OUTPUT_ROOT)) {
      res.json({ runs: [] });
      return;
    }
    const entries = await readdir(OUTPUT_ROOT);
    const runs = entries.filter((e) => e.startsWith("run-")).sort().reverse();
    res.json({ runs });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// ─── Fallback: serve index.html for SPA ─────────────────────────────
app.get("*", (_req, res) => {
  res.sendFile(join(frontendDir, "index.html"));
});

// ─── Start ──────────────────────────────────────────────────────────────
const PORT = Number(process.env.PORT) || 3000;
app.listen(PORT, () => {
  console.log(`\n  🚀 BalVibe Pipeline Server running at http://localhost:${PORT}\n`);
});
