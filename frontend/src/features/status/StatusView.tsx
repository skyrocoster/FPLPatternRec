import { InlineFeedback } from "../design-system/feedback/InlineFeedback";
import styles from "./StatusView.module.css";

export type StatusViewState = { kind: "loading" } | { kind: "success" } | { kind: "error" };

interface StatusViewProps {
  state: StatusViewState;
}

export function StatusView({ state }: StatusViewProps) {
  const feedback =
    state.kind === "loading"
      ? {
          severity: "information" as const,
          message: "Checking backend health…",
          role: "status" as const,
        }
      : state.kind === "success"
        ? {
            severity: "success" as const,
            message: "Backend connected and healthy.",
            role: "status" as const,
          }
        : {
            severity: "error" as const,
            message: "Backend unavailable.",
            role: "alert" as const,
          };

  return (
    <section className={styles.status} data-state={state.kind} aria-labelledby="status-heading">
      <h1 className={styles.heading} id="status-heading">
        System status
      </h1>
      <InlineFeedback {...feedback} />
    </section>
  );
}
