import * as Dialog from "@radix-ui/react-dialog";
import { Cpu, Download, HardDrive, Search } from "lucide-react";
import { useEffect, useId, useState } from "react";
import { Button } from "../components/ui/button";
import { Status } from "../components/ui/status";
import type { LocalModelStatus } from "../contract/ulei-contract-v1";
import type { Messages } from "../locales";

const gib = 1024 ** 3;
const catalogue = [
  { family: "Qwen 2.5 Coder", name: "qwen2.5-coder:1.5b", size: 1, memory: 3 },
  { family: "Qwen 2.5 Coder", name: "qwen2.5-coder:7b", size: 4.7, memory: 8 },
  { family: "Qwen 2.5 Coder", name: "qwen2.5-coder:32b", size: 20, memory: 28 },
  { family: "Llama 3.2", name: "llama3.2:3b", size: 2, memory: 4 },
  { family: "Mistral", name: "mistral:7b", size: 4.1, memory: 7 },
];

export type RuntimeScenario =
  | "external"
  | "idle"
  | "managed"
  | "missing"
  | "offline"
  | "port"
  | "unsupported";
const runtimeLabels = {
  external: "runtimeExternal",
  idle: "runtimeIdle",
  managed: "runtimeManaged",
  missing: "runtimeMissing",
  offline: "runtimeFailed",
  port: "runtimePort",
  unsupported: "runtimeUnsupported",
} as const;

const modelLabels = {
  missing: "modelMissing",
  downloading: "modelDownloading",
  paused: "modelPaused",
  installed: "modelInstalled",
  starting: "modelStarting",
  running: "running",
  error: "modelFailed",
} as const;

type Props = {
  t: Messages;
  scenario?: RuntimeScenario;
  initialModels?: LocalModelStatus[];
  disk?: number;
  memory?: number;
  onSettings: () => void;
};

