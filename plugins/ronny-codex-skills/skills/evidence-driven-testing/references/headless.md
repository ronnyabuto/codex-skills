# Headless browser capture

Prefer the project's existing Playwright/browser environment. If none exists and installing tools is within scope, create an isolated temporary npm project outside the application, install Playwright there and run the capture script from that directory. Follow applicable network approval requirements. Do not claim that `npx --package=playwright node record.mjs` makes Playwright imports resolvable: executable PATH and Node module resolution are different.

Example setup, using a task-specific temporary directory:

```bash
mkdir -p /tmp/task-browser-evidence
cd /tmp/task-browser-evidence
npm init -y
npm install playwright
npx playwright install chromium
```

Create record.mjs in that same directory. Use a task-specific absolute output directory and the actual tested app URL:

```js
import { chromium } from "playwright";
const browser = await chromium.launch();
try {
  const context = await browser.newContext({recordVideo: {dir: outputDir}});
  try {
    const page = await context.newPage();
    await page.goto(appUrl);
    // Drive the requested flow and assert observable outcomes.
    await page.screenshot({path: `${outputDir}/01-result.png`});
  } finally {
    await context.close(); // Flush the recorded video.
  }
} finally {
  await browser.close();
}
```

Define outputDir/appUrl in the actual script and create its output directory. Record assertions with their outcome and conditions beside the captures. Do not label an arbitrary screenshot as passed without a meaningful observation/assertion. Use browser traces or measured timestamps for latency claims; viewing the recording is supporting evidence.

## Probes and agent outcomes

For APIs, SQL or performance, retain a repeatable probe and its measured output.
Compare actual request/SQL traces and returned data on both versions. Record
starting state, workload, revision and environment; confirm the server belongs
to this checkout and keep performance measurements free of competing workloads.

For agent behavior, retain native event excerpts with the relevant command,
result and observed outcome. Compare fresh skill-enabled and skill-disabled
sessions on the same synthetic inputs. Keep invocation/read observations
separate from task success, and report errors as unscored. A positive delta
is not guaranteed; review evidence before attributing an improvement to a skill.
