import { FeedbackCore } from "./FeedbackCore";
import type { FeedbackProps } from "./feedbackTypes";
import styles from "./InlineFeedback.module.css";

/**
 * Thin inline presentation wrapper over the shared FeedbackCore.
 * Consumer FeedbackProps flow through unchanged: FeedbackCore still renders
 * the decorative fixed icon, optional heading, and required message, and
 * still forwards the five consumer live-region attributes as-is with NO
 * defaults. The wrapper adds only the compact, transparent/border-first
 * inline treatment; it adds no role/aria-live, actions, children, or custom
 * icon API.
 */
export function InlineFeedback(props: FeedbackProps) {
  return (
    <div className={styles.inline}>
      <FeedbackCore {...props} />
    </div>
  );
}
