import type {
  DoneEvent,
  ErrorEvent,
  LogEvent,
  StartEvent,
  StepEvent,
} from "./ulei-contract-v1";

export type RunEvent =
  | StartEvent
  | StepEvent
  | LogEvent
  | ErrorEvent
  | DoneEvent;
export type RunState = {
  taskId: string | null;
  phase: "idle" | "running" | "ok" | "stopped" | "failed";
  agents: string[];
  steps: StepEvent[];
  logs: LogEvent[];
  errors: ErrorEvent[];
  result: string;
};

export const emptyRun: RunState = {
  taskId: null,
  phase: "idle",
  agents: [],
  steps: [],
  logs: [],
  errors: [],
  result: "",
};

function isRunEvent(value: unknown): value is RunEvent {
  if (!value || typeof value !== "object") return false;
  const frame = value as Record<string, unknown>;
  if (frame.version !== "1" || typeof frame.task_id !== "string") return false;
  const agentIsValid =
    frame.agent_id == null || typeof frame.agent_id === "string";
  switch (frame.type) {
    case "start":
      return (
        typeof frame.pipeline === "string" &&
        Array.isArray(frame.agents) &&
        frame.agents.every((agent) => typeof agent === "string")
      );
    case "step":
      return (
        Number.isInteger(frame.index) &&
        Number.isInteger(frame.total) &&
        Number(frame.index) >= 1 &&
        Number(frame.total) >= Number(frame.index) &&
        typeof frame.agent_id === "string" &&
        typeof frame.title === "string"
      );
    case "log":
      return agentIsValid && typeof frame.text === "string";
    case "error":
      return (
        agentIsValid &&
        typeof frame.code === "string" &&
        typeof frame.message === "string"
      );
    case "done":
      return (
        ["ok", "stopped", "failed"].includes(String(frame.outcome)) &&
        (frame.result === undefined || typeof frame.result === "string")
      );
    default:
      return false;
  }
}

export function receiveEvent(state: RunState, value: unknown): RunState {
  if (!isRunEvent(value)) return state;
  if (value.type === "start") {
    if (state.taskId === value.task_id) return state;
    return {
      ...emptyRun,
      taskId: value.task_id,
      agents: value.agents,
      phase: "running",
    };
  }
  if (state.taskId !== value.task_id || state.phase !== "running") return state;
  switch (value.type) {
    case "step":
      if (
        state.steps.some(
          (step) =>
            step.index === value.index && step.agent_id === value.agent_id,
        )
      )
        return state;
      return { ...state, steps: [...state.steps, value] };
    case "log":
      return { ...state, logs: [...state.logs, value] };
    case "error":
      return { ...state, errors: [...state.errors, value] };
    case "done":
      return { ...state, phase: value.outcome, result: value.result ?? "" };
    default:
      return state;
  }
}