export function LocalModels({
  t,
  scenario = "external",
  initialModels,
  disk = 74,
  memory = 16,
  onSettings,
}: Props) {
  const [runtime, setRuntime] = useState(scenario);
  const [install, setInstall] = useState<number | null>(null);
  const [models, setModels] = useState<LocalModelStatus[]>(
    () =>
      initialModels ??
      (scenario === "external"
        ? [{ name: "llama3.2:3b", state: "running", size_bytes: 2 * gib }]
        : []),
  );
  const [query, setQuery] = useState("");
  const [tag, setTag] = useState(catalogue[1].name);
  const [remove, setRemove] = useState<string | null>(null);
  const tagId = useId();
  const selected = catalogue.find((item) => item.name === tag) ?? catalogue[0];
  const runtimeReady =
    runtime === "external" || runtime === "managed" || runtime === "idle";
  const downloading = models.some(({ state }) => state === "downloading");
  const matching = catalogue.filter(({ name, family }) =>
    `${name} ${family}`.toLowerCase().includes(query.trim().toLowerCase()),
  );

  useEffect(() => {
    if (install === null) return;
    const timer = window.setTimeout(() => {
      if (install >= 0.8) {
        setInstall(null);
        setRuntime("idle");
      } else {
        setInstall(install + 0.2);
      }
    }, 450);
    return () => window.clearTimeout(timer);
  }, [install]);

  useEffect(() => {
    if (!downloading) return;
    const timer = window.setInterval(() => {
      setModels((current) =>
        current.map((model) => {
          if (model.state !== "downloading") return model;
          const progress = Math.min(1, (model.progress ?? 0) + 0.1);
          return progress >= 0.999
            ? {
                ...model,
                progress: 1,
                completed: model.total,
                state: "installed",
              }
            : {
                ...model,
                progress,
                completed: Math.round(progress * (model.total ?? 0)),
              };
        }),
      );
    }, 450);
    return () => window.clearInterval(timer);
  }, [downloading]);

  function changeModel(name: string, state: LocalModelStatus["state"]) {
    setModels((current) =>
      current.map((model) =>
        model.name === name ? { ...model, state } : model,
      ),
    );
  }

  function download() {
    setModels((current) => [
      ...current.filter((model) => model.name !== selected.name),
      {
        version: "1",
        name: selected.name,
        state: "downloading",
        progress: 0,
        completed: 0,
        total: selected.size * gib,
        size_bytes: selected.size * gib,
      },
    ]);
  }

  return (
    <div className="local-grid">
      <section
        className="studio-card local-runtime"
        aria-label={t.runtimeLabel}
      >
        <div className="local-runtime-title">
          <span className="studio-role-icon">
            <Cpu size={22} aria-hidden />
          </span>
          <div>
            <p>{t.runtimeLabel}</p>
            <h2>Ollama</h2>
          </div>
        </div>
        <div aria-live="polite">
          {install === null ? (
            <>
              <Status
                tone={
                  runtimeReady
                    ? "done"
                    : runtime === "missing"
                      ? "idle"
                      : "error"
                }
              >
                {t[runtimeLabels[runtime]]}
              </Status>
              {runtime === "external" && <p>{t.runtimeExternalNote}</p>}
              {runtime === "missing" && <p>{t.runtimeNoAdmin}</p>}
            </>
          ) : (
            <label className="local-progress">
              {t.runtimeDownloading}
              <progress max={1} value={install} />
            </label>
          )}
        </div>
        <div className="studio-actions">
          {install !== null && (
            <Button variant="secondary" onClick={() => setInstall(null)}>
              {t.cancel}
            </Button>
          )}
          {install === null &&
            (runtime === "missing" || runtime === "offline") && (
              <Button onClick={() => setInstall(0)}>
                {runtime === "offline" ? t.retry : t.runtimeInstall}
              </Button>
            )}
          {runtime === "idle" && (
            <Button onClick={() => setRuntime("managed")}>
              {t.runtimeStart}
            </Button>
          )}
          {runtime === "port" && (
            <Button variant="secondary" onClick={onSettings}>
              {t.settingsScreen}
            </Button>
          )}
        </div>
      </section>

      <section
        className="studio-card local-hardware"
        aria-label={`${t.diskFree}, ${t.memory}`}
      >
        <div>
          <HardDrive size={18} aria-hidden />
          <span>{t.diskFree}</span>
          <strong>
            {disk} {t.gib}
          </strong>
        </div>
        <div>
          <Cpu size={18} aria-hidden />
          <span>{t.memory}</span>
          <strong>
            {memory} {t.gib}
          </strong>
        </div>
      </section>

      <section className="studio-card local-catalogue">
        <h2>{t.catalogLabel}</h2>
        {scenario === "offline" && <p>{t.catalogFallback}</p>}
        <label className="local-search">
          <Search size={18} aria-hidden />
          <input
            type="search"
            aria-label={t.modelSearch}
            placeholder={t.modelSearch}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
        {matching.length ? (
          <>
            <select
              id={tagId}
              aria-label={t.smallerTag}
              value={
                matching.some(({ name }) => name === selected.name)
                  ? selected.name
                  : ""
              }
              onChange={(event) => setTag(event.target.value)}
            >
              <option value="" disabled>
                {t.smallerTag}
              </option>
              {matching.map(({ name, size }) => (
                <option key={name} value={name}>
                  {name} · {size} {t.gib}
                </option>
              ))}
            </select>
            {matching.includes(selected) && (
              <div className="local-actions">
                {selected.size > disk && (
                  <p className="text-danger">{t.diskLimit}</p>
                )}
                {selected.memory > memory && <p>{t.memoryLimit}</p>}
                <Button
                  disabled={
                    !runtimeReady ||
                    selected.size > disk ||
                    models.some(
                      (model) =>
                        model.name === selected.name && model.state !== "error",
                    )
                  }
                  variant={selected.memory > memory ? "secondary" : "primary"}
                  onClick={download}
                >
                  <Download size={16} aria-hidden />
                  {selected.memory > memory
                    ? t.downloadAnyway
                    : t.modelDownload}
                </Button>
              </div>
            )}
          </>
        ) : (
          <p>{t.emptyTitle}</p>
        )}
      </section>

      <section className="studio-card local-installed">
        <h2>{t.installedModels}</h2>
        {models.length === 0 ? (
          <p>{t.noInstalledModels}</p>
        ) : (
          <ul className="local-model-list">
            {models.map((model) => {
              const inTransfer =
                model.state === "downloading" || model.state === "paused";
              return (
                <li key={model.name}>
                  <div className="local-model-detail">
                    <code>{model.name}</code>
                    <Status
                      tone={
                        model.state === "error"
                          ? "error"
                          : model.state === "running"
                            ? "done"
                            : model.state === "downloading"
                              ? "running"
                              : "idle"
                      }
                    >
                      {t[modelLabels[model.state]]}
                    </Status>
                  </div>
                  {model.message && <p>{model.message}</p>}
                  {inTransfer ? (
                    <>
                      <label className="local-progress">
                        <span>
                          {(Number(model.completed ?? 0) / gib).toFixed(1)} /{" "}
                          {(Number(model.total ?? 0) / gib).toFixed(1)} {t.gib}
                        </span>
                        <progress max={1} value={model.progress ?? undefined} />
                      </label>
                      <div className="studio-actions">
                        <Button
                          variant="secondary"
                          onClick={() =>
                            changeModel(
                              model.name,
                              model.state === "paused"
                                ? "downloading"
                                : "paused",
                            )
                          }
                        >
                          {model.state === "paused" ? t.resume : t.pause}
                        </Button>
                        <Button
                          variant="quiet"
                          onClick={() =>
                            setModels((current) =>
                              current.filter(({ name }) => name !== model.name),
                            )
                          }
                        >
                          {t.cancel}
                        </Button>
                      </div>
                    </>
                  ) : (
                    <Button
                      variant="quiet"
                      onClick={() => setRemove(model.name)}
                    >
                      {t.remove}
                    </Button>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section className="studio-card local-log">
        <h2>{t.logLabel}</h2>
        <div role="log" aria-label={t.logLabel}>
          {runtime === "managed" ? t.runtimeLogStarted : t.runtimeLogEmpty}
        </div>
      </section>

      <Dialog.Root
        open={remove !== null}
        onOpenChange={(open) => {
          if (!open) setRemove(null);
        }}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="studio-overlay" />
          <Dialog.Content className="studio-dialog">
            <Dialog.Title>{t.confirmRemove}</Dialog.Title>
            <Dialog.Description>
              {t.removeNote} <code>{remove}</code>
            </Dialog.Description>
            <div className="studio-actions">
              <Dialog.Close asChild>
                <Button variant="secondary">{t.cancel}</Button>
              </Dialog.Close>
              <Button
                variant="danger"
                onClick={() => {
                  setModels((current) =>
                    current.filter(({ name }) => name !== remove),
                  );
                  setRemove(null);
                }}
              >
                {t.remove}
              </Button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
