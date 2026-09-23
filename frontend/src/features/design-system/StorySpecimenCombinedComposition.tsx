import { PanelFeedback } from "./feedback/PanelFeedback";
import styles from "./StorySpecimenCombinedComposition.module.css";

/**
 * Composition/ReviewSummary owner: one restrained design-system
 * surface composing the accepted typescale, geometry, tonal surfaces, fine
 * borders, one reserved elevation level, and exactly one shipped
 * FeedbackCore-backed feedback presentation through the PanelFeedback
 * wrapper. Storybook-only: no state, no routing, no actions, no fake
 * analytical content, and no duplicate token definitions - every value
 * comes from the centralized --md-sys-typescale-* and --app-* / --md-sys-*
 * tokens.
 */
export function StorySpecimenCombinedComposition() {
  return (
    <main className={styles.composition}>
      <header className={styles.headingRegion}>
        <p className={styles.eyebrow}>Design system composition</p>
        <h1 className={styles.display}>ReviewSummary</h1>
        <h2 className={styles.headline}>One restrained review surface</h2>
        <p className={styles.title}>
          The accepted typescale, geometry, tonal surfaces, fine borders, one reserved elevation
          level, and one feedback presentation compose a single coherent surface.
        </p>
      </header>

      <section className={styles.surfaceRegion} aria-label="Tonal surface region">
        <h3 className={styles.sectionTitle}>Tonal surface with fine border</h3>
        <p className={styles.sectionBody}>
          Normal structure stays border-first: the tonal surface and its 1px fine border carry the
          region, and the reserved elevation is limited to the floating emphasis card.
        </p>
        <div className={styles.elevatedCard} tabIndex={0}>
          <h4 className={styles.cardTitle}>Reserved elevation</h4>
          <p className={styles.cardBody}>
            One reserved elevation level demonstrates the restrained depth scale for major and
            floating emphasis.
          </p>
        </div>
      </section>

      <section className={styles.feedbackRegion} aria-label="Feedback presentation">
        <PanelFeedback
          severity="information"
          heading="Composition note"
          message="The combined composition reuses the shipped feedback presentation unchanged."
        />
      </section>
    </main>
  );
}
