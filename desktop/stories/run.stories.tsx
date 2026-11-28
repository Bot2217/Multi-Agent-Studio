import type { Meta, StoryObj } from "@storybook/react-vite";
import example from "../src/contract/fixtures/example.json";
import { getMessages } from "../src/locales";
import { RunTimeline } from "../src/shell/run-timeline";
import "../src/shell/studio.css";

const meta = {
  id: "ulei-run",
  title: "Улей/События запуска",
  component: RunTimeline,
  args: { frames: example, t: getMessages("ru") },
  render: (args, { globals }) => (
    <main className="studio-content">
      <RunTimeline
        key={globals.locale}
        {...args}
        t={getMessages(globals.locale)}
      />
    </main>
  ),
} satisfies Meta<typeof RunTimeline>;
export default meta;
type Story = StoryObj<typeof meta>;
export const ContractExample: Story = { name: "Пример из контракта" };
export const UnknownEvent: Story = {
  name: "Неизвестный кадр",
  args: {
    frames: [
      ...example.slice(0, 2),
      { version: "2", type: "future" },
      ...example.slice(2),
    ],
  },
};
export const Stopped: Story = {
  name: "Остановлено",
  args: {
    frames: [
      ...example.slice(0, 3),
      { version: "1", type: "done", task_id: "task_01", outcome: "stopped" },
    ],
  },
};
