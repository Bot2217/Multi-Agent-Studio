import { readFileSync, writeFileSync } from "node:fs";

const desktop = new URL("../", import.meta.url);
const tokens = JSON.parse(readFileSync(new URL("design/tokens.json", desktop), "utf8"));
const output = new URL("src/tokens.css", desktop);

function variables(group, prefix = "") {
  return Object.entries(group).flatMap(([name, entry]) => {
    const key = prefix ? `${prefix}-${name}` : name;
    if (!("$value" in entry)) return variables(entry, key);
    let value = entry.$value;
    if (entry.$type === "cubicBezier") value = `cubic-bezier(${value.join(", ")})`;
    if (entry.$type === "fontFamily") value = JSON.stringify(value);
    return `  --ulei-${key}: ${value};`;
  });
}

function rule(selector, declarations) {
  return `${selector} {\n${declarations.join("\n")}\n}`;
}

const { color, ...shared } = tokens;
const rules = [rule(":root", variables(shared))];
const automaticDark = [];
for (const [palette, modes] of Object.entries(color)) {
  for (const [mode, values] of Object.entries(modes)) {
    const target = `[data-palette="${palette}"]`;
    const manual = `${target}[data-mode="${mode}"]`;
    const auto = `${target}[data-mode="auto"]`;
    const declarations = [`  color-scheme: ${mode};`, ...variables(values, "color")];
    if (mode === "light") {
      rules.push(rule(palette === "graphite" ? `:root, ${auto}, ${manual}` : `${auto}, ${manual}`, declarations));
    } else {
      rules.push(rule(manual, declarations));
      automaticDark.push(rule(palette === "graphite" ? `:root:not([data-mode]), ${auto}` : auto, declarations));
    }
  }
}
rules.push(`@media (prefers-color-scheme: dark) {\n${automaticDark.join("\n\n").split("\n").map((line) => line && `  ${line}`).join("\n")}\n}`);
const css = `/* Generated from design/tokens.json by npm run tokens. */\n\n${rules.join("\n\n")}\n`;

if (process.argv.includes("--check")) {
  if (readFileSync(output, "utf8") !== css) {
    console.error("tokens.css is out of date. Run npm run tokens.");
    process.exitCode = 1;
  }
} else {
  writeFileSync(output, css);
}
