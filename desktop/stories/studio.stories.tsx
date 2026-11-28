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
