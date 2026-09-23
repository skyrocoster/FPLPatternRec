import styles from "./StorySpecimenTypescale.module.css";

interface TypescaleRole {
  name: string;
  className: string;
}

const TYPESCALE_ROLES: readonly TypescaleRole[] = [
  { name: "display-large", className: styles.displayLarge },
  { name: "display-medium", className: styles.displayMedium },
  { name: "display-small", className: styles.displaySmall },
  { name: "headline-large", className: styles.headlineLarge },
  { name: "headline-medium", className: styles.headlineMedium },
  { name: "headline-small", className: styles.headlineSmall },
  { name: "title-large", className: styles.titleLarge },
  { name: "title-medium", className: styles.titleMedium },
  { name: "title-small", className: styles.titleSmall },
  { name: "body-large", className: styles.bodyLarge },
  { name: "body-medium", className: styles.bodyMedium },
  { name: "body-small", className: styles.bodySmall },
  { name: "label-large", className: styles.labelLarge },
  { name: "label-medium", className: styles.labelMedium },
  { name: "label-small", className: styles.labelSmall },
];

export function StorySpecimenTypescale() {
  return (
    <main className={styles.specimen}>
      <h1 className={`${styles.pageTitle} ${styles.titleLarge}`}>CompleteTypescale</h1>
      <p className={`${styles.intro} ${styles.bodyMedium}`}>
        All 15 Material 3 system-ui typescale roles driven by the centralized --md-sys-typescale-*
        variables.
      </p>
      <ul className={styles.roleList}>
        {TYPESCALE_ROLES.map((role) => (
          <li key={role.name} className={styles.roleRow}>
            <span className={role.className}>Typescale sample</span>
            <code className={styles.roleName}>{role.name}</code>
          </li>
        ))}
      </ul>
    </main>
  );
}
