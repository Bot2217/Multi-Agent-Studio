import type { PreviewRole } from "./studio-sections";
import type { RunEvent } from "../contract/run-state";
import type { Messages } from "../locales";

export const modes = {
  code_only: { label: "quickMode", agents: ["developer", "reviewer"] },
  full: {
    label: "fullMode",
    agents: ["manager", "researcher", "architect", "developer", "reviewer"],
  },
  research_code: { label: "researchMode", agents: ["researcher", "developer"] },
  single: { label: "singleMode", agents: ["developer"] },
} as const;

export type DemoMode = keyof typeof modes;

export function demoEvents(
  taskId: string,
  mode: DemoMode,
  roles: PreviewRole[],
  t: Messages,
): RunEvent[] {
  const context = { version: "1" as const, task_id: taskId };
  const agents = modes[mode].agents.filter((id) =>
    roles.some((role) => role.id === id),
  );
  return [
    { ...context, type: "start", pipeline: mode, agents },
    ...agents.flatMap((agent, index): RunEvent[] => [
      {
        ...context,
        type: "step",
        agent_id: agent,
        title: t[agent],
        index: index + 1,
        total: agents.length,
      },
      { ...context, type: "log", agent_id: agent, text: t.demoStep },
    ]),
    { ...context, type: "done", outcome: "ok", result: t.demoResult },
  ];
}
