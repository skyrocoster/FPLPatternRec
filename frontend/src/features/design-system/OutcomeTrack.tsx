import styles from "./OutcomeTrack.module.css";

export type OutcomeTrackValues = {
  wins: number;
  draws: number;
  losses: number;
  /** Optional unclassified games kept in the total so the track stays truthful. */
  unknown?: number;
};

export type OutcomeTrackProps = {
  values: OutcomeTrackValues;
  accessibleLabel: string;
  compact?: boolean;
  className?: string;
};

function share(value: number, total: number): number {
  return total > 0 ? (Math.max(0, value) / total) * 100 : 0;
}

/** Shared win/draw/loss track for engine and played-game results. */
export function OutcomeTrack({
  values,
  accessibleLabel,
  compact = false,
  className,
}: OutcomeTrackProps) {
  const unknown = Math.max(0, values.unknown ?? 0);
  const total =
    Math.max(0, values.wins) + Math.max(0, values.draws) + Math.max(0, values.losses) + unknown;

  return (
    <div
      className={[styles.track, compact ? styles.compact : null, className]
        .filter(Boolean)
        .join(" ")}
      role="img"
      aria-label={accessibleLabel}
    >
      <span
        className={styles.win}
        style={{ inlineSize: `${share(values.wins, total)}%` }}
        aria-hidden="true"
      />
      <span
        className={styles.draw}
        style={{ inlineSize: `${share(values.draws, total)}%` }}
        aria-hidden="true"
      />
      <span
        className={styles.loss}
        style={{ inlineSize: `${share(values.losses, total)}%` }}
        aria-hidden="true"
      />
      {unknown > 0 ? (
        <span
          className={styles.unknown}
          style={{ inlineSize: `${share(unknown, total)}%` }}
          aria-hidden="true"
        />
      ) : null}
    </div>
  );
}
