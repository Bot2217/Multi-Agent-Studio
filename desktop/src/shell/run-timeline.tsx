import { useState, type ReactNode } from "react";
import { Button } from "../components/ui/button";
import { Status } from "../components/ui/status";
import { emptyRun, receiveEvent, type RunState } from "../contract/run-state";
import type { Messages } from "../locales";

export function RunTimeline({ frames, t }: { frames: unknown[]; t: Messages }) {
  const [cursor, setCursor] = useState(0);
  const state = frames.slice(0, cursor).reduce(receiveEvent, emptyRun);
  return (
    <RunProgress state={state} t={t}>
      <div className="studio-actions">
        <Button
          variant="secondary"
          disabled={cursor === 0}
          onClick={() => setCursor(0)}
        >
          {t.resetPreview}
        </Button>
        <Button
          disabled={cursor >= frames.length}
          onClick={() => setCursor((value) => value + 1)}
        >
          {t.nextEvent}
        </Button>
      </div>
    </RunProgress>
  );
}

export function RunProgress({
  state,
  t,
  children,
  report,
}: {
  state: RunState;
  t: Messages;
  children?: ReactNode;
  report?: string;
}) {
  const label =
    state.phase === "ok"
      ? t.done
      : state.phase === "failed"
        ? t.failed
        : state.phase === "stopped"
          ? t.stopped
          : state.phase === "running"
            ? t.running
            : t.idle;
  return (
    <section className="studio-card studio-result">
      <div className="studio-section-heading">
        <h2>{t.rolesLabel}</h2>
        <div aria-live="polite">
          <Status
            tone={
              state.phase === "failed"
                ? "error"
                : state.phase === "ok"
                  ? "done"
                  : state.phase === "running"
                    ? "running"
                    : "idle"
            }
          >
            {label}
          </Status>
        </div>
      </div>
      <div className="studio-timeline-roles">
        {state.agents.map((agent) => {
          const step = state.steps.find((item) => item.agent_id === agent);
          const error = state.errors.find((item) => item.agent_id === agent);
          return (
            <div key={agent} className="studio-card">
              <strong>{step?.title ?? agent}</strong>
              <Status
                tone={
                  error
                    ? "error"
                    : state.phase === "ok"
                      ? "done"
                      : step && state.phase === "running"
                        ? "running"
                        : "idle"
                }
              >
                {error
                  ? t.failed
                  : state.phase === "ok"
                    ? t.done
                    : step && state.phase === "running"
                      ? t.running
                      : t.idle}
              </Status>
              {error && <p role="alert">{error.message}</p>}
            </div>
          );
        })}
      </div>
      <div className="studio-log" role="log" aria-label={t.logLabel}>
        {state.logs.length ? (
          state.logs.map((log, index) => (
            <p key={index}>
              <code>{log.agent_id || t.brand}</code> {log.text}
            </p>
          ))
        ) : (
          <p>{t.emptyDescription}</p>
        )}
      </div>
      {state.errors
        .filter((error) => !error.agent_id)
        .map((error, index) => (
          <p key={index} role="alert">
            {error.message}
          </p>
        ))}
      {state.errors.length > 0 && (
        <details>
          <summary>{t.technicalDetails}</summary>
          <code>{state.errors.map((error) => error.code).join(", ")}</code>
        </details>
      )}
      {state.result && (
        <div className="studio-run-result">
          <h3>{t.resultLabel}</h3>
          <p>{state.result}</p>
        </div>
      )}
      {report && state.phase === "ok" && (
        <Button asChild variant="secondary">
          <a
            href={`data:text/plain;charset=utf-8,${encodeURIComponent(report)}`}
            download="ulei-report.txt"
          >
            {t.downloadReport}
          </a>
        </Button>
      )}
      {children}
    </section>
  );
}
