import type { ComponentPropsWithoutRef } from "react";
import { CircleCheck, CircleX, Info, TriangleAlert } from "lucide-react";
import type { LucideIcon } from "lucide-react";

export type FeedbackSeverity = "information" | "success" | "warning" | "error";

/**
 * The narrow consumer-live-attribute contract. role is not part of React
 * AriaAttributes (which owns only aria-* keys); it derives from the div
 * element props so consumers may supply exactly these five attributes,
 * all optional and forwarded as-is with NO default values.
 */
export type FeedbackLiveRegionAttributes = Pick<
  ComponentPropsWithoutRef<"div">,
  "role" | "aria-live" | "aria-atomic" | "aria-relevant" | "aria-busy"
>;

/**
 * FeedbackProps admits exactly: required severity, required message,
 * optional heading, and the five consumer-supplied live-region attributes.
 * It does NOT admit children, actions, a custom icon, arbitrary div props,
 * or automatic announcement behavior.
 */
export interface FeedbackProps extends FeedbackLiveRegionAttributes {
  severity: FeedbackSeverity;
  message: string;
  heading?: string;
}

export interface FeedbackVariantTokens {
  accent: string;
  onAccent: string;
  container: string;
  onContainer: string;
}

export interface FeedbackVariant {
  icon: LucideIcon;
  tokens: FeedbackVariantTokens;
}

/**
 * Each severity maps to exactly one fixed installed Lucide icon and the
 * four dedicated repository-owned feedback token names. These tokens are
 * fixed hex values intentionally NOT aliased to --md-sys-color roles.
 */
export const FEEDBACK_VARIANTS: Record<FeedbackSeverity, FeedbackVariant> = {
  information: {
    icon: Info,
    tokens: {
      accent: "--app-info-accent",
      onAccent: "--app-info-on-accent",
      container: "--app-info-container",
      onContainer: "--app-info-on-container",
    },
  },
  success: {
    icon: CircleCheck,
    tokens: {
      accent: "--app-success-accent",
      onAccent: "--app-success-on-accent",
      container: "--app-success-container",
      onContainer: "--app-success-on-container",
    },
  },
  warning: {
    icon: TriangleAlert,
    tokens: {
      accent: "--app-warning-accent",
      onAccent: "--app-warning-on-accent",
      container: "--app-warning-container",
      onContainer: "--app-warning-on-container",
    },
  },
  error: {
    icon: CircleX,
    tokens: {
      accent: "--app-error-accent",
      onAccent: "--app-error-on-accent",
      container: "--app-error-container",
      onContainer: "--app-error-on-container",
    },
  },
};
