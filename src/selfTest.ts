import assert from "node:assert/strict";
import { generateTwoStageScript } from "./scriptPipeline";
import { splitForSarvam } from "./sarvamTranslation";
import { StorylineSchema } from "./types";

const instruction = "Show six numbers for exactly 2 seconds. Hide one number and ask the child to identify it. Include one practice round and three formal trials, then close.";
const story = await generateTwoStageScript(
  instruction,
  "6-8",
  120,
  async (_instruction, ageBand, duration) => ({
    ageBand,
    language: "en-US",
    targetDurationSeconds: duration,
    sections: [
      { sectionOrder: 1, title: "Welcome", purpose: "Explain the activity", durationSeconds: 30, requiredContent: "Introduce task" },
      { sectionOrder: 2, title: "Practice", purpose: "Practice once", durationSeconds: 30, requiredContent: ["Practice"] },
      { sectionOrder: 3, title: "Formal trials", purpose: "Complete trials", durationSeconds: 60, requiredContent: ["Three trials"] },
    ],
  }),
  async (_instruction, _age, section) => ({
    scenes: [{
      sceneOrder: 1,
      durationSeconds: section.durationSeconds,
      characterType: "robot",
      characterName: "Pico",
      characterState: "points at the numbers",
      visualAssetTag: "number_game",
      audioScript: `${section.title}. Look at the numbers. [PAUSE 2 seconds] Now tell me what is missing.`,
      sourceText: `${section.title}. Look at the numbers. [PAUSE 2 seconds] Now tell me what is missing.`,
    }],
  })
);
const parsed = StorylineSchema.parse(story);
assert.equal(parsed.scenes.reduce((sum, scene) => sum + scene.durationSeconds, 0), 120);
assert.equal(new Set(parsed.scenes.map((scene) => scene.characterName)).size, 1);
assert.equal(parsed.language, "en-US");
assert.deepEqual(parsed.plannedSections[0]?.requiredContent, ["Introduce task"]);

const oversized = `${"Read this sentence carefully. ".repeat(100)}`;
const chunks = splitForSarvam(oversized, 1800);
assert.ok(chunks.every((chunk) => chunk.length <= 1800));
assert.equal(chunks.join(" ").replace(/\s+/g, " ").trim(), oversized.replace(/\s+/g, " ").trim());

await assert.rejects(() => generateTwoStageScript(
  instruction,
  "6-8",
  60,
  async (_instruction, ageBand, duration) => ({
    ageBand,
    language: "en-US",
    targetDurationSeconds: duration,
    sections: [{ sectionOrder: 1, title: "Close", purpose: "Finish", durationSeconds: duration, requiredContent: ["Finish"] }],
  }),
  async (_instruction, _age, section) => ({
    scenes: [{ sceneOrder: 1, durationSeconds: section.durationSeconds, characterType: "human", characterName: "Person", characterState: "waves", visualAssetTag: "human", audioScript: "Hello.", sourceText: "Hello." }],
  })
));

console.log("Self-test passed: planner normalization, storyline validation, duration reconciliation, character rules, and Sarvam chunk limits.");