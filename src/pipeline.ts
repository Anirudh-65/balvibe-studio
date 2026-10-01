import "dotenv/config";
import { spawn } from "node:child_process";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { createInterface } from "node:readline/promises";
import { stdin, stdout } from "node:process";
import { fileURLToPath } from "node:url";
import { GroqScriptGenerator } from "./providers/groqScriptGenerator";
import { AgeBandSchema, type HindiStoryline } from "./types";
import { assertDurationSeconds } from "./scriptPipeline";
import { translateStorylineToHindi } from "./sarvamTranslation";

function option(args: string[], name: string, fallback?: string): string | undefined {
  const index = args.indexOf(name);
  return index < 0 ? fallback : args[index + 1];
}

function runPython(script: string, input: string, output: string): Promise<void> {
  const command = process.env.PYTHON_COMMAND || (process.platform === "win32" ? "python" : "python3");
  return new Promise((resolve, reject) => {
    const child = spawn(command, [script, input, output], { stdio: "inherit", env: process.env });
    child.once("error", reject);
    child.once("close", (code) => code === 0 ? resolve() : reject(new Error(`Azure voiceover exited with status ${code}.`)));
  });
}

async function confirmApproval(approvedByFlag: boolean): Promise<boolean> {
  if (approvedByFlag) {
    console.log("Researcher approval received via --approve.");
    return true;
  }
  const terminal = createInterface({ input: stdin, output: stdout });
  try {
    const answer = await terminal.question("Review the English storyline above. Continue to Hindi translation and Azure voice generation? [y/N] ");
    return answer.trim().toLowerCase() === "y" || answer.trim().toLowerCase() === "yes";
  } finally {
    terminal.close();
  }
}

async function main(): Promise<void> {
  const args = process.argv.slice(2);
  const instruction = option(args, "--instruction");
  if (!instruction) {
    throw new Error('Usage: npm run pipeline -- --instruction "..." --age 6-8 --duration 300');
  }
  const ageResult = AgeBandSchema.safeParse(option(args, "--age", "6-8"));
  if (!ageResult.success) throw new Error("--age must be one of: 4-5, 6-8, 9-11.");
  const duration = assertDurationSeconds(Number(option(args, "--duration", "300")));
  const outputDir = option(args, "--out-dir", `output/run-${new Date().toISOString().replace(/[:.]/g, "-")}`)!;
  await mkdir(outputDir, { recursive: true });

  console.log(`Creating ${ageResult.data} English storyline with Groq...`);
  const englishStoryline = await new GroqScriptGenerator().generateScript(instruction, ageResult.data, duration);
  const englishPath = `${outputDir}/english-storyline.json`;
  await writeFile(englishPath, JSON.stringify(englishStoryline, null, 2), "utf8");
  console.log(`\nValidated English storyline saved to ${englishPath}\n`);
  console.log(JSON.stringify(englishStoryline, null, 2));

  if (!await confirmApproval(args.includes("--approve"))) {
    console.log(`Stopped before translation/TTS. English draft remains at ${englishPath}.`);
    return;
  }

  const hindiStoryline = await translateStorylineToHindi(englishStoryline);
  const hindiPath = `${outputDir}/hindi-storyline.json`;
  await writeFile(hindiPath, JSON.stringify(hindiStoryline, null, 2), "utf8");
  console.log(`Hindi translation saved to ${hindiPath}`);

  const audioDir = `${outputDir}/audio`;
  const renderer = fileURLToPath(new URL("../voiceover/render_scene_audio.py", import.meta.url));
  await runPython(renderer, hindiPath, audioDir);
  const audioMetadata = JSON.parse(await readFile(`${audioDir}/audio-metadata.json`, "utf8")) as Array<{
    sceneOrder: number;
    audioFile: string;
    audioDurationMs: number;
  }>;
  const metadataByScene = new Map(audioMetadata.map((item) => [item.sceneOrder, item]));
  const result: HindiStoryline & {
    approvedByResearcher: boolean;
    scenes: Array<HindiStoryline["scenes"][number] & { audioFile: string; audioDurationMs: number }>;
  } = {
    ...hindiStoryline,
    scenes: hindiStoryline.scenes.map((scene) => {
      const audio = metadataByScene.get(scene.sceneOrder);
      if (!audio) throw new Error(`Audio metadata missing for scene ${scene.sceneOrder}.`);
      return { ...scene, audioFile: audio.audioFile, audioDurationMs: audio.audioDurationMs };
    }),
    approvedByResearcher: true,
  };
  const resultPath = `${outputDir}/pipeline-result.json`;
  await writeFile(resultPath, JSON.stringify(result, null, 2), "utf8");
  console.log(`\nPipeline complete. Hindi voiceover and metadata: ${resultPath}`);
}

main().catch((error: unknown) => {
  console.error("Pipeline failed:", error instanceof Error ? error.message : error);
  process.exitCode = 1;
});