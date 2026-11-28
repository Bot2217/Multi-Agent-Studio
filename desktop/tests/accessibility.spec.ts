import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { join } from "node:path";

test.describe.configure({ mode: "parallel" });

const story = (name: string, globals: string) =>
  `/iframe.html?id=ulei-studio--${name}&globals=${globals}`;

for (const [index, theme] of [
  "palette:graphite;mode:dark",
  "palette:graphite;mode:light",
  "palette:warm;mode:dark",
  "palette:warm;mode:light",
].entries()) {
  for (const [width, height] of [
    [1200, 800],
    [880, 640],
  ]) {
    test(`main sections fit ${width}×${height} in ${theme}`, async ({
      page,
    }) => {
      await page.setViewportSize({ width, height });
      await page.emulateMedia({ reducedMotion: "reduce" });
      const locale = (index + (width === 880 ? 1 : 0)) % 2 === 0 ? "ru" : "en";
      for (const screen of [
        "shell",
        "agents",
        "models",
        "local-models",
        "files-long",
        "mcp-long",
      ]) {
        await page.goto(story(screen, `${theme};locale:${locale}`));
        await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
        await expect(page.locator("html")).toHaveAttribute("lang", locale);
        expect(
          await page.evaluate(() => document.documentElement.scrollWidth),
          screen,
        ).toBe(width);
        const { violations } = await new AxeBuilder({ page }).analyze();
        expect(
          violations.map(({ id }) => id),
          screen,
        ).toEqual([]);
        const output = process.env.ULEI_SCREENSHOTS;
        if (screen === "shell" && output) {
          await page.evaluate(() => document.fonts.ready);
          await page.screenshot({
            path: join(
              output,
              `ulei-studio-${theme.replace(/[:;]/g, "-")}-${width}.png`,
            ),
          });
        }
      }
    });
  }
}

test("command palette filters, navigates and restores focus", async ({
  page,
}) => {
  await page.goto(story("shell", "palette:graphite;mode:dark;locale:ru"));
  const trigger = page.getByRole("button", { name: "Перейти к разделу" });
  await trigger.press("Control+k");
  const search = page.getByRole("searchbox", { name: "Поиск разделов" });
  await expect(search).toBeFocused();
  await search.fill("Локальные");
  await search.press("Enter");
  await expect(page.getByRole("dialog")).toBeHidden();
  await expect(
    page.getByRole("heading", { level: 1, name: "Локальные модели" }),
  ).toBeFocused();

  await trigger.click();
  await expect(search).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(trigger).toBeFocused();
});

test("keyboard launch respects missing credentials", async ({ page }) => {
  await page.goto(story("run-no-keys", "palette:graphite;mode:dark;locale:ru"));
  const task = page.getByRole("textbox", { name: "Что сделаем?" });
  await task.fill("Пример");
  await task.press("Control+Enter");
  await expect(
    page.getByRole("button", { name: "Посмотреть запуск" }),
  ).toBeDisabled();
  await expect(page.getByRole("button", { name: "Остановить" })).toHaveCount(0);
  await page.getByRole("button", { name: "Добавить ключ" }).click();
  await expect(
    page.getByRole("heading", { name: "Настройки", level: 1 }),
  ).toBeVisible();
});
