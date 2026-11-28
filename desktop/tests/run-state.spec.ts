import { expect, test } from "@playwright/test";
import { emptyRun, receiveEvent } from "../src/contract/run-state";

const start = {
  version: "1",
  type: "start",
  task_id: "task",
  agents: ["developer", "reviewer"],
  pipeline: "code_only",
};
test("stream skips malformed and future frames", () => {
  for (const frame of [
    null,
    [],
    "error",
    { version: "2", type: "start" },
    { ...start, agents: [null] },
    { ...start, type: "future" },
  ]) {
    expect(receiveEvent(emptyRun, frame)).toBe(emptyRun);
  }
});
test("error remains local until done, and replayed start preserves progress", () => {
  const running = receiveEvent(emptyRun, start);
  const failedStep = receiveEvent(running, {
    version: "1",
    type: "error",
    task_id: "task",
    agent_id: "developer",
    code: "timeout",
    message: "Timeout",
  });
  expect(failedStep.phase).toBe("running");
  expect(receiveEvent(failedStep, start)).toBe(failedStep);
  const done = receiveEvent(failedStep, {
    version: "1",
    type: "done",
    task_id: "task",
    outcome: "failed",
  });
  expect(done.phase).toBe("failed");
  expect(done.errors).toHaveLength(1);
  expect(receiveEvent(done, { ...start, type: "log", text: "late" })).toBe(
    done,
  );
});
test("frames from a different task do not alter current state", () => {
  const running = receiveEvent(emptyRun, start);
  expect(
    receiveEvent(running, {
      version: "1",
      type: "done",
      task_id: "other",
      outcome: "ok",
    }),
  ).toBe(running);
});

test("timeline replays contract example accessibly", async ({ page }) => {
  await page.goto("/iframe.html?id=ulei-run--contract-example&globals=locale:ru;mode:dark");
  const next = page.getByRole("button", { name: "Следующее событие" });
  for (let index = 0; index < 5; index += 1) await next.click();
  await expect(next).toBeDisabled();
  await expect(page.getByRole("heading", { name: "Итог" })).toBeVisible();
  await page.getByRole("button", { name: "Сначала" }).click();
  await expect(next).toBeEnabled();
});
