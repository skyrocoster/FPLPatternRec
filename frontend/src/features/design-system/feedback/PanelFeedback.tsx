import type { FeedbackProps } from "./feedbackTypes";
import { FeedbackCore } from "./FeedbackCore";
import styles from "./PanelFeedback.module.css";

export function PanelFeedback({ severity, ...props }: FeedbackProps) {
  return (
    <div className={`${styles.panel} ${styles[severity]}`} data-severity={severity}>
      <FeedbackCore severity={severity} {...props} />
    </div>
  );
}
