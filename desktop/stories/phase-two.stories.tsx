import type { Meta, StoryObj } from "@storybook/react-vite";
import { useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { Button } from "../src/components/ui/button";
import { StatePanel } from "../src/components/ui/state-panel";
import type { Locale } from "../src/locales";
import "../src/shell/studio.css";
import "../src/shell/studio-sections.css";
import "./phase-two.css";

const copy = {
  ru: {
    marker: "Фаза 2 · Концепция",
    teams: "Команды",
    agents: "Роли",
    add: "Добавить роль",
    remove: "Убрать",
    earlier: "Раньше",
    later: "Позже",
    wave: "Волна",
    noModel: "Модель не выбрана",
    knowledge: "Папка знаний",
    noFiles: "В папке пока нет документов",
    indexing: "Идёт индексация",
    indexError: "Не удалось прочитать документ",
    ready: "Готово",
    waiting: "Ожидает",
    running: "Работает",
    board: "Доска роя",
    move: "Переместить роль",
    child: "Вложенные шаги",
    none: "Добавь первую роль",
    noRoles: "Команда пуста",
    pro: "Улей Pro",
    proDescription: "Платное расширение к открытому ядру Улья.",
    restore: "Восстановить покупку",
    restorePrototype: "Здесь появится результат проверки покупки.",
    license: "Лицензия",
    roleTitle: ["Разработчик", "Ревьюер", "Исследователь"],
    actions: ["Читает структуру проекта", "Собирает сводку"],
  },
  en: {
    marker: "Phase 2 · Concept",
    teams: "Teams",
    agents: "Roles",
    add: "Add role",
    remove: "Remove",
    earlier: "Move up",
    later: "Move down",
    wave: "Wave",
    noModel: "No model selected",
    knowledge: "Knowledge folder",
    noFiles: "There are no documents in this folder",
    indexing: "Indexing",
    indexError: "Could not read the document",
    ready: "Done",
    waiting: "Waiting",
    running: "Running",
    board: "Team board",
    move: "Move role",
    child: "Nested steps",
    none: "Add the first role",
    noRoles: "The team is empty",
    pro: "Ulei Pro",
    proDescription: "A paid extension for the open Ulei core.",
    restore: "Restore purchase",
    restorePrototype: "The purchase check will appear here.",
    license: "License",
    roleTitle: ["Developer", "Reviewer", "Researcher"],
    actions: ["Read the project structure", "Compile summary"],
  },
};

type Concept = "teams" | "knowledge" | "board" | "pro";
type Scenario = "empty" | "single" | "long" | "missing" | "indexing" | "error";
type Text = typeof copy.ru;

function ConceptFrame({
  title,
  t,
  children,
}: {
  title: string;
  t: Text;
  children: ReactNode;
}) {
  return (
    <main className="studio-content concept-page">
      <div className="studio-page-heading">
        <p>{t.marker}</p>
        <h1>{title}</h1>
      </div>
      {children}
    </main>
  );
}

function TeamConcept({ t, scenario }: { t: Text; scenario?: Scenario }) {
  const count =
    scenario === "empty"
      ? 0
      : scenario === "single" || scenario === "missing"
        ? 1
        : scenario === "long"
          ? 12
          : 3;
  const [roles, setRoles] = useState(() =>
    Array.from({ length: count }, (_, id) => ({
      id,
      wave: 1 + Math.floor(id / 2),
    })),
  );
  const [nextId, setNextId] = useState(count);
  function move(index: number, offset: number) {
    const next = [...roles];
    [next[index], next[index + offset]] = [next[index + offset], next[index]];
    setRoles(next);
  }
  return (
    <ConceptFrame t={t} title={t.teams}>
      <section className="studio-card studio-section-stack">
        <div className="studio-section-heading">
          <h2>{t.agents}</h2>
          <Button
            onClick={() => {
              setRoles([...roles, { id: nextId, wave: 1 }]);
              setNextId(nextId + 1);
            }}
          >
            {t.add}
          </Button>
        </div>
        {!roles.length && <StatePanel title={t.noRoles} description={t.none} />}
        <ol className="concept-list">
          {roles.map(({ id, wave }, index) => (
            <li key={id} className="concept-row">
              <div>
                <strong>
                  {t.roleTitle[id % 3]}
                  {id > 2 ? ` · ${id + 1}` : ""}
                </strong>
                <p>
                  {scenario === "missing" && id === 0
                    ? t.noModel
                    : "gemini-2.5-flash"}
                </p>
              </div>
              <label>
                {t.wave}
                <input
                  type="number"
                  min={1}
                  value={wave}
                  onChange={(event) =>
                    setRoles(
                      roles.map((role) =>
                        role.id === id
                          ? {
                              ...role,
                              wave: Math.max(
                                1,
                                event.target.valueAsNumber || 1,
                              ),
                            }
                          : role,
                      ),
                    )
                  }
                />
              </label>
              <div className="studio-actions">
                <Button
                  variant="quiet"
                  disabled={index === 0}
                  onClick={() => move(index, -1)}
                >
                  {t.earlier}
                </Button>
                <Button
                  variant="quiet"
                  disabled={index === roles.length - 1}
                  onClick={() => move(index, 1)}
                >
                  {t.later}
                </Button>
                <Button
                  variant="quiet"
                  onClick={() =>
                    setRoles(roles.filter((role) => role.id !== id))
                  }
                >
                  {t.remove}
                </Button>
              </div>
            </li>
          ))}
        </ol>
      </section>
    </ConceptFrame>
  );
}

function KnowledgeConcept({ t, scenario }: { t: Text; scenario?: Scenario }) {
  const files = Array.from(
    { length: scenario === "long" ? 42 : 2 },
    (_, index) => `notes-${index + 1}.md`,
  );
  const state =
    scenario === "indexing"
      ? t.indexing
      : scenario === "error"
        ? t.indexError
        : t.ready;
  return (
    <ConceptFrame t={t} title={t.knowledge}>
      <section className="studio-card studio-section-stack">
        <code>~/work/demo/knowledge</code>
        <div role="status">{scenario === "empty" ? t.noFiles : state}</div>
        {scenario === "indexing" && <progress aria-label={t.indexing} />}
        {scenario !== "empty" && (
          <ul className="concept-list">
            {files.map((file, index) => (
              <li className="concept-row" key={file}>
                <code>{file}</code>
                <span>{index === 0 ? state : t.ready}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </ConceptFrame>
  );
}

function BoardConcept({ t }: { t: Text }) {
  const [stages, setStages] = useState([1, 0, 2]);
  const columns = [t.waiting, t.running, t.ready];
  const focusRole = useRef<number | null>(null);
  const cardControls = useRef<Array<HTMLSelectElement | null>>([]);
  useLayoutEffect(() => {
    if (focusRole.current === null) return;
    cardControls.current[focusRole.current]?.focus();
    focusRole.current = null;
  }, [stages]);
  return (
    <ConceptFrame t={t} title={t.board}>
      <div className="concept-board">
        {columns.map((name, column) => (
          <section className="studio-card studio-section-stack" key={name}>
            <h2>{name}</h2>
            {stages.map(
              (stage, role) =>
                stage === column && (
                  <div className="concept-role" key={role}>
                    <strong>{t.roleTitle[role]}</strong>
                    {column === 1 && (
                      <details open>
                        <summary>{t.child}</summary>
                        <ul>
                          {t.actions.map((action) => (
                            <li key={action}>{action}</li>
                          ))}
                        </ul>
                      </details>
                    )}
                    <label className="studio-select">
                      {t.move}
                      <select
                        aria-label={`${t.move} · ${t.roleTitle[role]}`}
                        ref={(node) => {
                          cardControls.current[role] = node;
                        }}
                        value={stage}
                        onChange={(event) => {
                          focusRole.current = role;
                          setStages(
                            stages.map((current, index) =>
                              index === role
                                ? Number(event.target.value)
                                : current,
                            ),
                          );
                        }}
                      >
                        {columns.map((label, index) => (
                          <option key={label} value={index}>
                            {label}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>
                ),
            )}
          </section>
        ))}
      </div>
    </ConceptFrame>
  );
}

function ProConcept({ t }: { t: Text }) {
  const [restore, setRestore] = useState(false);
  return (
    <ConceptFrame t={t} title={t.pro}>
      <section className="studio-card studio-section-stack">
        <h2>{t.license}</h2>
        <p>{t.proDescription}</p>
        <code>{"{{ЦЕНА}}"}</code>
        <Button variant="secondary" onClick={() => setRestore(true)}>
          {t.restore}
        </Button>
        {restore && <p role="status">{t.restorePrototype}</p>}
      </section>
    </ConceptFrame>
  );
}

function PhaseTwo({
  locale,
  concept,
  scenario,
}: {
  locale: Locale;
  concept: Concept;
  scenario?: Scenario;
}) {
  const t = copy[locale];
  if (concept === "teams") return <TeamConcept t={t} scenario={scenario} />;
  if (concept === "knowledge")
    return <KnowledgeConcept t={t} scenario={scenario} />;
  if (concept === "board") return <BoardConcept t={t} />;
  return <ProConcept t={t} />;
}

const meta = {
  id: "ulei-phase-two",
  title: "Улей/Фаза 2 · Концепции",
  component: PhaseTwo,
  args: { locale: "ru", concept: "teams" },
  render: (args, { globals }) => (
    <PhaseTwo key={globals.locale} {...args} locale={globals.locale} />
  ),
} satisfies Meta<typeof PhaseTwo>;
export default meta;
type Story = StoryObj<typeof meta>;

export const Team: Story = { name: "Сборка команды" };
export const EmptyTeam: Story = {
  name: "Пустая команда",
  args: { scenario: "empty" },
};
export const SingleRole: Story = {
  name: "Одна роль",
  args: { scenario: "single" },
};
export const LongTeam: Story = {
  name: "Длинная команда",
  args: { scenario: "long" },
};
export const RoleWithoutModel: Story = {
  name: "Роль без модели",
  args: { scenario: "missing" },
};
export const Knowledge: Story = {
  name: "Папка знаний",
  args: { concept: "knowledge" },
};
export const EmptyKnowledge: Story = {
  name: "Пустая папка знаний",
  args: { concept: "knowledge", scenario: "empty" },
};
export const Indexing: Story = {
  name: "Индексация",
  args: { concept: "knowledge", scenario: "indexing" },
};
export const IndexError: Story = {
  name: "Ошибка чтения документа",
  args: { concept: "knowledge", scenario: "error" },
};
export const LongKnowledge: Story = {
  name: "Длинный список документов",
  args: { concept: "knowledge", scenario: "long" },
};
export const Board: Story = {
  name: "Рой и вложенные шаги",
  args: { concept: "board" },
};
export const Pro: Story = { name: "Улей Pro", args: { concept: "pro" } };
