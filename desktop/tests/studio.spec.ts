import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { join } from "node:path";

const preview = (
  name: string,
  globals = "palette:graphite;mode:dark;locale:ru",
) => `/iframe.html?id=ulei-studio--${name}&viewMode=story&globals=${globals}`;

for (const name of ["shell", "onboarding", "engine-down", "update"]) {
  for (const mode of ["light", "dark"]) {
    test(`${name} ${mode} at minimum width`, async ({ page }) => {
      await page.setViewportSize({ width: 880, height: 640 });
      await page.goto(preview(name, `palette:warm;mode:${mode};locale:ru`));
      await expect(
        page.getByRole(name === "update" ? "dialog" : "navigation"),
      ).toBeVisible();
      await page.evaluate(() => document.fonts.ready);
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth),
      ).toBe(880);
      const { violations } = await new AxeBuilder({ page }).analyze();
      expect(violations.map(({ id }) => id)).toEqual([]);
    });
  }
}

test("first run, validation and keyboard", async ({ page }) => {
  await page.goto(preview("onboarding"));
  await page.getByRole("button", { name: /Ключ Google/ }).click();
  await page.getByRole("button", { name: "Продолжить", exact: true }).click();
  const task = page.getByRole("textbox", { name: "Что сделаем?" });
  await expect(task).toHaveValue("Создай hello.py и запусти его");
  await task.fill("");
  await task.press("Control+Enter");
  await expect(page.getByRole("alert")).toHaveText(
    "Опиши задачу перед запуском.",
  );
  await task.fill("Пример задачи");
  await task.press("Control+Enter");
  await page.getByRole("button", { name: "Остановить" }).click();
  await expect(page.getByText("Остановлено", { exact: true })).toBeVisible();
});

test("theme, locale and navigation", async ({ page }) => {
  await page.goto(preview("shell"));
  await page.getByRole("button", { name: "Настройки", exact: true }).click();
  await page.getByLabel("Палитра").selectOption("warm");
  await page.getByLabel("Тема", { exact: true }).selectOption("light");
  await expect(page.locator("html")).toHaveAttribute("data-palette", "warm");
  await expect(page.locator("html")).toHaveAttribute("data-mode", "light");
  await page.getByLabel("Язык", { exact: true }).selectOption("en");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await page.getByRole("button", { name: "Run", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Run", exact: true }),
  ).toBeFocused();
});

test("update dismisses for this session", async ({ page }) => {
  await page.goto(preview("update"));
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toBeHidden();
  await page.getByRole("button", { name: "Настройки", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeHidden();
});

test("capture studio screens", async ({ page }) => {
  const output = process.env.ULEI_SCREENSHOTS;
  test.skip(!output, "Screenshots require an output directory.");
  for (const width of [1200, 880]) {
    await page.setViewportSize({ width, height: width === 1200 ? 800 : 640 });
    for (const name of ["shell", "onboarding"]) {
      await page.goto(preview(name));
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await page.evaluate(() => document.fonts.ready);
      await page.screenshot({
        path: join(output!, `ulei-${name}-${width}.png`),
      });
    }
  }
});

test("selected mode streams its roles and produces a downloadable report", async ({
  page,
}) => {
  await page.goto(preview("shell"));
  await page.getByRole("combobox", { name: "Режим" }).selectOption("single");
  await page.getByRole("button", { name: "Описать проект" }).click();
  await page.getByRole("button", { name: "Посмотреть запуск" }).click();
  await expect(page.getByRole("button", { name: "Остановить" })).toBeFocused();
  await expect(page.getByRole("log")).toContainText(
    "Демонстрационный шаг выполнен.",
  );
  await expect(page.getByRole("heading", { name: "Итог" })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Недавние задачи" }),
  ).toBeVisible();
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("link", { name: "Скачать отчёт" }).click(),
  ]);
  expect(download.suggestedFilename()).toBe("ulei-report.txt");
});
