import { execFileSync } from "node:child_process";
import { mkdirSync, writeFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import openapiTS, { astToString } from "openapi-typescript";
import { format } from "prettier";

const root = fileURLToPath(new URL("../../", import.meta.url));
const local = path.join(
  root,
  ".venv",
  process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
);
const backendLocal = path.join(
  root,
  "backend/.venv",
  process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
);
const python =
  process.env.PYTHON ||
  (existsSync(local)
    ? local
    : existsSync(backendLocal)
      ? backendLocal
      : "python");
const schema = execFileSync(
  python,
  [
    "-c",
    "import json; from app.main import create_app; from app.core.config import Settings; print(json.dumps(create_app(Settings(_env_file=None)).openapi()))",
  ],
  {
    cwd: path.join(root, "backend"),
    encoding: "utf8",
    maxBuffer: 4 * 1024 * 1024,
  },
);
const output = path.join(root, "frontend/src/api");
mkdirSync(output, { recursive: true });
writeFileSync(
  path.join(output, "schema.ts"),
  await format(astToString(await openapiTS(JSON.parse(schema))), {
    parser: "typescript",
  }),
);
console.log(
  "Generated API types from the existing FastAPI OpenAPI contract (no DB connection).",
);
