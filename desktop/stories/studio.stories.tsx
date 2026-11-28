import type { Meta, StoryObj } from "@storybook/react-vite";
import { Studio } from "../src/shell/studio";

const meta = {
  id: "ulei-studio",
  title: "Улей/Студия",
  component: Studio,
  render: (args, { globals }) => (
    <Studio
      key={`${globals.locale}-${globals.mode}-${globals.palette}`}
      {...args}
      initialLocale={globals.locale}
      initialMode={globals.mode}
      initialPalette={globals.palette}
    />
  ),
} satisfies Meta<typeof Studio>;

export default meta;
type Story = StoryObj<typeof meta>;
export const Shell: Story = { name: "Оболочка" };
export const Onboarding: Story = {
  name: "Первый запуск",
  args: { initialOnboarding: true },
};
export const EngineDown: Story = {
  name: "Движок недоступен",
  args: { engineUnavailable: true },
};
export const Update: Story = {
  name: "Обновление",
  args: { updateAvailable: true },
};

export const LocalModels: Story = {
  name: "Локальные модели",
  args: { initialScreen: "local" },
};
export const LocalModelsOffline: Story = {
  name: "Локальные модели без сети",
  args: { initialScreen: "local", localScenario: "offline" },
};
export const LocalModelsMissing: Story = {
  name: "Ollama не установлена",
  args: { initialScreen: "local", localScenario: "missing" },
};
export const LocalModelsPortBusy: Story = {
  name: "Порт Ollama занят",
  args: { initialScreen: "local", localScenario: "port" },
};
export const LocalModelsUnsupported: Story = {
  name: "Нет сборки Ollama",
  args: { initialScreen: "local", localScenario: "unsupported" },
};
