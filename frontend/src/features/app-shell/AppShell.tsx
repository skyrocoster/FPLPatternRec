import { Drawer, type DrawerRoot } from "@base-ui/react/drawer";
import { Activity, Crown, Menu, X } from "lucide-react";
import { NavLink } from "react-router-dom";
import { useRef } from "react";

import { PageContentBoundary } from "./PageContentBoundary";
import styles from "./AppShell.module.css";

interface AppShellProps {
  children: React.ReactNode;
}

function NavigationItems({ onSelect }: { onSelect?: () => void }) {
  return (
    <>
      <NavLink className={styles.navigationLink} to="/" end onClick={onSelect}>
        <Activity aria-hidden="true" size={20} />
        <span>Status</span>
      </NavLink>
    </>
  );
}

export function AppShell({ children }: AppShellProps) {
  const drawerActionsRef = useRef<DrawerRoot.Actions | null>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  return (
    <Drawer.Root actionsRef={drawerActionsRef}>
      <div className={styles.shell}>
        <a className={styles.skipLink} href="#main-content">
          Skip to main content
        </a>

        <header className={styles.header}>
          <Drawer.Trigger
            ref={triggerRef}
            className={styles.menuTrigger}
            aria-label="Open navigation menu"
          >
            <Menu aria-hidden="true" size={24} />
          </Drawer.Trigger>
          <div className={styles.identity} data-testid="shell-identity-header">
            FPLPatternRec
          </div>
        </header>

        <aside className={styles.rail} aria-label="Primary navigation">
          <div className={styles.railIdentity} data-testid="shell-identity-rail">
            <span className={styles.identityMark} aria-hidden="true">
              <Crown size={20} />
            </span>
            <span className={styles.identityWordmark}>FPLPatternRec</span>
          </div>
          <nav className={styles.railNav} aria-label="Desktop navigation">
            <NavigationItems />
          </nav>
        </aside>

        <Drawer.Portal>
          <Drawer.Backdrop className={styles.drawerBackdrop} data-testid="drawer-backdrop" />
          <Drawer.Viewport className={styles.drawerViewport}>
            <Drawer.Popup
              className={styles.drawerPopup}
              initialFocus={closeButtonRef}
              finalFocus={triggerRef}
            >
              <Drawer.Content className={styles.drawerContent}>
                <div className={styles.drawerHeader}>
                  <Drawer.Title className={styles.drawerTitle}>Navigation</Drawer.Title>
                  <Drawer.Close
                    ref={closeButtonRef}
                    className={styles.closeTrigger}
                    aria-label="Close navigation menu"
                  >
                    <X aria-hidden="true" size={24} />
                  </Drawer.Close>
                </div>
                <nav aria-label="Drawer navigation">
                  <NavigationItems onSelect={() => drawerActionsRef.current?.close()} />
                </nav>
              </Drawer.Content>
            </Drawer.Popup>
          </Drawer.Viewport>
        </Drawer.Portal>

        <main className={styles.main} id="main-content">
          <PageContentBoundary>{children}</PageContentBoundary>
        </main>
      </div>
    </Drawer.Root>
  );
}
