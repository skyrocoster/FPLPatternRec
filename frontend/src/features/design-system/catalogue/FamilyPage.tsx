import type { ReactNode } from "react";

import styles from "./catalogue.module.css";

export interface CatalogueLink {
  /** Human-readable story name as it appears in the Storybook sidebar. */
  label: string;
  /** Story id usable as `?path=/story/<storyId>` from the Storybook URL. */
  storyId: string;
  note?: string;
}

export interface CatalogueSection {
  heading: string;
  body?: ReactNode;
  links?: CatalogueLink[];
}

export interface FamilyPageProps {
  family: string;
  intro: ReactNode;
  caution?: ReactNode;
  sections: CatalogueSection[];
}

function storyHref(storyId: string): string {
  return `?path=/story/${storyId}`;
}

/**
 * Shared documentation-page renderer for the catalogue families. Catalogue-only
 * markup; it renders prose and links to existing stories and is not part of
 * the production component set.
 */
export function FamilyPage({ family, intro, caution, sections }: FamilyPageProps) {
  return (
    <main className={styles.page}>
      <h1 className={styles.pageTitle}>{family}</h1>
      <p className={styles.intro}>{intro}</p>
      {caution ? <p className={styles.caution}>{caution}</p> : null}
      {sections.map((section) => (
        <section className={styles.section} key={section.heading}>
          <h2 className={styles.sectionTitle}>{section.heading}</h2>
          {section.body ? <p className={styles.sectionBody}>{section.body}</p> : null}
          {section.links && section.links.length > 0 ? (
            <ul className={styles.linkList}>
              {section.links.map((link) => (
                <li className={styles.linkItem} key={link.storyId}>
                  <a className={styles.linkLabel} href={storyHref(link.storyId)}>
                    {link.label}
                  </a>
                  {link.note ? <span className={styles.linkNote}>{link.note}</span> : null}
                </li>
              ))}
            </ul>
          ) : null}
        </section>
      ))}
    </main>
  );
}

interface DemoRowProps {
  caption: string;
  children: ReactNode;
  className?: string;
}

/** Small catalogued row: a plain-English caption above a produced example. */
export function DemoRow({ caption, children, className }: DemoRowProps) {
  return (
    <div className={[styles.demoRow, className].filter(Boolean).join(" ")}>
      <p className={styles.demoCaption}>{caption}</p>
      {children}
    </div>
  );
}
