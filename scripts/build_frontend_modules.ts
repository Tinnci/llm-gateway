import { basename, join } from "node:path";

const frontendDir = join(
  import.meta.dir,
  "..",
  "custom_components",
  "llm_gateway",
  "frontend",
);
const outputDir = "/tmp/llm-gateway-frontend-modules";
const entrypoints = [
  "voice-harness-api.ts",
  "voice-harness-components.ts",
  "voice-harness-model.ts",
  "voice-harness-scenario.ts",
  "voice-harness-ui.ts",
  "voice-harness-utils.ts",
].map((file) => join(frontendDir, file));

const result = await Bun.build({
  entrypoints,
  format: "esm",
  outdir: outputDir,
  target: "browser",
});

if (!result.success) {
  for (const log of result.logs) {
    console.error(log);
  }
  process.exit(1);
}

for (const output of result.outputs) {
  await Bun.write(join(frontendDir, basename(output.path)), output);
}

console.log(`Built ${result.outputs.length} frontend modules.`);
