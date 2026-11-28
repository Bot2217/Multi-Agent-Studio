import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const tokens: typeof import("../design/tokens.json") = JSON.parse(
  readFileSync(new URL("../design/tokens.json", import.meta.url), "utf8"),
);

const palettes = ["graphite", "warm"] as const;
const modes = ["light", "dark"] as const;
const sizes = [{ width: 1200, height: 800 }, { width: 880, height: 640 }];
const story = "/iframe.html?id=ulei-foundations--overview&viewMode=story";

for (const palette of palettes) {
  for (const mode of modes) {
    for (const { width, height } of sizes) {
      for (const locale of ["ru", "en"]) {
        test(`${palette} ${mode} at ${width}×${height} (${locale})`, async ({ page }) => {
          await page.setViewportSize({ width, height });
          await page.goto(`${story}&globals=palette:${palette};mode:${mode};locale:${locale}`);
          await expect(page.locator("html")).toHaveAttribute("lang", locale);
          await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
          const expectedColor = tokens.color[palette][mode].accent.$value;
          await expect(page.locator("html")).toHaveCSS("--ulei-color-accent", expectedColor);
          await page.evaluate(() => document.fonts.ready);
          const fits = await page.evaluate(() => {
            const root = document.documentElement;
            return root.scrollWidth <= window.innerWidth && root.scrollHeight <= window.innerHeight;
          });
          expect(fits).toBe(true);

          const { violations } = await new AxeBuilder({ page }).include("main").analyze();
          expect(violations.map(({ id }) => id)).toEqual([]);

          const output = process.env.ULEI_SCREENSHOTS;
          if (output && locale === "ru") {
            await page.screenshot({
              path: join(output, `ulei-${palette}-${mode}-${width}.png`),
              animations: "disabled",
            });
          }
        });
      }
    }
  }
}

test("automatic theme follows the system within the chosen palette", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "light" });
  await page.goto(`${story}&globals=palette:warm;mode:auto`);
  const html = page.locator("html");
  await expect(html).toHaveCSS("--ulei-color-accent", tokens.color.warm.light.accent.$value);
  await page.emulateMedia({ colorScheme: "dark" });
  await expect(html).toHaveCSS("--ulei-color-accent", tokens.color.warm.dark.accent.$value);
});

test("folder validation, keyboard controls and reconnect feedback", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto(`${story}&globals=locale:en`);
  const folder = page.getByRole("textbox", { name: "Project folder" });
  const run = page.getByRole("button", { name: "Run", exact: true });
  const stop = page.getByRole("button", { name: "Stop", exact: true });

  await folder.fill("");
  await page.keyboard.press("Enter");
  await expect(folder).toHaveAttribute("aria-invalid", "true");
  await expect(folder).toHaveAccessibleDescription("Enter a project folder.");
  await page.getByRole("button", { name: "Insert example" }).click();
  await expect(folder).toHaveValue("~/work/demo");
  await expect(folder).not.toHaveAttribute("aria-invalid");
  await folder.focus();
  await page.keyboard.press("Tab");
  await expect(run).toBeFocused();
  await expect(run).toHaveCSS("outline-style", "solid");
  await expect(run).toHaveCSS("transition-duration", "0s");
  await page.keyboard.press("Enter");
  await expect(page.getByRole("status")).toHaveText("Running");
  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  await expect(stop).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("status")).toHaveText("Stopped");
  await expect(run).toBeFocused();

  const retry = page.getByRole("button", { name: "Try again" });
  await retry.click();
  await expect(page.getByText("The engine is available again.")).toBeVisible();
  await expect(retry).toBeFocused();
});
