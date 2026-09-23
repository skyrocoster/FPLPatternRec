import provenance from "../../styles/material/material-theme-provenance.json";
import "../../styles/app-tokens.css";

const SYSTEM_ROLES: readonly string[] = [
  "primary",
  "on-primary",
  "primary-container",
  "on-primary-container",
  "secondary",
  "on-secondary",
  "secondary-container",
  "on-secondary-container",
  "tertiary",
  "on-tertiary",
  "tertiary-container",
  "on-tertiary-container",
  "error",
  "on-error",
  "error-container",
  "on-error-container",
  "background",
  "on-background",
  "surface",
  "on-surface",
  "surface-variant",
  "on-surface-variant",
  "surface-dim",
  "surface-bright",
  "surface-container-lowest",
  "surface-container-low",
  "surface-container",
  "surface-container-high",
  "surface-container-highest",
  "outline",
  "outline-variant",
  "shadow",
  "scrim",
  "inverse-surface",
  "inverse-on-surface",
  "inverse-primary",
  "surface-tint",
];

const FEEDBACK_GROUPS: readonly { severity: string; tokens: readonly string[] }[] = [
  {
    severity: "Information",
    tokens: [
      "--app-info-accent",
      "--app-info-on-accent",
      "--app-info-container",
      "--app-info-on-container",
    ],
  },
  {
    severity: "Success",
    tokens: [
      "--app-success-accent",
      "--app-success-on-accent",
      "--app-success-container",
      "--app-success-on-container",
    ],
  },
  {
    severity: "Warning",
    tokens: [
      "--app-warning-accent",
      "--app-warning-on-accent",
      "--app-warning-container",
      "--app-warning-on-container",
    ],
  },
  {
    severity: "Error",
    tokens: [
      "--app-error-accent",
      "--app-error-on-accent",
      "--app-error-container",
      "--app-error-on-container",
    ],
  },
];

function TokenRow({ token }: { token: string }) {
  return (
    <li
      style={{
        display: "flex",
        alignItems: "center",
        gap: "12px",
        padding: "6px 0",
      }}
    >
      <span
        aria-hidden="true"
        style={{
          display: "inline-block",
          width: "44px",
          height: "44px",
          borderRadius: "8px",
          background: `var(${token})`,
          border: "1px solid var(--md-sys-color-outline-variant)",
          flexShrink: 0,
        }}
      />
      <code style={{ fontSize: "13px" }}>{token}</code>
    </li>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section
      style={{
        margin: "0 0 32px",
        padding: "20px 24px",
        background: "var(--md-sys-color-surface-container)",
        borderRadius: "12px",
        border: "1px solid var(--md-sys-color-outline-variant)",
      }}
    >
      <h2 style={{ margin: "0 0 12px", fontSize: "20px" }}>{title}</h2>
      {children}
    </section>
  );
}

export function StorySpecimenTokenOverview() {
  return (
    <main
      className="dark"
      style={{
        minHeight: "100vh",
        background: "var(--md-sys-color-surface)",
        color: "var(--md-sys-color-on-surface)",
        padding: "40px",
        fontFamily: "system-ui",
      }}
    >
      <h1 style={{ margin: "0 0 4px", fontSize: "28px" }}>TokenOverview</h1>
      <p style={{ margin: "0 0 28px", color: "var(--md-sys-color-on-surface-variant)" }}>
        Fixed dark Material token source — provenance, system roles, and application tokens.
      </p>

      <Section title="Fixed dark Material scheme">
        <dl style={{ display: "grid", gridTemplateColumns: "180px 1fr", gap: "8px", margin: 0 }}>
          <dt style={{ color: "var(--md-sys-color-on-surface-variant)" }}>Seed</dt>
          <dd style={{ margin: 0 }}>{provenance.theme.seed}</dd>
          <dt style={{ color: "var(--md-sys-color-on-surface-variant)" }}>Variant</dt>
          <dd style={{ margin: 0 }}>{provenance.theme.variant}</dd>
          <dt style={{ color: "var(--md-sys-color-on-surface-variant)" }}>Contrast</dt>
          <dd style={{ margin: 0 }}>{provenance.theme.contrast}</dd>
          <dt style={{ color: "var(--md-sys-color-on-surface-variant)" }}>Scheme</dt>
          <dd style={{ margin: 0 }}>{provenance.theme.scheme}</dd>
          <dt style={{ color: "var(--md-sys-color-on-surface-variant)" }}>Typeface</dt>
          <dd style={{ margin: 0 }}>{provenance.application.typeface}</dd>
        </dl>
      </Section>

      <Section title="Artifact provenance">
        <dl style={{ display: "grid", gridTemplateColumns: "180px 1fr", gap: "8px", margin: 0 }}>
          <dt style={{ color: "var(--md-sys-color-on-surface-variant)" }}>Generator</dt>
          <dd style={{ margin: 0 }}>
            {provenance.generator.name} {provenance.generator.version}
          </dd>
          <dt style={{ color: "var(--md-sys-color-on-surface-variant)" }}>Schema version</dt>
          <dd style={{ margin: 0 }}>{provenance.schemaVersion}</dd>
          <dt style={{ color: "var(--md-sys-color-on-surface-variant)" }}>Runtime asset</dt>
          <dd style={{ margin: 0 }}>{provenance.artifact.runtimeAsset}</dd>
          <dt style={{ color: "var(--md-sys-color-on-surface-variant)" }}>Runtime member</dt>
          <dd style={{ margin: 0 }}>{provenance.artifact.runtimeMember}</dd>
          <dt style={{ color: "var(--md-sys-color-on-surface-variant)" }}>Runtime SHA-256</dt>
          <dd style={{ margin: 0 }}>
            <code style={{ fontSize: "12px", overflowWrap: "anywhere" }}>
              {provenance.artifact.runtimeMemberSha256}
            </code>
          </dd>
          <dt style={{ color: "var(--md-sys-color-on-surface-variant)" }}>Retained member</dt>
          <dd style={{ margin: 0 }}>{provenance.artifact.runtimeMember}</dd>
          <dt style={{ color: "var(--md-sys-color-on-surface-variant)" }}>Runtime generation</dt>
          <dd style={{ margin: 0 }}>{String(provenance.ownership.runtimeThemeGeneration)}</dd>
        </dl>
        <p style={{ margin: "16px 0 0", color: "var(--md-sys-color-on-surface-variant)" }}>
          The retained CSS is a generated-unmodified input; provenance metadata, application tokens,
          this overview, its story, and its tests are repository-owned.
        </p>
      </Section>

      <Section title="Material system roles (--md-sys-*)">
        <ul style={{ listStyle: "none", margin: 0, padding: 0, columns: "2" }}>
          {SYSTEM_ROLES.map((role) => (
            <TokenRow key={role} token={`--md-sys-color-${role}`} />
          ))}
        </ul>
      </Section>

      <Section title="Application feedback tokens (--app-*)">
        <p style={{ margin: "0 0 16px", color: "var(--md-sys-color-on-surface-variant)" }}>
          Dedicated feedback tokens for information, success, warning, and error — not aliases of
          the Material system roles.
        </p>
        <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
          {FEEDBACK_GROUPS.map((group) => (
            <li key={group.severity} style={{ margin: "0 0 16px" }}>
              <h3 style={{ margin: "0 0 4px", fontSize: "16px" }}>{group.severity}</h3>
              <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
                {group.tokens.map((token) => (
                  <TokenRow key={token} token={token} />
                ))}
              </ul>
            </li>
          ))}
        </ul>
      </Section>
    </main>
  );
}
