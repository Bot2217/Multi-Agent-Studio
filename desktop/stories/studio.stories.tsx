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

export const Agents: Story = {
  name: "Агенты",
  args: { initialScreen: "agents" },
};

export const AgentsEmpty: Story = {
  name: "Ролей нет",
  args: { initialScreen: "agents", agentsEmpty: true },
};

export const Models: Story = {
  name: "Каталог моделей",
  args: { initialScreen: "models" },
};

export const Files: Story = {
  name: "Файлы проекта",
  args: { initialScreen: "files" },
};

export const FilesMissing: Story = {
  name: "Папка не найдена",
  args: { initialScreen: "files", filesScenario: "missing" },
};

export const FilesEmpty: Story = {
  name: "Папка пуста",
  args: { initialScreen: "files", filesScenario: "empty" },
};

export const FilesError: Story = {
  name: "Ошибка чтения",
  args: { initialScreen: "files", filesScenario: "error" },
};

export const FilesLong: Story = {
  name: "Длинный список файлов",
  args: { initialScreen: "files", filesScenario: "long" },
};

export const Settings: Story = {
  name: "Настройки",
  args: { initialScreen: "settings" },
};

export const McpChecking: Story = {
  name: "Проверка MCP",
  args: { initialScreen: "settings", mcpScenario: "checking" },
};

export const McpReady: Story = {
  name: "MCP подключён",
  args: { initialScreen: "settings", mcpScenario: "ready" },
};

export const McpError: Story = {
  name: "Ошибка MCP",
  args: { initialScreen: "settings", mcpScenario: "error" },
};

export const McpOffline: Story = {
  name: "MCP без сети",
  args: { initialScreen: "settings", mcpScenario: "offline" },
};

export const McpLong: Story = {
  name: "Длинный список инструментов MCP",
  args: { initialScreen: "settings", mcpScenario: "long" },
};
