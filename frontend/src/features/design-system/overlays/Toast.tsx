import { Toast as BaseToast } from "@base-ui/react/toast";
import type {
  ToastManager,
  ToastManagerAddOptions,
  ToastProviderProps as BaseToastProviderProps,
  UseToastManagerReturnValue,
} from "@base-ui/react/toast";
import type { ReactNode } from "react";

import styles from "./OverlayPrimitives.module.css";

export interface ToastProviderProps extends Omit<BaseToastProviderProps, "children"> {
  children: ReactNode;
  dismissLabel?: ReactNode;
}

export type ToastOptions<Data extends object = Record<string, unknown>> =
  ToastManagerAddOptions<Data>;

function ToastRegion({ dismissLabel }: { dismissLabel: ReactNode }) {
  const { toasts } = BaseToast.useToastManager();

  return (
    <BaseToast.Portal>
      <BaseToast.Viewport className={styles.toastViewport}>
        {toasts.map((toast) => (
          <BaseToast.Root className={styles.toast} key={toast.id} toast={toast}>
            <BaseToast.Content className={styles.toastContent}>
              <div className={styles.toastText}>
                <BaseToast.Title className={styles.toastTitle} />
                <BaseToast.Description className={styles.toastDescription} />
              </div>
              <div className={styles.toastActions}>
                {toast.actionProps ? (
                  <BaseToast.Action {...toast.actionProps} className={styles.toastAction} />
                ) : null}
                <BaseToast.Close className={styles.toastClose}>{dismissLabel}</BaseToast.Close>
              </div>
            </BaseToast.Content>
          </BaseToast.Root>
        ))}
      </BaseToast.Viewport>
    </BaseToast.Portal>
  );
}

/** Application toast provider with a ready-to-use stacked notification region. */
export function ToastProvider({
  children,
  dismissLabel = "Dismiss",
  ...providerProps
}: ToastProviderProps) {
  return (
    <BaseToast.Provider {...providerProps}>
      {children}
      <ToastRegion dismissLabel={dismissLabel} />
    </BaseToast.Provider>
  );
}

/** Access the nearest ToastProvider's queue and update methods. */
// Kept with ToastProvider so consumers have one public toast module.
// eslint-disable-next-line react-refresh/only-export-components
export function useToast<
  Data extends object = Record<string, unknown>,
>(): UseToastManagerReturnValue<Data> {
  return BaseToast.useToastManager<Data>();
}

/** Create a toast manager for notifications raised outside the React tree. */
// Kept with ToastProvider so consumers have one public toast module.
// eslint-disable-next-line react-refresh/only-export-components
export function createToastManager<
  Data extends object = Record<string, unknown>,
>(): ToastManager<Data> {
  return BaseToast.createToastManager<Data>();
}
