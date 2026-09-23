import { InlineFeedback } from "./feedback/InlineFeedback";
import { PageFeedback } from "./feedback/PageFeedback";
import { PanelFeedback } from "./feedback/PanelFeedback";
import styles from "./StorySpecimenAccessibilityReview.module.css";

/**
 * Acceptance/ResponsiveAccessibilityReview owner: one Storybook-only review
 * fixture that places every presentation level (inline, panel, page) inside
 * a single constrained review container. It demonstrates long-message
 * wrapping, no-heading content, explicit consumer-owned live semantics, and
 * StorySpecimenFoundation-style focus specimens.
 *
 * Live-region attributes are ordinary FeedbackProps passed through the
 * shipped wrappers and forwarded as-is by FeedbackCore: no wrapper or core
 * supplies a default role or aria-live. No state, no new feedback API, no
 * duplicate token definitions, and no production import.
 */
export function StorySpecimenAccessibilityReview() {
  return (
    <main className={styles.review} data-testid="accessibility-review">
      <h1 className={styles.title}>Responsive and accessibility review</h1>
      <p className={styles.intro}>
        All presentation levels inside one constrained review container: long-message wrapping,
        no-heading content, explicit consumer-owned live semantics, and focus specimens.
      </p>

      <section className={styles.presentationSection} aria-label="Inline feedback review">
        <InlineFeedback
          severity="information"
          message="A compact border-first inline presentation with no heading. This consumer-owned instance supplies role=status, aria-live=polite, and aria-atomic=true; the wrapper and core add no default live semantics of their own."
          role="status"
          aria-live="polite"
          aria-atomic="true"
        />
      </section>

      <section className={styles.presentationSection} aria-label="Panel feedback review">
        <PanelFeedback
          severity="warning"
          message="This panel presentation carries a deliberately long message so the constrained review container can prove wrapping behavior at both review sizes. The sentence keeps flowing across several lines without any manual line break while the tonal container, the 1px fine border, and the severity accent stay intact at 1920x1080 and at 412x915 portrait. No wrapper default role or aria-live is applied, so this instance simply renders its message content."
        />
      </section>

      <section className={styles.presentationSection} aria-label="Page feedback review">
        <PageFeedback
          severity="error"
          message="Page feedback spans the readable width on the accepted tonal surface. This consumer-owned instance supplies role=alert and aria-live=assertive, while the page presentation itself assigns no announcement role by default."
          role="alert"
          aria-live="assertive"
          aria-relevant="additions text"
        />
      </section>

      <section className={styles.presentationSection} aria-label="Focus specimens review">
        <p className={styles.focusIntro}>
          Focusable specimens prove the centralized 2px primary focus ring with 2px separation.
        </p>
        <div className={styles.focusRow}>
          <button type="button" className={styles.focusSpecimen}>
            Focus specimen one
          </button>
          <button type="button" className={styles.focusSpecimen}>
            Focus specimen two
          </button>
        </div>
      </section>
    </main>
  );
}
