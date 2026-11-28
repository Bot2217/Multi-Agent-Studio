import { FileText } from "lucide-react";
import { useId, useState } from "react";
import { Button } from "../components/ui/button";
import { Field } from "../components/ui/field";
import { StatePanel } from "../components/ui/state-panel";
import type { Messages } from "../locales";
import data from "./fixtures/studio-data.json";

export const roleDefaults = data.agents;
export type PreviewRole = (typeof roleDefaults)[number];
const models = data.models;
const bills = {
  free: "billFree",
  freemium: "billFreemium",
  paid: "billPaid",
  local: "billLocal",
  unknown: "billUnknown",
} as const;
const filters = {
  all: "allModels",
  free: "freeModels",
  paid: "paidModels",
  local: "localModels",
} as const;
type Filter = keyof typeof filters;

export function AgentsScreen({
  roles,
  setRoles,
  t,
}: {
  roles: PreviewRole[];
  setRoles: (roles: PreviewRole[]) => void;
  t: Messages;
}) {
  function update(id: string, change: Partial<PreviewRole>) {
    setRoles(
      roles.map((role) => (role.id === id ? { ...role, ...change } : role)),
    );
  }
  return (
    <div className="studio-section-stack">
      {!roles.length && (
        <StatePanel title={t.agentsScreen} description={t.agentsEmpty} />
      )}
      {roles.length > 0 && !roles.some(({ enabled }) => enabled) && (
        <p className="studio-notice">{t.noEnabledRoles}</p>
      )}
      {roles.map((role) => (
        <section className="studio-card studio-section-stack" key={role.id}>
          <div className="studio-section-heading">
            <div>
              <h2>{role.id in t ? t[role.id as keyof Messages] : role.name}</h2>
              <p>{role.description}</p>
            </div>
            <label className="studio-check">
              <input
                type="checkbox"
                checked={role.enabled}
                onChange={(event) =>
                  update(role.id, { enabled: event.target.checked })
                }
              />
              {t.enabledRole}
            </label>
          </div>
          <div className="studio-form-options">
            <ModelPicker
              value={role.model}
              onChange={(value) => update(role.id, { model: value })}
              t={t}
            />
            <label className="studio-select">
              {t.temperature} · {role.temperature.toFixed(1)}
              <input
                type="range"
                min={0}
                max={2}
                step={0.1}
                value={role.temperature}
                onChange={(event) =>
                  update(role.id, { temperature: event.target.valueAsNumber })
                }
              />
              <span>{t.temperatureHelp}</span>
            </label>
          </div>
          {role.recommended.length > 0 && (
            <div className="studio-recommendations">
              <p>{t.recommended}</p>
              {role.recommended.map((id) => (
                <Button
                  key={id}
                  variant="secondary"
                  onClick={() => update(role.id, { model: id })}
                >
                  {models.find((model) => model.litellm === id)?.name ?? id}
                </Button>
              ))}
            </div>
          )}
          <Button
            variant="quiet"
            onClick={() => {
              const original = roleDefaults.find(({ id }) => id === role.id);
              if (original) update(role.id, original);
            }}
          >
            {t.resetDefaults}
          </Button>
        </section>
      ))}
    </div>
  );
}

