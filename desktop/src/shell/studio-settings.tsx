import { useEffect, useState, type ReactNode } from "react";
import { Button } from "../components/ui/button";
import { Field } from "../components/ui/field";
import { Status } from "../components/ui/status";
import type { Messages } from "../locales";

export type McpScenario =
  | "empty"
  | "ready"
  | "checking"
  | "error"
  | "offline"
  | "long";

export function StudioSettings({
  t,
  appearance,
  mcpScenario = "empty",
}: {
  t: Messages;
  appearance: ReactNode;
  mcpScenario?: McpScenario;
}) {
  const [keyNotice, setKeyNotice] = useState(false);
  const [sshState, setSshState] = useState<"idle" | "pending" | "unavailable">(
    "idle",
  );
  useEffect(() => {
    if (sshState !== "pending") return;
    const timer = window.setTimeout(() => setSshState("unavailable"), 500);
    return () => window.clearTimeout(timer);
  }, [sshState]);

  return (
    <div className="studio-section-stack">
      {appearance}
      <section className="studio-card studio-section-stack">
        <h2>{t.apiKeys}</h2>
        <p>{t.apiKeyHint}</p>
        <form
          className="studio-section-stack"
          onSubmit={(event) => {
            event.preventDefault();
            event.currentTarget.reset();
            setKeyNotice(true);
          }}
        >
          <div className="studio-form-options">
            {[
              "Google",
              "OpenRouter",
              "OpenAI",
              "Anthropic",
              "DeepSeek",
              "Groq",
              "xAI",
            ].map((provider) => (
              <Field
                key={provider}
                label={provider}
                type="password"
                autoComplete="off"
              />
            ))}
          </div>
          <Button type="submit">{t.saveKeys}</Button>
        </form>
        {keyNotice && <p role="status">{t.settingsPreviewOnly}</p>}
      </section>

      <section className="studio-card studio-section-stack">
        <h2>{t.runScreen}</h2>
        <div className="studio-form-options">
          <Field label={t.maxSteps} type="number" min={1} defaultValue={8} />
          <Field
            label={t.shellTimeout}
            type="number"
            min={1}
            defaultValue={60}
          />
          <Field
            label={t.ollamaAddress}
            type="url"
            defaultValue="http://127.0.0.1:11434"
          />
          <Field label={t.ollamaFolder} placeholder="~/work/models" />
        </div>
        <label className="studio-check">
          <input type="checkbox" />
          {t.keepAwake}
        </label>
        <label className="studio-check">
          <input type="checkbox" />
          {t.keepDisplay}
        </label>
      </section>

      <section className="studio-card studio-section-stack">
        <h2>{t.ssh}</h2>
        <p>{t.sshHint}</p>
        <form
          className="studio-section-stack"
          onSubmit={(event) => {
            event.preventDefault();
            setSshState("pending");
          }}
        >
          <div className="studio-form-options">
            <Field label={t.sshHost} required />
            <Field label={t.sshUser} />
            <Field label={t.sshKey} />
            <Field
              label={t.sshPort}
              type="number"
              min={1}
              max={65535}
              defaultValue={22}
            />
          </div>
          <Field label={t.sshCommand} required />
          <Button type="submit" disabled={sshState === "pending"}>
            {t.sshRun}
          </Button>
        </form>
        <div role="status">
          {sshState === "pending"
            ? t.sshConnecting
            : sshState === "unavailable"
              ? t.sshPreviewOnly
              : null}
        </div>
      </section>

      <McpSettings t={t} scenario={mcpScenario} />

      <section className="studio-card studio-section-stack">
        <h2>{t.helpTitle}</h2>
        <p>{t.helpStart}</p>
        <p>{t.helpLocal}</p>
        <p>{t.helpFiles}</p>
      </section>
    </div>
  );
}

function McpSettings({ t, scenario }: { t: Messages; scenario: McpScenario }) {
  const online = scenario === "ready" || scenario === "long";
  const statuses = {
    empty: t.mcpEmpty,
    ready: t.mcpReady,
    checking: t.mcpChecking,
    error: t.mcpError,
    offline: t.mcpOffline,
    long: t.mcpReady,
  };
  const tools =
    scenario === "long"
      ? Array.from({ length: 40 }, (_, index) => `tool_${index + 1}`)
      : ["list_notes", "read_note"];
  return (
    <section className="studio-card studio-section-stack">
      <h2>{t.mcpTitle}</h2>
      {scenario !== "empty" && (
        <div>
          <strong>Notes</strong>
          <br />
          <code>http://127.0.0.1:7337/mcp</code>
        </div>
      )}
      <Status
        tone={
          online
            ? "done"
            : scenario === "error" || scenario === "offline"
              ? "error"
              : scenario === "checking"
                ? "running"
                : "idle"
        }
      >
        {statuses[scenario]}
      </Status>
      {online && (
        <details>
          <summary>{t.mcpTools}</summary>
          <ul className="studio-tool-list">
            {tools.map((tool) => (
              <li key={tool}>
                <code>{tool}</code>
              </li>
            ))}
          </ul>
        </details>
      )}
      <p>{t.mcpPending}</p>
    </section>
  );
}
