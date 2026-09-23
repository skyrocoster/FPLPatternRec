/**
 * Mechanical backstop for the workflow-wide bash-timeout rule: every workflow agent that
 * can run shell commands must invoke the `bash` tool with an explicit finite timeout in
 * milliseconds, because commands sometimes hang. This hook guarantees finiteness by
 * injecting the default when the timeout is missing, zero, or non-finite; any valid
 * finite timeout is preserved untouched, along with all other arguments.
 *
 * Tracked deliberately: `.opencode/plugin/` is un-ignored in the root .gitignore, and an
 * untracked rule is one that silently stops applying on the next clone.
 */

const DEFAULT_TIMEOUT_MS = 120_000

export const BashTimeout = async () => ({
  "tool.execute.before": async (input, output) => {
    if (input.tool !== "bash") return
    const timeout = output.args?.timeout
    if (typeof timeout !== "number" || !Number.isFinite(timeout) || timeout <= 0) {
      output.args = { ...(output.args ?? {}), timeout: DEFAULT_TIMEOUT_MS }
    }
  },
})

export default BashTimeout