function ModelPicker({
  value,
  onChange,
  t,
}: {
  value: string;
  onChange: (value: string) => void;
  t: Messages;
}) {
  const [query, setQuery] = useState("");
  const available = models.filter(({ name, litellm }) =>
    `${name} ${litellm}`.toLowerCase().includes(query.toLowerCase()),
  );
  return (
    <div className="studio-section-stack">
      <Field
        label={t.modelSearch}
        type="search"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
      />
      <label className="studio-select">
        {t.modelLabel}
        <select
          value={value}
          onChange={(event) => onChange(event.target.value)}
        >
          {!available.some(({ litellm }) => litellm === value) && (
            <option value={value}>{value}</option>
          )}
          {available.map(({ litellm, name, billing }) => (
            <option key={litellm} value={litellm ?? ""}>
              {name}
              {billing === "local"
                ? ` · Ollama (${t.billLocal.toLowerCase()})`
                : ""}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}

export function ModelsScreen({ t }: { t: Messages }) {
  const [filter, setFilter] = useState<Filter>("all");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const filterId = useId();
  const list = models.filter(
    ({ name, provider, litellm, billing }) =>
      (filter === "all" ||
        filter === billing ||
        (filter === "free" && billing === "freemium")) &&
      `${name} ${provider} ${litellm}`
        .toLowerCase()
        .includes(query.trim().toLowerCase()),
  );
  const model = list.find(({ litellm }) => litellm === selected);
  return (
    <section className="studio-card studio-section-stack">
      <div className="studio-form-options">
        <Field
          label={t.modelSearch}
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <label className="studio-select" htmlFor={filterId}>
          {t.access}
          <select
            id={filterId}
            value={filter}
            onChange={(event) => setFilter(event.target.value as Filter)}
          >
            {Object.entries(filters).map(([value, key]) => (
              <option key={value} value={value}>
                {t[key]}
              </option>
            ))}
          </select>
        </label>
      </div>
      <p role="status">
        {t.shown} {list.length} {t.ofTotal} {models.length}
      </p>
      {list.length ? (
        <div
          className="studio-table-wrap"
          tabIndex={0}
          aria-label={t.modelsScreen}
        >
          <table className="studio-table">
            <thead>
              <tr>
                {[t.modelLabel, t.provider, t.access, t.price, t.context].map(
                  (label) => (
                    <th key={label} scope="col">
                      {label}
                    </th>
                  ),
                )}
              </tr>
            </thead>
            <tbody>
              {list.map((row) => (
                <tr key={row.litellm}>
                  <th scope="row">
                    <Button
                      variant="quiet"
                      aria-expanded={selected === row.litellm}
                      onClick={() =>
                        setSelected(
                          selected === row.litellm ? null : row.litellm,
                        )
                      }
                    >
                      {row.name}
                    </Button>
                  </th>
                  <td>{row.provider}</td>
                  <td>
                    {
                      t[
                        bills[row.billing as keyof typeof bills] ??
                          "billUnknown"
                      ]
                    }
                  </td>
                  <td>
                    {row.price_status === "known" &&
                    row.price_input_per_1m !== null &&
                    row.price_output_per_1m !== null
                      ? `$${row.price_input_per_1m} / $${row.price_output_per_1m}`
                      : t.unknownValue}
                  </td>
                  <td>
                    {row.context && row.context !== "unknown"
                      ? row.context
                      : t.unknownValue}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <StatePanel
          title={t.noResults}
          description=""
          action={
            <Button
              variant="secondary"
              onClick={() => {
                setQuery("");
                setFilter("all");
              }}
            >
              {t.allModels}
            </Button>
          }
        />
      )}
      {model && (
        <div className="studio-card studio-section-stack">
          <h2>{model.name}</h2>
          <code>{model.litellm}</code>
          <p>{model.best_for}</p>
          {model.source?.startsWith("https://") && (
            <a href={model.source} target="_blank" rel="noreferrer">
              {t.source}
            </a>
          )}
          <p>
            {t.verified} · {model.last_verified ?? t.unknownValue}
          </p>
        </div>
      )}
    </section>
  );
}

export type FilesScenario = "normal" | "empty" | "missing" | "error" | "long";
const sampleFiles = [
  {
    name: "README.md",
    content: "# Example workspace\n\nA small project for the first Ulei run.",
  },
  { name: "hello.py", content: 'print("Hello, world")\n' },
  { name: "notes.md", content: "# Notes\n\nAdd project notes here." },
];
const manyFiles = Array.from({ length: 80 }, (_, index) => ({
  name: `notes/note-${String(index + 1).padStart(2, "0")}.md`,
  content: `# Note ${index + 1}`,
}));

export function FilesScreen({
  t,
  folder,
  scenario = "normal",
}: {
  t: Messages;
  folder: string;
  scenario?: FilesScenario;
}) {
  const [file, setFile] = useState<(typeof sampleFiles)[number] | null>(null);
  const files =
    scenario === "normal" ? sampleFiles : scenario === "long" ? manyFiles : [];
  return (
    <section className="studio-card studio-section-stack">
      <h2>{t.projectFolder}</h2>
      <code>{folder}</code>
      <p>{t.pathsNotice}</p>
      {files.length ? (
        <ul className="studio-file-list">
          {files.map((item) => (
            <li key={item.name}>
              <Button
                variant="quiet"
                aria-pressed={file?.name === item.name}
                onClick={() => setFile(item)}
              >
                <FileText size={18} aria-hidden />
                <code>{item.name}</code>
              </Button>
            </li>
          ))}
        </ul>
      ) : (
        <p role={scenario === "error" ? "alert" : undefined}>
          {scenario === "empty"
            ? t.filesEmpty
            : scenario === "missing"
              ? t.filesMissing
              : t.fileReadError}
        </p>
      )}
      {file && (
        <div className="studio-file-preview">
          <h2>
            {t.filePreview} · {file.name}
          </h2>
          <pre>{file.content}</pre>
        </div>
      )}
    </section>
  );
}
