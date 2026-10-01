import Groq from "groq-sdk";
import type { AgeBand, Storyline } from "../types";
import type { IScriptGenerator } from "./IScriptGenerator";
import { buildPlannerSystemPrompt, buildPlannerUserPrompt, buildWriterSystemPrompt, buildWriterUserPrompt } from "../prompts";
import { generateTwoStageScript } from "../scriptPipeline";

export class GroqScriptGenerator implements IScriptGenerator {
  private readonly client: Groq;
  private readonly model: string;
  private readonly maxTokens: number;

  constructor() {
    const apiKey = process.env.GROQ_API_KEY;
    if (!apiKey) {
      throw new Error("GROQ_API_KEY is missing. Add it to the local .env file.");
    }
    this.client = new Groq({ apiKey });
    this.model = process.env.GROQ_MODEL || "qwen/qwen3.8-27b";
    this.maxTokens = Number(process.env.GROQ_MAX_TOKENS || 900);
  }

  async generateScript(instruction: string, ageBand: AgeBand, duration: number): Promise<Storyline> {
    return generateTwoStageScript(
      instruction,
      ageBand,
      duration,
      async (raw, band, seconds) => this.callJson(
        buildPlannerSystemPrompt(band, seconds),
        buildPlannerUserPrompt(raw)
      ),
      async (raw, band, section, first, last, characterName) => this.callJson(
        buildWriterSystemPrompt(band, section.title, section.durationSeconds, first, last, characterName),
        buildWriterUserPrompt(raw, section)
      )
    );
  }

  private async callJson(system: string, user: string): Promise<unknown> {
    const completion = await this.client.chat.completions.create({
      model: this.model,
      temperature: 0.6,
      max_tokens: this.maxTokens,
      response_format: { type: "json_object" },
      messages: [{ role: "system", content: system }, { role: "user", content: user }],
    });
    const content = completion.choices[0]?.message?.content;
    if (!content) throw new Error("Groq returned an empty response.");
    try {
      return JSON.parse(content) as unknown;
    } catch {
      throw new Error(`Groq response was not valid JSON:\n${content}`);
    }
  }
}