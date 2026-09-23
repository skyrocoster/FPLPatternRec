import { Avatar as BaseAvatar } from "@base-ui/react/avatar";
import type { ComponentPropsWithoutRef, ReactNode } from "react";

import styles from "./ContentPrimitives.module.css";

export type AvatarSize = "sm" | "md";

export interface AvatarProps extends Omit<ComponentPropsWithoutRef<"span">, "children"> {
  src?: string;
  alt: string;
  fallback: ReactNode;
  size?: AvatarSize;
  imageProps?: Omit<ComponentPropsWithoutRef<"img">, "src" | "alt">;
  fallbackDelay?: number;
}

/** Image avatar with a reliable accessible fallback. */
export function Avatar({
  src,
  alt,
  fallback,
  size = "md",
  imageProps,
  fallbackDelay,
  className,
  ...rest
}: AvatarProps) {
  const imageClassName = [styles.avatarImage, imageProps?.className].filter(Boolean).join(" ");

  return (
    <BaseAvatar.Root
      {...rest}
      className={[styles.avatar, className].filter(Boolean).join(" ")}
      data-size={size}
    >
      {src ? (
        <BaseAvatar.Image {...imageProps} src={src} alt={alt} className={imageClassName} />
      ) : null}
      <BaseAvatar.Fallback className={styles.avatarFallback} delay={fallbackDelay}>
        {fallback}
      </BaseAvatar.Fallback>
    </BaseAvatar.Root>
  );
}
