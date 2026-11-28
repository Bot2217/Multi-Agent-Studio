import type { Meta, StoryObj } from "@storybook/react-vite";
import { ArrowUpRight, Play, RotateCw, Square } from "lucide-react";
import { useRef, useState } from "react";
import { Button } from "../src/components/ui/button";
import { Field } from "../src/components/ui/field";
import { StatePanel } from "../src/components/ui/state-panel";
import { Status } from "../src/components/ui/status";
import { getMessages, type Locale, type Messages } from "../src/locales";

type FoundationProps = { locale: Locale; invalid?: boolean };
const swatches = [
  { token: "bg", label: "canvas" },
  { token: "surface", label: "surface" },
  { token: "accent", label: "accent" },
  { token: "ink", label: "text" },
] as const;

function FolderForm({ t, invalid }: { t: Messages; invalid?: boolean }) {
  const [value, setValue] = useState(invalid ? "" : "~/work/demo");
  const [submitted, setSubmitted] = useState(Boolean(invalid));
  const runButton = useRef<HTMLButtonElement>(null);
  const [status, setStatus] = useState<"idle" | "running" | "stopped">("idle");

  return (
    <form
      className="foundation-form"
      onSubmit={(event) => {
        event.preventDefault();
        if (status === "running") return;
        setSubmitted(true);
        if (value.trim()) setStatus("running");
      }}
    >
      <Field
        label={t.projectFolder}
        value={value}
        onChange={(event) => {
          setValue(event.target.value);
          setStatus("idle");
        }}
        placeholder="~/work/demo"
        hint={t.folderHint}
        error={submitted && !value.trim() ? t.folderError : undefined}
      />
      <div className="foundation-actions">
        <Button ref={runButton} type="submit" aria-disabled={status === "running"}>
          <Play size={16} aria-hidden />{t.run}
        </Button>
        <Button
          variant="secondary"
          onClick={() => {
            setValue("~/work/demo");
            setStatus("idle");
          }}
        >
          {t.insertExample}
        </Button>
        <Button
          variant="danger"
          disabled={status !== "running"}
          onClick={() => {
            setStatus("stopped");
            runButton.current?.focus();
          }}
        >
          <Square size={16} aria-hidden />{t.stop}
        </Button>
      </div>
      <div role="status"><Status tone={status === "stopped" ? "idle" : status}>{t[status]}</Status></div>
    </form>
  );
}

function Foundation({ locale, invalid }: FoundationProps) {
  const t = getMessages(locale);
  const [engineReady, setEngineReady] = useState(false);
  return (
    <main className="foundation-board">
      <header className="foundation-heading">
        <div className="foundation-brand">
          <svg aria-hidden="true" width="32" height="32" viewBox="0 0 32 32">
            <path fill="#c2f24e" d="M16 4.2 21.2 7.2v6L16 16.2 10.8 13.2v-6z" />
            <path fill="#e0a15a" d="M22.4 8.4 27.6 11.4v6l-5.2 3-5.2-3v-6z" />
            <path fill="#9be0b8" d="M9.6 8.4 14.8 11.4v6l-5.2 3-5.2-3v-6z" />
            <path fill="#eef0f4" d="M16 15.6 21.2 18.6v6L16 27.6 10.8 24.6v-6z" />
          </svg>
          {t.brand}
        </div>
        <h1>{t.foundation}</h1>
      </header>

      <section className="foundation-palette" aria-labelledby="foundation-colors">
        <h2 id="foundation-colors">{t.colors}</h2>
        <ul className="foundation-swatches">
          {swatches.map(({ token, label }) => (
            <li key={token}>
              <div className="foundation-sample" data-token={token} />
              <span>{t[label]}</span>
              <code>{token}</code>
            </li>
          ))}
        </ul>
      </section>

      <div className="foundation-grid">
        <section className="foundation-card" aria-labelledby="foundation-controls">
          <h2 id="foundation-controls">{t.controls}</h2>
          <FolderForm key={String(invalid)} t={t} invalid={invalid} />
          <div className="foundation-statuses">
            <Status tone="running">{t.running}</Status>
            <Status tone="done">{t.done}</Status>
            <Status tone="error">{t.failed}</Status>
          </div>
        </section>
        <section className="foundation-card foundation-states" aria-labelledby="foundation-states">
          <h2 id="foundation-states">{t.states}</h2>
          <StatePanel
            title={t.emptyTitle}
            description={t.emptyDescription}
            action={
              <Button asChild variant="quiet">
                <a href="#foundation-controls">{t.details}<ArrowUpRight size={16} aria-hidden /></a>
              </Button>
            }
          />
          <StatePanel
            kind={engineReady ? "success" : "error"}
            title={engineReady ? t.done : t.errorTitle}
            description={engineReady ? t.engineReady : t.errorDescription}
            action={
              <Button variant="secondary" onClick={() => setEngineReady(true)}>
                <RotateCw size={16} aria-hidden />{t.retry}
              </Button>
            }
            announce
          />
        </section>
      </div>
    </main>
  );
}

const meta = {
  title: "Улей/Основа",
  id: "ulei-foundations",
  component: Foundation,
  args: { locale: "ru" },
  render: (args, { globals }) => <Foundation {...args} locale={globals.locale} />,
} satisfies Meta<typeof Foundation>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Overview: Story = { name: "Обзор" };
export const InvalidField: Story = { name: "Ошибка поля", args: { invalid: true } };
