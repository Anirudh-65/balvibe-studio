import type { AgeBand } from "./types";

const AGE_RULES: Record<AgeBand, string> = {
  "4-5": "Use very short sentences (5-8 words), concrete familiar vocabulary, and one action at a time.",
  "6-8": "Use short, simple sentences (8-12 words) and everyday vocabulary.",
  "9-11": "Use clear sentences of about 15 words or fewer; common school vocabulary is suitable.",
};

export function buildPlannerSystemPrompt(age: AgeBand, duration: number): string {
  return `Plan a child-facing cognitive experiment instruction for ages ${age}. Return only JSON with ageBand, language="en-US", targetDurationSeconds=${duration}, and sections shaped like [{"sectionOrder":1,"title":"Introduction","purpose":"Explain the activity","durationSeconds":30,"requiredContent":["Explain the task","Describe the response"]}]. requiredContent must always be an array of strings, even when there is only one item. Durations must be positive and sum exactly to ${duration}. Include every rule, response option, timing, practice round, trial count and closing from the source. Do not invent experiment rules or feedback. Create one cohesive story and one friendly non-human character. The child-facing plan must not claim experimental outcomes.`;
}

export function buildPlannerUserPrompt(instruction: string): string {
  return `Researcher's complete experiment instructions:\n"""\n${instruction}\n"""\nReturn the JSON plan.`;
}

export function buildWriterSystemPrompt(
  age: AgeBand,
  title: string,
  duration: number,
  first: boolean,
  last: boolean,
  characterName?: string
): string {
  return `Write the complete ${duration}-second section "${title}" for children aged ${age}. ${AGE_RULES[age]} Return only JSON shaped as {"scenes":[{"sceneOrder":1,"durationSeconds":10,"characterType":"animal","characterName":"Milo","characterState":"waving","visualAssetTag":"intro","audioScript":"spoken narration; [PAUSE 2 seconds] is a silent pause","sourceText":"same narration"}]}. Create enough scenes to fill the section. Durations must sum exactly to ${duration}. Preserve every experiment rule, stimulus, response, timing and trial count. Use one consistent non-human character (animal, robot or creature) throughout. Never add rewards, correctness claims or corrective feedback. Use the established character name ${characterName || "chosen in this section and reused"}. ${first ? "Greet and introduce the activity." : "Do not greet again."} ${last ? "End with a brief goodbye." : "Do not end the whole activity."} Add trial metadata only to actual demonstration, practice or formal trial scenes; omit it otherwise, never use null. Trial numbers start at 1.`;
}

export function buildWriterUserPrompt(
  instruction: string,
  section: { title: string; purpose: string; durationSeconds: number; requiredContent: string[] }
): string {
  return `Full researcher instruction:\n"""\n${instruction}\n"""\nSection brief:\n${JSON.stringify(section, null, 2)}\nWrite all scenes for this section.`;
}