import * as Dialog from "@radix-ui/react-dialog";
import {
  Bot,
  Box,
  Check,
  ChevronRight,
  FileText,
  Folder,
  KeyRound,
  Laptop,
  Play,
  Settings,
  Square,
  X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Button } from "../components/ui/button";
import { Field } from "../components/ui/field";
import { StatePanel } from "../components/ui/state-panel";
import { Status } from "../components/ui/status";
import { getMessages, type Locale } from "../locales";
import { emptyRun, receiveEvent } from "../contract/run-state";
import { demoEvents, modes, type DemoMode } from "./demo-run";
import { RunProgress } from "./run-timeline";
import { LocalModels, type RuntimeScenario } from "./local-models";
import "./studio.css";
import "./local-models.css";

const screens = [
  { id: "run", label: "runScreen", Icon: Play },
  { id: "agents", label: "agentsScreen", Icon: Bot },
  { id: "models", label: "modelsScreen", Icon: Box },
  { id: "local", label: "localScreen", Icon: Laptop },
  { id: "files", label: "filesScreen", Icon: FileText },
  { id: "settings", label: "settingsScreen", Icon: Settings },
] as const;
type Screen = (typeof screens)[number]["id"];
type Mode = "auto" | "light" | "dark";
type Palette = "graphite" | "warm";

export type StudioProps = {
  initialScreen?: Screen;
  localScenario?: RuntimeScenario;
  initialLocale?: Locale;
  initialMode?: Mode;
  initialPalette?: Palette;
  initialOnboarding?: boolean;
  engineUnavailable?: boolean;
  updateAvailable?: boolean;
};

function Brand({ name, subtitle }: { name: string; subtitle: string }) {
  return (
    <div className="studio-brand">
      <svg aria-hidden width="40" height="40" viewBox="0 0 32 32">
        <path fill="#c2f24e" d="M16 4.2 21.2 7.2v6L16 16.2 10.8 13.2v-6z" />
        <path fill="#e0a15a" d="M22.4 8.4 27.6 11.4v6l-5.2 3-5.2-3v-6z" />
        <path fill="#9be0b8" d="M9.6 8.4 14.8 11.4v6l-5.2 3-5.2-3v-6z" />
        <path fill="#eef0f4" d="M16 15.6 21.2 18.6v6L16 27.6 10.8 24.6v-6z" />
      </svg>
      <div>
        <b>{name}</b>
        <small>{subtitle}</small>
      </div>
    </div>
  );
}

