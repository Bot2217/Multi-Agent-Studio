import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { join } from "node:path";

const story = (
  name: string,
  globals = "locale:ru;mode:dark;palette:graphite",
) => `/iframe.html?id=ulei-studio--${name}&globals=${globals}`;

test("model download can be paused, resumed and cancelled", async ({
  page,
}) => {
  await page.goto(story("local-models"));
  await expect(page.getByText("Запущена отдельно")).toBeVisible();
  await page.getByRole("button", { name: "Скачать", exact: true }).click();
  await page.getByRole("button", { name: "Пауза" }).click();
  await expect(page.getByText("Приостановлено")).toBeVisible();
  await page.getByRole("button", { name: "Возобновить" }).click();
  await expect(page.getByText("Скачивается")).toBeVisible();
  await page.getByRole("button", { name: "Отменить" }).click();
  await expect(page.getByText("Скачивается")).toHaveCount(0);
});

test("installation and removal are reversible before confirmation", async ({
  page,
}) => {
  await page.goto(story("local-models-missing"));
  await page.getByRole("button", { name: "Установить Ollama" }).click();
  await expect(page.getByRole("progressbar")).toBeVisible();
  await page.getByRole("button", { name: "Отменить" }).click();
  await expect(page.getByText("Не установлена")).toBeVisible();
  await page.goto(story("local-models"));
  await page.getByRole("button", { name: "Удалить" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(page.getByText("llama3.2:3b", { exact: true })).toBeVisible();
});

test("narrow offline preview and hardware warning", async ({ page }) => {
  await page.setViewportSize({ width: 880, height: 640 });
  await page.goto(
    story("local-models-offline", "palette:warm;mode:light;locale:ru"),
  );
  await expect(page.getByText(/Показан встроенный список/)).toBeVisible();
  await page
    .getByRole("combobox", { name: "Выбрать меньший тег" })
    .selectOption("qwen2.5-coder:32b");
  await expect(page.getByText(/может не хватить памяти/)).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(
    880,
  );
  expect(
    (await new AxeBuilder({ page }).analyze()).violations.map(({ id }) => id),
  ).toEqual([]);
  const output = process.env.ULEI_SCREENSHOTS;
  if (output)
    await page.screenshot({ path: join(output, "ulei-local-models-880.png") });
});
