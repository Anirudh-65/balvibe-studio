import type { HindiStoryline, Scene, Storyline } from "./types";

const TRANSLATE_URL = "https://api.sarvam.ai/translate";
const MAX_INPUT_CHARS = 1800;
const PAUSE_PATTERN = /(\[PAUSE(?:\s+\d+(?:\.\d+)?\s*(?:seconds?|s)?)?\])/gi;

export function splitForSarvam(text: string, maxLength = MAX_INPUT_CHARS): string[] {
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

async function translateText(text: string, apiKey: string): Promise<string> {
  const chunks = splitForSarvam(text);
  const translated: string[] = [];
  for (const input of chunks) {
    const response = await fetch(TRANSLATE_URL, {
      method: "POST",
      headers: { "api-subscription-key": apiKey, "content-type": "application/json" },
      body: JSON.stringify({
        input,
        source_language_code: "en-IN",
        target_language_code: "hi-IN",
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

async function translateKeepingPauses(text: string, apiKey: string): Promise<string> {
  const output: string[] = [];
  let previousIndex = 0;
  for (const match of text.matchAll(PAUSE_PATTERN)) {
    const index = match.index ?? 0;
    const before = text.slice(previousIndex, index).trim();
    if (before) output.push(await translateText(before, apiKey));
    output.push(match[0]);
    previousIndex = index + match[0].length;
  }
  const after = text.slice(previousIndex).trim();
  if (after) output.push(await translateText(after, apiKey));
  return output.join(" ");
}

export async function translateStorylineToHindi(storyline: Storyline): Promise<HindiStoryline> {
  const apiKey = process.env.SARVAM_API_KEY;
  if (!apiKey) throw new Error("SARVAM_API_KEY is missing. Add it to the local .env file.");
  const scenes: Array<Scene & { translatedText: string }> = [];
  for (const scene of storyline.scenes) {
    const translatedText = await translateKeepingPauses(scene.audioScript, apiKey);
    scenes.push({ ...scene, translatedText });
    console.log(`Translated scene ${scene.sceneOrder}/${storyline.scenes.length}`);
  }
  return { ...storyline, language: "hi-IN", scenes };
}