export function Studio({
  initialScreen = "run",
  localScenario,
  initialLocale = "ru",
  initialMode = "auto",
  initialPalette = "graphite",
  initialOnboarding = false,
  engineUnavailable = false,
  updateAvailable = false,
}: StudioProps) {
  const [locale, setLocale] = useState(initialLocale);
  const [mode, setMode] = useState(initialMode);
  const [palette, setPalette] = useState(initialPalette);
  const [screen, setScreen] = useState<Screen>(initialScreen);
  const [onboarding, setOnboarding] = useState(initialOnboarding);
  const [path, setPath] = useState<"cloud" | "local" | null>(null);
  const [updateOpen, setUpdateOpen] = useState(updateAvailable);
  const [updateError, setUpdateError] = useState(false);
  const [task, setTask] = useState("");
  const [folder, setFolder] = useState("~/work/demo");
  const [validation, setValidation] = useState(false);
  const [pipeline, setPipeline] = useState<DemoMode>("code_only");
  const [progress, setProgress] = useState(emptyRun);
  const [pendingFrames, setPendingFrames] = useState<
    ReturnType<typeof demoEvents>
  >([]);
  const [recent, setRecent] = useState<string[]>([]);
  const runId = useRef(0);
  const running = pendingFrames.length > 0;
  const stopButton = useRef<HTMLButtonElement>(null);
  const restoreFocus = useRef(false);
  const [connectionAttempt, setConnectionAttempt] = useState(false);
  const heading = useRef<HTMLHeadingElement>(null);
  const runButton = useRef<HTMLButtonElement>(null);
  const firstNavigation = useRef(true);
  const t = getMessages(locale);

  useEffect(() => {
    document.documentElement.dataset.palette = palette;
    document.documentElement.dataset.mode = mode;
    document.documentElement.lang = locale;
  }, [palette, mode, locale]);

  useEffect(() => {
    if (firstNavigation.current) {
      firstNavigation.current = false;
      return;
    }
    heading.current?.focus();
  }, [screen, onboarding]);

  useEffect(() => {
    const [frame, ...remaining] = pendingFrames;
    if (!frame) return;
    const timer = window.setTimeout(() => {
      setProgress((current) => receiveEvent(current, frame));
      setPendingFrames(remaining);
    }, 450);
    return () => window.clearTimeout(timer);
  }, [pendingFrames]);

  useEffect(() => {
    if (!restoreFocus.current) return;
    restoreFocus.current = false;
    (running ? stopButton : runButton).current?.focus();
  }, [running]);

  function navigate(target: Screen) {
    setScreen(target);
    setOnboarding(false);
  }

  function startRun() {
    setValidation(true);
    if (running || !task.trim() || !folder.trim()) return;
    const text = task.trim();
    runId.current += 1;
    setProgress(emptyRun);
    setPendingFrames(demoEvents(`demo-${runId.current}`, pipeline, t));
    setRecent((previous) =>
      [text, ...previous.filter((item) => item !== text)].slice(0, 5),
    );
    restoreFocus.current = true;
  }

  function stopRun() {
    restoreFocus.current = true;
    setPendingFrames([]);
    setProgress((current) => ({ ...current, phase: "stopped" }));
  }

  return (
    <div className="studio-shell">
      <aside className="studio-sidebar">
        <a className="studio-skip" href="#studio-content">
          {t.skip}
        </a>
        <Brand name={t.brand} subtitle={t.studio} />
        <nav aria-label={t.navigation}>
          {screens.map(({ id, label, Icon }) => (
            <button
              key={id}
              className="studio-nav"
              aria-current={!onboarding && screen === id ? "page" : undefined}
              onClick={() => navigate(id)}
            >
              <Icon size={24} aria-hidden />
              <span>{t[label]}</span>
            </button>
          ))}
        </nav>
        <div className="studio-sidebar-bottom">
          <label className="studio-select">
            {t.theme}
            <select
              aria-label={t.theme}
              value={mode}
              onChange={(event) => setMode(event.target.value as Mode)}
            >
              <option value="auto">{t.auto}</option>
              <option value="light">{t.light}</option>
              <option value="dark">{t.dark}</option>
            </select>
          </label>
        </div>
      </aside>

      <div className="studio-main">
        <header className="studio-topbar">
          <span>{t.previewLabel}</span>
          <label className="studio-language">
            <span className="sr-only">{t.language}</span>
            <select
              aria-label={t.language}
              value={locale}
              onChange={(event) => setLocale(event.target.value as Locale)}
            >
              <option value="ru">Русский</option>
              <option value="en">English</option>
            </select>
          </label>
        </header>
        <main id="studio-content" className="studio-content">
          {engineUnavailable && (
            <section className="studio-notice" aria-label={t.engineDown}>
              <div>
                <strong>{t.engineDown}</strong>
                <p>
                  {connectionAttempt ? t.errorDescription : t.engineDownBody}
                </p>
              </div>
              <Button
                variant="secondary"
                onClick={() => setConnectionAttempt(true)}
              >
                {t.retry}
              </Button>
            </section>
          )}

          {onboarding ? (
            <section className="studio-onboarding">
              <div className="studio-page-heading">
                <p className="studio-eyebrow">{t.onboarding}</p>
                <h1 ref={heading} tabIndex={-1}>
                  {path ? t.connectTitle : t.welcome}
                </h1>
                <p>{t.welcomeBody}</p>
              </div>
              {path ? (
                <div className="studio-card studio-setup">
                  {path === "cloud" ? (
                    <KeyRound size={32} aria-hidden />
                  ) : (
                    <Laptop size={32} aria-hidden />
                  )}
                  <h2>{path === "cloud" ? t.cloudPath : t.localPath}</h2>
                  <p>{path === "cloud" ? t.connectBody : t.localPending}</p>
                  {path === "cloud" && (
                    <p className="studio-disclosure">{t.keyNotice}</p>
                  )}
                  <div className="studio-actions">
                    <Button variant="secondary" onClick={() => setPath(null)}>
                      {t.back}
                    </Button>
                    <Button
                      onClick={() => {
                        setTask(t.exampleTask);
                        setOnboarding(false);
                      }}
                    >
                      {t.continue}
                      <ChevronRight size={16} aria-hidden />
                    </Button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="studio-paths">
                    <button
                      className="studio-card studio-path"
                      onClick={() => setPath("cloud")}
                    >
                      <KeyRound size={24} aria-hidden />
                      <h2>{t.cloudPath}</h2>
                      <p>{t.cloudBody}</p>
                      <ChevronRight size={20} aria-hidden />
                    </button>
                    <button
                      className="studio-card studio-path"
                      onClick={() => setPath("local")}
                    >
                      <Laptop size={24} aria-hidden />
                      <h2>{t.localPath}</h2>
                      <p>{t.localBody}</p>
                      <ChevronRight size={20} aria-hidden />
                    </button>
                  </div>
                  <Button variant="quiet" onClick={() => navigate("settings")}>
                    {t.otherProvider}
                  </Button>
                </>
              )}
              <Button variant="quiet" onClick={() => setOnboarding(false)}>
                {t.skip}
              </Button>
            </section>
          ) : (
            <>
              <div className="studio-page-heading">
                <h1 ref={heading} tabIndex={-1}>
                  {t[screens.find(({ id }) => id === screen)!.label]}
                </h1>
                <p>{t.previewBody}</p>
              </div>
              {screen === "run" ? (
                <div className="studio-run-grid">
                  <section className="studio-card studio-task">
                    <form
                      onSubmit={(event) => {
                        event.preventDefault();
                        startRun();
                      }}
                    >
                      <label htmlFor="studio-task">{t.taskLabel}</label>
                      <textarea
                        id="studio-task"
                        value={task}
                        disabled={running}
                        aria-invalid={(validation && !task.trim()) || undefined}
                        aria-describedby={
                          validation && !task.trim() ? "task-error" : undefined
                        }
                        placeholder={t.taskPlaceholder}
                        onChange={(event) => setTask(event.target.value)}
                        onKeyDown={(event) => {
                          if (
                            (event.ctrlKey || event.metaKey) &&
                            event.key === "Enter"
                          ) {
                            event.preventDefault();
                            if (!running) startRun();
                          }
                        }}
                      />
                      {validation && !task.trim() && (
                        <p id="task-error" role="alert" className="text-danger">
                          {t.emptyTask}
                        </p>
                      )}
                      {!task && (
                        <div className="studio-examples">
                          {(["example", "readme", "todo"] as const).map(
                            (sample) => (
                              <Button
                                key={sample}
                                variant="quiet"
                                onClick={() => setTask(t[`${sample}Task`])}
                              >
                                {t[`${sample}Label`]}
                                <ChevronRight size={16} aria-hidden />
                              </Button>
                            ),
                          )}
                        </div>
                      )}
                      <div className="studio-form-options">
                        <label className="studio-select">
                          {t.modeLabel}
                          <select
                            aria-label={t.modeLabel}
                            disabled={running}
                            value={pipeline}
                            onChange={(event) =>
                              setPipeline(event.target.value as DemoMode)
                            }
                          >
                            {(Object.keys(modes) as DemoMode[]).map((mode) => (
                              <option key={mode} value={mode}>
                                {t[modes[mode].label]}
                              </option>
                            ))}
                          </select>
                        </label>
                        <Field
                          label={t.projectFolder}
                          value={folder}
                          onChange={(event) => setFolder(event.target.value)}
                          disabled={running}
                          error={
                            validation && !folder.trim()
                              ? t.folderError
                              : undefined
                          }
                        />
                      </div>
                      <div className="studio-submit">
                        <span className="studio-shortcut">
                          ⌘ / Ctrl + Enter
                        </span>
                        {running ? (
                          <Button
                            key="stop"
                            ref={stopButton}
                            variant="danger"
                            onClick={stopRun}
                          >
                            <Square size={16} aria-hidden />
                            {t.stop}
                          </Button>
                        ) : (
                          <Button key="run" ref={runButton} type="submit">
                            <Play size={16} aria-hidden />
                            {t.runDemo}
                          </Button>
                        )}
                      </div>
                    </form>
                  </section>
                  <section className="studio-card studio-team">
                    <div className="studio-section-heading">
                      <h2>{t.rolesLabel}</h2>
                      <Button
                        variant="quiet"
                        onClick={() => navigate("agents")}
                      >
                        {t.configure}
                      </Button>
                    </div>
                    {modes[pipeline].agents.map((agent, index) => (
                      <div className="studio-role" key={agent}>
                        <span className="studio-role-icon">
                          {index === 0 ? (
                            <Bot size={24} aria-hidden />
                          ) : (
                            <Check size={24} aria-hidden />
                          )}
                        </span>
                        <div>
                          <strong>{t[agent]}</strong>
                          <code>gemini-2.5-flash</code>
                        </div>
                      </div>
                    ))}
                  </section>
                  {progress.phase === "idle" ? (
                    <section
                      className="studio-card studio-result"
                      aria-live="polite"
                    >
                      {running ? (
                        <Status tone="running">{t.startingRun}</Status>
                      ) : (
                        <StatePanel
                          title={t.emptyTitle}
                          description={t.emptyDescription}
                        />
                      )}
                    </section>
                  ) : (
                    <RunProgress
                      state={progress}
                      t={t}
                      report={[
                        recent[0],
                        ...progress.logs.map(
                          (log) => `${log.agent_id ?? ""} ${log.text}`,
                        ),
                        progress.result,
                      ].join("\n")}
                    />
                  )}
                  {!running && recent.length > 0 && (
                    <section className="studio-card studio-result">
                      <h2>{t.recentTasks}</h2>
                      <ul className="studio-recent">
                        {recent.map((text) => (
                          <li key={text}>
                            <Button
                              variant="quiet"
                              onClick={() => setTask(text)}
                            >
                              {text}
                            </Button>
                          </li>
                        ))}
                      </ul>
                    </section>
                  )}
                </div>
              ) : screen === "local" ? (
                <LocalModels
                  t={t}
                  scenario={localScenario}
                  onSettings={() => navigate("settings")}
                />
              ) : screen === "settings" ? (
                <section className="studio-card studio-settings">
                  <h2>{t.appearance}</h2>
                  <label className="studio-select">
                    {t.palette}
                    <select
                      aria-label={t.palette}
                      value={palette}
                      onChange={(event) =>
                        setPalette(event.target.value as Palette)
                      }
                    >
                      <option value="graphite">{t.graphite}</option>
                      <option value="warm">{t.warm}</option>
                    </select>
                  </label>
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setPath(null);
                      setOnboarding(true);
                    }}
                  >
                    {t.onboarding}
                  </Button>
                </section>
              ) : (
                <section className="studio-card">
                  <StatePanel
                    title={t.screenPending}
                    description={t.screenPendingBody}
                    action={
                      <Button
                        variant="secondary"
                        onClick={() => navigate("run")}
                      >
                        <Folder size={16} aria-hidden />
                        {t.runScreen}
                      </Button>
                    }
                  />
                </section>
              )}
            </>
          )}
        </main>
      </div>
      <Dialog.Root open={updateOpen} onOpenChange={setUpdateOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="studio-overlay" />
          <Dialog.Content className="studio-dialog">
            <Dialog.Title>{t.updateTitle}</Dialog.Title>
            <Dialog.Description>{t.updateBody}</Dialog.Description>
            <Dialog.Close asChild>
              <Button
                variant="quiet"
                className="studio-dialog-close"
                aria-label={t.close}
              >
                <X size={20} aria-hidden />
              </Button>
            </Dialog.Close>
            {updateError && (
              <p role="alert" className="text-danger">
                {t.updateError}
              </p>
            )}
            <div className="studio-actions">
              <Dialog.Close asChild>
                <Button variant="secondary">{t.later}</Button>
              </Dialog.Close>
              <Button onClick={() => setUpdateError(true)}>
                {t.updateAction}
              </Button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
