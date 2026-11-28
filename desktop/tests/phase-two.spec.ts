import AxeBuilder from "@axe-core/playwright";
import { test, expect } from "@playwright/test";

const story = (name: string) =>
  `/iframe.html?id=ulei-phase-two--${name}&globals=locale:ru;mode:dark`;

test("empty team can add roles and assign a wave", async ({ page }) => {
  await page.goto(story("empty-team"));
  await page.getByRole("button", { name: "Добавить роль" }).click();
  const wave = page.getByRole("spinbutton", { name: "Волна" });
  await wave.fill("2");
  await expect(wave).toHaveValue("2");
  await expect(page.getByText("Команда пуста")).toHaveCount(0);
});

test("board card can move without dragging", async ({ page }) => {
  await page.setViewportSize({ width: 880, height: 640 });
  await page.goto(story("board"));
  const running = page.locator("section").filter({
    has: page.getByRole("heading", { name: "Работает", exact: true }),
  });
  await expect(running.getByText("Разработчик")).toBeVisible();
  const select = running.getByRole("combobox");
  await select.focus();
  await select.selectOption("2");
  await expect(running.getByText("Разработчик")).toHaveCount(0);
  const done = page.locator("section").filter({
    has: page.getByRole("heading", { name: "Готово", exact: true }),
  });
  await expect(done.getByText("Разработчик")).toBeVisible();
  await expect(
    done.getByRole("combobox", { name: /Разработчик/ }),
  ).toBeFocused();
  expect(
    (await new AxeBuilder({ page }).analyze()).violations.map(({ id }) => id),
  ).toEqual([]);
});
