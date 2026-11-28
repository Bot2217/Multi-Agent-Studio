import "@fontsource-variable/inter";
import "@fontsource-variable/jetbrains-mono";
import "../src/foundation.css";
import "../stories/foundation-preview.css";

import type { Preview } from "@storybook/react-vite";

const preview: Preview = {
  parameters: { layout: "fullscreen" },
  globalTypes: {
    palette: {
      toolbar: {
        icon: "paintbrush",
        items: [{ value: "graphite", title: "Графит" }, { value: "warm", title: "Тёплая" }],
        dynamicTitle: true,
      },
    },
    mode: {
      toolbar: {
        icon: "mirror",
        items: [
          { value: "auto", title: "Авто" },
          { value: "light", title: "Светлая" },
          { value: "dark", title: "Тёмная" },
        ],
        dynamicTitle: true,
      },
    },
    locale: {
      toolbar: {
        icon: "globe",
        items: [{ value: "ru", title: "Русский" }, { value: "en", title: "English" }],
        dynamicTitle: true,
      },
    },
  },
  initialGlobals: { palette: "graphite", mode: "dark", locale: "ru" },
  decorators: [
    (Story, { globals }) => {
      document.documentElement.dataset.palette = globals.palette;
      document.documentElement.dataset.mode = globals.mode;
      document.documentElement.lang = globals.locale;
      return <Story />;
    },
  ],
};

export default preview;
