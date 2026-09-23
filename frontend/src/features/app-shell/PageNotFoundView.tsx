import { PageFeedback } from "../design-system/feedback/PageFeedback";

import styles from "./PageNotFoundView.module.css";

export default function PageNotFoundView() {
  return (
    <div className={styles.pageNotFound}>
      <h1>Page not found</h1>
      <PageFeedback severity="error" message="The page you requested could not be found." />
    </div>
  );
}
