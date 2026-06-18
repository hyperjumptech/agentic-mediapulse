import { render } from "@react-email/render";
import { mkdirSync, readdirSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import * as React from "react";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const emailsDir = resolve(scriptDir, "../emails");
const outputDir = resolve(scriptDir, "../../src/templates");

function toMarkers(html: string): string {
  return html.replace(/\[\[#(\w+)\]\]/g, "<!--#$1-->").replace(/\[\[\/(\w+)\]\]/g, "<!--/$1-->");
}

mkdirSync(outputDir, { recursive: true });

const files = readdirSync(emailsDir).filter((file) => file.endsWith(".tsx"));

for (const file of files) {
  const module = await import(pathToFileURL(join(emailsDir, file)).href);
  const Template = module.default;
  const templateProps = module.templateProps;
  if (typeof Template !== "function" || !templateProps) {
    continue;
  }

  const name = file.replace(/\.tsx$/, "");
  const html = toMarkers(await render(React.createElement(Template, templateProps), { pretty: true }));
  writeFileSync(join(outputDir, `${name}.html`), html, "utf8");

  console.log(`Wrote ${name}.html`);
}
