import type { CSSProperties } from "react";
import { FEEDBACK_VARIANTS } from "./feedbackTypes";
import type { FeedbackProps } from "./feedbackTypes";
import styles from "./FeedbackCore.module.css";

/**
 * Shared semantic feedback core: consumer props -> static FEEDBACK_VARIANTS
 * map -> decorative fixed icon plus optional heading and required message.
 * The five picked consumer live-region attributes forward to the root
 * element as-is with NO default role/aria-live. No internal state, effects,
 * actions, child composition, loading severity, or custom icon API.
 */
export function FeedbackCore({
  severity,
  message,
  heading,
  role,
  "aria-live": ariaLive,
  "aria-atomic": ariaAtomic,
  "aria-relevant": ariaRelevant,
  "aria-busy": ariaBusy,
}: FeedbackProps) {
  const variant = FEEDBACK_VARIANTS[severity];
  const Icon = variant.icon;

  return (
    <div
      role={role}
      aria-live={ariaLive}
      aria-atomic={ariaAtomic}
      aria-relevant={ariaRelevant}
      aria-busy={ariaBusy}
      className={styles.core}
      data-testid={`core-${severity}`}
      style={
        {
          "--app-feedback-accent": `var(${variant.tokens.accent})`,
          "--app-feedback-on-accent": `var(${variant.tokens.onAccent})`,
          "--app-feedback-container": `var(${variant.tokens.container})`,
          "--app-feedback-on-container": `var(${variant.tokens.onContainer})`,
        } as CSSProperties
      }
    >
      <Icon aria-hidden="true" className={styles.icon} data-testid={`icon-${severity}`} />
      <div className={styles.content}>
        {heading ? <h3 className={styles.heading}>{heading}</h3> : null}
        <p className={styles.message}>{message}</p>
      </div>
    </div>
  );
}
