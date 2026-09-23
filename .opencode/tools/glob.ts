/**
 * Override of the built-in `glob` tool.
 *
 * The built-in tool shells to `ripgrep --files`, which respects `.gitignore` by default and
 * never passes `--hidden`, so it can neither list gitignored files nor dot-files such as
 * `.env`, `node_modules/`, or `.opencode/`. This override runs the same ripgrep invocation
 * with `--no-ignore --hidden`, so glob searches everything on disk in the target directory.
 *
 * Deliberately a custom tool rather than a config knob: the `.ignore` file ripgrep's docs
 * suggest can re-include only non-hidden paths, and the built-in glob tool exposes no option
 * to pass those flags. Custom tools take precedence over built-ins with the same name.
 *
 * Tracked deliberately: `.opencode/` is otherwise gitignored, and an untracked rule is one
 * that silently stops applying on the next clone.
 */

import { spawnSync } from "node:child_process"
import os from "node:os"
import path from "node:path"
import { tool } from "@opencode-ai/plugin"

const LIMIT = 100

function resolveRg(): string {
  const name = process.platform === "win32" ? "rg.exe" : "rg"
  const candidates = [
    name,
    path.join(os.homedir(), ".cache", "opencode", "bin", name),
    path.join(os.homedir(), ".local", "share", "opencode", "bin", name),
    process.env.LOCALAPPDATA ? path.join(process.env.LOCALAPPDATA, "opencode", "bin", name) : "",
  ].filter(Boolean)
  for (const candidate of candidates) {
    try {
      const probe = spawnSync(candidate, ["--version"], { stdio: "ignore" })
      if (probe.error == null && probe.status === 0) return candidate
    } catch {
      // keep looking
    }
  }
  return name
}

function globFiles(cwd: string, pattern: string): string[] {
  const rg = resolveRg()
  const result = spawnSync(
    rg,
    [
      "--no-config",
      "--files",
      "--no-ignore",
      "--hidden",
      `--glob=${pattern}`,
      "--glob=!**/.git/**",
      ".",
    ],
    { cwd, encoding: "utf8", maxBuffer: 64 * 1024 * 1024 },
  )
  if (result.error) return []
  const code = result.status ?? -1
  if (code === 0 || code === 1) {
    return (result.stdout ?? "").split(/\r?\n/).filter(Boolean)
  }
  return []
}

export default tool({
  description:
    "Find files by pattern matching. Searches ALL files in the directory, including files and directories ignored by .gitignore and hidden (dot) files such as .env, node_modules/, and .opencode/.",
  args: {
    pattern: tool.schema.string().describe("The glob pattern to match files against"),
    path: tool.schema
      .string()
      .optional()
      .describe(
        `The directory to search in. If not specified, the current working directory will be used. IMPORTANT: Omit this field to use the default directory. DO NOT enter "undefined" or "null" - simply omit it for the default behavior. Must be a valid directory path if provided.`,
      ),
  },
  async execute(args, context) {
    const search = args.path ? path.resolve(context.directory, args.path) : context.directory

    await context.ask({
      permission: "glob",
      patterns: [args.pattern],
      always: ["*"],
      metadata: { pattern: args.pattern, path: args.path },
    })

    const files = globFiles(search, args.pattern)
    const truncated = files.length > LIMIT
    const shown = truncated ? files.slice(0, LIMIT) : files

    const output: string[] = []
    if (shown.length === 0) output.push("No files found")
    else {
      output.push(...shown.map((file) => path.resolve(search, file)))
      if (truncated) {
        output.push("")
        output.push(
          `(Results are truncated: showing first ${LIMIT} results. Consider using a more specific path or pattern.)`,
        )
      }
    }

    return {
      title: path.relative(context.worktree, search) || ".",
      metadata: { count: files.length, truncated },
      output: output.join("\n"),
    }
  },
})
