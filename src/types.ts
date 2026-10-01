import { z } from "zod";

export const AgeBandSchema = z.enum(["4-5", "6-8", "9-11"]);
export type AgeBand = z.infer<typeof AgeBandSchema>;

export const CharacterTypeSchema = z.enum(["animal", "robot", "creature"]);
export const TrialSchema = z.object({
  trialNumber: z.number().int().positive(),
  phase: z.enum(["demonstration", "practice", "formal"]),
  displayNumbers: z.array(z.number().int()).min(1),
  missingNumber: z.number().int(),
  displayDurationSeconds: z.number().positive(),
  responseWindowSeconds: z.number().positive(),
});

export const SceneSchema = z.object({
  sceneOrder: z.number().int().positive(),
  durationSeconds: z.number().positive(),
  characterType: CharacterTypeSchema,
  characterName: z.string().min(1),
  characterState: z.string().min(1),
  visualAssetTag: z.string().min(1),
  audioScript: z.string(),
  sourceText: z.string(),
  trial: TrialSchema.optional(),
});
export type Scene = z.infer<typeof SceneSchema>;

export const PlanSectionSchema = z.object({
  sectionOrder: z.number().int().positive(),
  title: z.string().min(1),
  purpose: z.string().min(1),
  durationSeconds: z.number().positive(),
  requiredContent: z.array(z.string().min(1)).min(1),
});

export const ExperimentPlanSchema = z.object({
  ageBand: AgeBandSchema,
  language: z.literal("en-US"),
  targetDurationSeconds: z.number().int().positive(),
  sections: z.array(PlanSectionSchema).min(1),
});
export type ExperimentPlan = z.infer<typeof ExperimentPlanSchema>;

export const StorylineSchema = z.object({
  ageBand: AgeBandSchema,
  language: z.literal("en-US"),
  targetDurationSeconds: z.number().int().positive(),
  plannedSections: z.array(PlanSectionSchema).min(1),
  scenes: z.array(SceneSchema).min(1),
});
export type Storyline = z.infer<typeof StorylineSchema>;

export type HindiStoryline = Omit<Storyline, "language" | "scenes"> & {
  language: "hi-IN";
  scenes: Array<Scene & { translatedText: string }>;
};