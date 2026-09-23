import { tool } from "@opencode-ai/plugin"

const WARNING_TOKENS = 100_000
const DECISION_TOKENS = 120_000
const ROLLOVER_TOKENS = 200_000

// Resume only while the provider-side prompt cache is conservatively expected to be warm.
// GPT-5.6 documents a 30-minute minimum lifetime. Z.AI does not publish a GLM cache TTL.
const CACHE_RESUME_WINDOWS_MS = {
  "coordinator-caseworker": 20 * 60_000,
  "coordinator-caseworker-flash": 4 * 60_000,
  "coordinator-caseworker-sol": 25 * 60_000,
}

export const ContextBudget = async ({ client, directory }) => ({
  tool: {
    context_budget: tool({
      description:
        "Measure a retained subagent session's active context and estimated cache freshness before deciding whether to resume it.",
      args: {
        session_id: tool.schema.string().describe("The retained OpenCode subagent session ID"),
      },
      async execute({ session_id }) {
        const response = await client.session.messages({
          path: { id: session_id },
          query: { directory },
        })
        const messages = response.data ?? []
        const assistants = messages
          .map((message) => message.info)
          .filter((info) => info.role === "assistant" && info.time.completed != null)
        const latest = assistants.at(-1)

        if (!latest) {
          return JSON.stringify({
            status: "UNAVAILABLE",
            session_id,
            reason: "No completed assistant message with token telemetry was found.",
          })
        }

        const active_tokens = latest.tokens.input + latest.tokens.cache.read
        let token_status = "OK"
        let default_action = "RESUME"
        if (active_tokens >= ROLLOVER_TOKENS) {
          token_status = "ROLLOVER-DEFAULT"
          default_action = "ROLLOVER"
        } else if (active_tokens >= DECISION_TOKENS) {
          token_status = "DECISION-REQUIRED"
          default_action = "DECIDE"
        } else if (active_tokens >= WARNING_TOKENS) {
          token_status = "WARNING"
        }

        const latestUser = messages
          .map((message) => message.info)
          .filter((info) => info.role === "user")
          .at(-1)
        const agent = latestUser?.agent
        const cache_resume_window_ms = CACHE_RESUME_WINDOWS_MS[agent] ?? null
        const last_activity_at = latest.time.completed
        const idle_ms = Math.max(0, Date.now() - last_activity_at)
        const cache_status =
          cache_resume_window_ms == null
            ? "UNTRACKED"
            : idle_ms >= cache_resume_window_ms
              ? "COLD"
              : "WARM"
        const status = cache_status === "COLD" ? "ROLLOVER-DEFAULT" : token_status
        if (cache_status === "COLD") default_action = "ROLLOVER"

        return JSON.stringify({
          status,
          token_status,
          session_id,
          agent,
          active_tokens,
          measurement: "latest completed assistant input + cache.read",
          warning_tokens: WARNING_TOKENS,
          decision_tokens: DECISION_TOKENS,
          rollover_tokens: ROLLOVER_TOKENS,
          cache_status,
          cache_resume_window_ms,
          idle_ms,
          last_activity_at,
          default_action,
          compacted: messages.some((message) =>
            message.parts.some((part) => part.type === "compaction"),
          ),
        })
      },
    }),
  },
})

export default ContextBudget
