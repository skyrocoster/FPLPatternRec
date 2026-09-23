import type { FeedbackProps } from "./feedbackTypes";
import { FeedbackCore } from "./FeedbackCore";
import styles from "./PageFeedback.module.css";

/**
 * Thin page presentation wrapper over the shared FeedbackCore.
 * Consumer FeedbackProps flow through unchanged: FeedbackCore still renders
 * the decorative fixed icon, optional heading, and required message, and
 * still forwards the five consumer live-region attributes as-is with NO
 * defaults. The wrapper adds only the page-level surface treatment with the
 * severity accent as a visual cue; it assigns no role/aria-live, adds no
 * actions, children, or custom icon API, and is not a notification system.
 */
export function PageFeedback({ severity, ...props }: FeedbackProps) {
  return (
    <div className={`${styles.page} ${styles[severity]}`} data-severity={severity}>
      <FeedbackCore severity={severity} {...props} />
    </div>
  );
}
