import type { ReactNode } from "react";

export function catalogueDemoShell(children: ReactNode) {
  return (
    <main
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "var(--app-spacing-24)",
        padding: "var(--app-spacing-32)",
        minHeight: "100vh",
        backgroundColor: "var(--md-sys-color-surface)",
        color: "var(--md-sys-color-on-surface)",
      }}
    >
      {children}
    </main>
  );
}
