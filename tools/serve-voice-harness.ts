import { resolve, sep } from "node:path";

const root = resolve(import.meta.dir, "..");
const frontend = resolve(root, "custom_components/llm_gateway/frontend");
const server = Bun.serve({
  hostname: "127.0.0.1",
  port: Number(process.env.PORT || 4174),
  async fetch(request) {
    const path = new URL(request.url).pathname;
    if (path === "/" || path === "/tools/voice-harness-ui-fixture.html")
      return new Response(
        Bun.file(resolve(root, "tools/voice-harness-ui-fixture.html")),
      );
    const candidate = resolve(root, "." + decodeURIComponent(path));
    if (!candidate.startsWith(frontend + sep))
      return new Response("Not found", { status: 404 });
    const file = Bun.file(candidate);
    return (await file.exists())
      ? new Response(file)
      : new Response("Not found", { status: 404 });
  },
});
console.log(`Voice Harness fixture: ${server.url}`);
