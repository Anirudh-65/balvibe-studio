import { ExperimentPlanSchema, SceneSchema, StorylineSchema, type AgeBand, type ExperimentPlan, type Scene, type Storyline } from "./types";

export type Planner = (instruction: string, age: AgeBand, duration: number) => Promise<unknown>;
export type SectionWriter = (
  instruction: string,
  age: AgeBand,
  section: ExperimentPlan["sections"][number],
  first: boolean,
  last: boolean,
  characterName?: string
) => Promise<unknown>;

function normalizePlannerOutput(output: unknown): unknown {
  if (!output || typeof output !== "object") return output;
  const planner = output as { sections?: unknown };
  if (!Array.isArray(planner.sections)) return output;
  return {
    ...planner,
    sections: planner.sections.map((section) => {
      if (!section || typeof section !== "object") return section;
      const entry = section as { requiredContent?: unknown };
      return typeof entry.requiredContent === "string"
        ? { ...entry, requiredContent: [entry.requiredContent] }
        : entry;
    }),
  };
}

function reconcile(items: Array<{ durationSeconds: number }>, target: number) {
  const total = items.reduce((sum, item) => sum + item.durationSeconds, 0);
  if (total <= 0) throw new Error("Generated section has no positive duration.");
  const scale = target / total;
  const adjusted = items.map((item) => ({ ...item, durationSeconds: item.durationSeconds * scale }));
  const adjustedTotal = adjusted.reduce((sum, item) => sum + item.durationSeconds, 0);
  const last = adjusted.length - 1;
  adjusted[last]!.durationSeconds += target - adjustedTotal;
  if (adjusted[last]!.durationSeconds <= 0) throw new Error("Could not reconcile generated durations.");
  return adjusted;
}

function ensureClosing(sections: ExperimentPlan["sections"]): ExperimentPlan["sections"] {
  const finalSection = sections.at(-1);
  if (!finalSection || /closing|finish|goodbye|ending|wrap/i.test(finalSection.title)) return sections;
  if (finalSection.durationSeconds < 2) return sections;
  const closingDuration = Math.min(10, Math.max(1, Math.floor(finalSection.durationSeconds / 2)));
  return [
    ...sections.slice(0, -1),
    { ...finalSection, durationSeconds: finalSection.durationSeconds - closingDuration },
    {
      sectionOrder: finalSection.sectionOrder + 1,
      title: "Closing",
      purpose: "Give a final instruction and goodbye.",
      durationSeconds: closingDuration,
      requiredContent: ["Give a brief final instruction or goodbye."],
    },
  ];
}

export async function generateTwoStageScript(
  instruction: string,
  age: AgeBand,
  duration: number,
  plan: Planner,
  write: SectionWriter
): Promise<Storyline> {
  const parsedPlan = ExperimentPlanSchema.parse(
    normalizePlannerOutput(await plan(instruction, age, duration))
  );
  const sections = ensureClosing(reconcile(parsedPlan.sections, duration) as ExperimentPlan["sections"]);
  const allScenes: Scene[] = [];
  let primaryCharacter: string | undefined;
  let trialNumber = 1;

  for (let index = 0; index < sections.length; index += 1) {
    const section = sections[index]!;
    const result = await write(instruction, age, section, index === 0, index === sections.length - 1, primaryCharacter) as { scenes?: unknown };
    if (!Array.isArray(result.scenes) || result.scenes.length === 0) {
      throw new Error(`Writer returned no scenes for section ${section.sectionOrder}.`);
    }
    const scenes = result.scenes.map((value, sceneIndex) => {
      const raw = { ...(value as Record<string, unknown>) };
      if (raw.trial === null) delete raw.trial;
      if (raw.trial && typeof raw.trial === "object") {
        const trial = { ...(raw.trial as Record<string, unknown>) };
        if (typeof trial.trialNumber !== "number" || trial.trialNumber < 1) trial.trialNumber = trialNumber;
        trialNumber = Math.max(trialNumber + 1, Number(trial.trialNumber) + 1);
        raw.trial = trial;
      }
      const narration = raw.audioScript || raw.sourceText;
      const source = raw.sourceText || raw.audioScript;
      const visualAssetTag = raw.visualAssetTag || `${section.title.toLowerCase().replace(/[^a-z0-9]+/g, "_")}_${sceneIndex + 1}`;
      return SceneSchema.parse({
        ...raw,
        sceneOrder: allScenes.length + sceneIndex + 1,
        visualAssetTag,
        audioScript: narration,
        sourceText: source,
      });
    });
    const timedScenes = reconcile(scenes, section.durationSeconds) as Scene[];
    const characterNames = new Set(timedScenes.map((scene) => scene.characterName));
    if (characterNames.size !== 1) throw new Error(`Character changes within section ${section.sectionOrder}.`);
    const sectionCharacter = timedScenes[0]!.characterName;
    if (primaryCharacter && sectionCharacter !== primaryCharacter) {
      throw new Error(`Character changed from ${primaryCharacter} to ${sectionCharacter}.`);
    }
    primaryCharacter ??= sectionCharacter;
    for (const scene of timedScenes) {
      if (/(you|your answer|the child).*(got it right|answered correctly|was correct)/i.test(scene.audioScript)) {
        throw new Error(`Scene ${scene.sceneOrder} makes a participant-outcome claim.`);
      }
      if (scene.trial && !scene.trial.displayNumbers.includes(scene.trial.missingNumber)) {
        throw new Error(`Scene ${scene.sceneOrder} has a missing number absent from its displayed numbers.`);
      }
    }
    allScenes.push(...timedScenes);
  }

  return StorylineSchema.parse({
    ageBand: age,
    language: "en-US",
    targetDurationSeconds: duration,
    plannedSections: sections,
    scenes: allScenes,
  });
}

export function assertDurationSeconds(value: number): number {
  if (!Number.isInteger(value) || value < 30 || value > 3600) {
    throw new Error("Duration must be a whole number from 30 to 3600 seconds.");
  }
  return value;
}