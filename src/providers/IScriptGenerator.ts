import type { AgeBand, Storyline } from "../types";

export interface IScriptGenerator {
  generateScript(
    instruction: string,
    ageBand: AgeBand,
    targetDurationSeconds: number
  ): Promise<Storyline>;
}