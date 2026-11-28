import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { join } from "node:path";

const studio = (
  screen: string,
  globals = "locale:ru;mode:dark;palette:graphite",
) => `/iframe.html?id=ulei-studio--${screen}&globals=${globals}`;

test("disabled role blocks its single-agent pipeline", async ({ page }) => {
  await page.goto(studio("agents"));
  const developer = page
    .locator("section")
    .filter({
      has: page.getByRole("heading", { name: "Разработчик", exact: true }),
    });
  await developer.getByRole("checkbox").uncheck();
  await page.getByRole("button", { name: "Запуск", exact: true }).click();
  await page.getByRole("combobox", { name: "Режим" }).selectOption("single");
  await expect(
    page.getByRole("button", { name: "Посмотреть запуск" }),
  ).toBeDisabled();
});

test("catalogue search, file preview and MCP details", async ({ page }) => {
  await page.goto(studio("models"));
  const search = page.getByRole("searchbox");
  await search.fill("no-such-model");
  await expect(page.getByText("По запросу ничего не найдено.")).toBeVisible();
  await page.getByRole("button", { name: "Все", exact: true }).click();
  await expect(page.getByRole("table")).toBeVisible();
  await page.goto(studio("files"));
  await page.getByRole("button", { name: "hello.py" }).click();
  await expect(
    page.getByText('print("Hello, world")', { exact: true }),
  ).toBeVisible();
  await page.goto(studio("mcp-ready"));
  await expect(page.getByText("Подключён", { exact: true })).toBeVisible();
  await page.getByText("Инструменты", { exact: true }).click();
  await expect(page.getByText("list_notes")).toBeVisible();
});

for (const screen of [
  "agents",
  "models",
  "files-long",
  "settings",
  "mcp-long",
]) {
  test(`${screen} accessibility at narrow width`, async ({ page }) => {
    await page.setViewportSize({ width: 880, height: 640 });
    await page.goto(studio(screen, "locale:en;mode:light;palette:warm"));
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBe(880);
    expect(
      (await new AxeBuilder({ page }).analyze()).violations.map(({ id }) => id),
    ).toEqual([]);
    const output = process.env.ULEI_SCREENSHOTS;
    if (output) {
      await page.evaluate(() => document.fonts.ready);
      await page.screenshot({ path: join(output, `ulei-${screen}-880.png`) });
    }
  });
}
