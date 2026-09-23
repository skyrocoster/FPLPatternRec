import styles from "./StorySpecimenFoundation.module.css";

const SPACING_STEPS = [4, 8, 12, 16, 24, 32, 48] as const;

const SPACING_CLASSES: Record<number, string> = {
  4: styles.spacing4,
  8: styles.spacing8,
  12: styles.spacing12,
  16: styles.spacing16,
  24: styles.spacing24,
  32: styles.spacing32,
  48: styles.spacing48,
};

const RADII = [
  { token: "--app-radius-4", className: styles.radius4 },
  { token: "--app-radius-8", className: styles.radius8 },
  { token: "--app-radius-12", className: styles.radius12 },
  { token: "--app-radius-default", className: styles.radiusDefault },
] as const;

const SURFACES = [
  {
    token: "--md-sys-color-surface-container-low",
    className: styles.surfaceSample,
  },
  {
    token: "--md-sys-color-surface-container",
    className: `${styles.surfaceSample} ${styles.surfaceContainer}`,
  },
  {
    token: "--md-sys-color-surface-container-high",
    className: `${styles.surfaceSample} ${styles.surfaceContainerHigh}`,
  },
] as const;

const ELEVATIONS = [
  { token: "--app-elevation-e0", className: styles.elevationE0 },
  { token: "--app-elevation-e1", className: styles.elevationE1 },
  { token: "--app-elevation-e2", className: styles.elevationE2 },
  { token: "--app-elevation-e3", className: styles.elevationE3 },
] as const;

export function StorySpecimenFoundation() {
  return (
    <main className={styles.specimen}>
      <h1 className={styles.pageTitle}>Foundations</h1>
      <p className={styles.intro}>
        Balanced density, exact spacing, restrained radii, tonal surfaces and fine borders first,
        reserved elevation, and the focus ring — driven by the centralized --app-* foundation tokens
        and the existing --md-sys color roles.
      </p>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Spacing scale</h2>
        <ul className={styles.specimenList}>
          {SPACING_STEPS.map((step) => (
            <li key={step} className={styles.specimenRow}>
              <span
                aria-hidden="true"
                className={`${styles.spacingBar} ${SPACING_CLASSES[step]}`}
              />
              <code className={styles.specimenLabel}>--app-spacing-{step}</code>
            </li>
          ))}
        </ul>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Radius</h2>
        <ul className={styles.specimenList}>
          {RADII.map((radius) => (
            <li key={radius.token} className={styles.specimenRow}>
              <span aria-hidden="true" className={`${styles.radiusSample} ${radius.className}`} />
              <code className={styles.specimenLabel}>{radius.token}</code>
            </li>
          ))}
        </ul>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Tonal surfaces and fine borders</h2>
        <ul className={styles.specimenList}>
          {SURFACES.map((surface) => (
            <li key={surface.token} className={styles.specimenRow}>
              <span aria-hidden="true" className={surface.className} />
              <code className={styles.specimenLabel}>{surface.token}</code>
            </li>
          ))}
        </ul>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Elevation (reserved)</h2>
        <ul className={styles.specimenList}>
          {ELEVATIONS.map((elevation) => (
            <li key={elevation.token} className={styles.specimenRow}>
              <span
                aria-hidden="true"
                className={`${styles.elevationSample} ${elevation.className}`}
              />
              <code className={styles.specimenLabel}>{elevation.token}</code>
            </li>
          ))}
        </ul>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Focus ring</h2>
        <button type="button" className={styles.focusSpecimen}>
          Focus specimen
        </button>
      </section>
    </main>
  );
}
