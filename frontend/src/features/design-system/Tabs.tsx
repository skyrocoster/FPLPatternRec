import { Tabs as BaseTabs } from "@base-ui/react/tabs";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useCallback, useEffect, useId, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { ComponentPropsWithoutRef, KeyboardEvent, ReactNode } from "react";

import styles from "./Tabs.module.css";

export interface TabDefinition {
  /** Unique, stable identifier for this tab within the Tabs instance. */
  id: string;
  /** Accessible and visible tab label. */
  label: string;
  /** Consumer-owned panel content. Panels remain mounted while inactive. */
  content: ReactNode;
  /** Disabled tabs cannot be activated or reached by roving keyboard focus. */
  disabled?: boolean;
}

export interface TabsProps extends Omit<ComponentPropsWithoutRef<"div">, "children"> {
  /** Caller-owned tab definitions. IDs must be unique within this instance. */
  tabs: readonly TabDefinition[];
  /** Initial selection for uncontrolled usage. */
  defaultSelectedId?: string;
  /** Selection for controlled usage. */
  selectedId?: string;
  /** Called when user interaction requests a different tab. */
  onSelectedIdChange?: (selectedId: string) => void;
  /** Accessible name for the tablist. */
  ariaLabel?: string;
}

const SCROLL_EDGE_TOLERANCE = 1;

interface ScrollState {
  hasOverflow: boolean;
  canScrollStart: boolean;
  canScrollEnd: boolean;
}

const INITIAL_SCROLL_STATE: ScrollState = {
  hasOverflow: false,
  canScrollStart: false,
  canScrollEnd: false,
};

function enabledTabsFrom(tabs: readonly TabDefinition[]) {
  return tabs.filter((tab) => !tab.disabled);
}

function initialSelection(
  tabs: readonly TabDefinition[],
  requestedId: string | undefined,
): string | undefined {
  return (
    tabs.find((tab) => tab.id === requestedId && !tab.disabled)?.id ??
    tabs.find((tab) => !tab.disabled)?.id
  );
}

function scrollStateFor(
  scrollElement: HTMLDivElement,
  scrollLeft = scrollElement.scrollLeft,
): ScrollState {
  const maxScrollLeft = Math.max(0, scrollElement.scrollWidth - scrollElement.clientWidth);
  const normalizedScrollLeft = Math.max(0, scrollLeft);

  return {
    hasOverflow: maxScrollLeft > SCROLL_EDGE_TOLERANCE,
    canScrollStart: normalizedScrollLeft > SCROLL_EDGE_TOLERANCE,
    canScrollEnd: normalizedScrollLeft < maxScrollLeft - SCROLL_EDGE_TOLERANCE,
  };
}

function domIdFor(prefix: string, tabId: string, suffix: "tab" | "panel") {
  return `${prefix}-${encodeURIComponent(tabId)}-${suffix}`;
}

/**
 * Shared horizontal tabs with an underlined selected state and an overflow rail.
 *
 * The component owns selection and rail interaction only. Consumers own panel
 * content and the placement/surface around the component.
 */
export function Tabs({
  tabs,
  defaultSelectedId,
  selectedId: selectedIdProp,
  onSelectedIdChange,
  ariaLabel = "Tabs",
  className,
  ...rest
}: TabsProps) {
  const [uncontrolledSelectedId, setUncontrolledSelectedId] = useState<string | undefined>(() =>
    initialSelection(tabs, defaultSelectedId),
  );
  const [scrollState, setScrollState] = useState<ScrollState>(INITIAL_SCROLL_STATE);
  const tabsScrollRef = useRef<HTMLDivElement | null>(null);
  const tabRefs = useRef(new Map<string, HTMLElement>());
  const idPrefix = `tabs-${useId().replaceAll(":", "")}`;
  const enabledTabs = useMemo(() => enabledTabsFrom(tabs), [tabs]);
  const requestedSelectedId = selectedIdProp ?? uncontrolledSelectedId;
  const lastRequestedIdRef = useRef(requestedSelectedId);
  const selectedTabDefinition =
    tabs.find((tab) => tab.id === requestedSelectedId && !tab.disabled) ?? enabledTabs[0];
  const selectedId = selectedTabDefinition?.id;
  const tabsLayoutKey = JSON.stringify(
    tabs.map((tab) => [tab.id, tab.label, Boolean(tab.disabled)]),
  );

  const setScrollStateIfChanged = useCallback((nextState: ScrollState) => {
    setScrollState((currentState) =>
      currentState.hasOverflow === nextState.hasOverflow &&
      currentState.canScrollStart === nextState.canScrollStart &&
      currentState.canScrollEnd === nextState.canScrollEnd
        ? currentState
        : nextState,
    );
  }, []);

  const updateScrollState = useCallback(() => {
    const scrollElement = tabsScrollRef.current;
    if (!scrollElement) return;

    setScrollStateIfChanged(scrollStateFor(scrollElement));
  }, [setScrollStateIfChanged]);

  const handleWheel = useCallback(
    (event: WheelEvent) => {
      const scrollElement = event.currentTarget;
      if (!(scrollElement instanceof HTMLDivElement)) return;

      const verticalDelta = Math.abs(event.deltaY) >= Math.abs(event.deltaX) ? event.deltaY : 0;
      if (verticalDelta === 0) return;

      const maxScrollLeft = Math.max(0, scrollElement.scrollWidth - scrollElement.clientWidth);
      const targetScrollLeft = Math.min(
        maxScrollLeft,
        Math.max(0, scrollElement.scrollLeft + verticalDelta),
      );
      if (targetScrollLeft === scrollElement.scrollLeft) return;

      event.preventDefault();
      scrollElement.scrollLeft = targetScrollLeft;
      setScrollStateIfChanged(scrollStateFor(scrollElement, targetScrollLeft));
    },
    [setScrollStateIfChanged],
  );

  const revealTab = useCallback((tabId: string) => {
    const scroller = tabsScrollRef.current;
    const tab = tabRefs.current.get(tabId);
    if (!scroller || !tab) return;

    // Adjust only the horizontal tab rail so the page never scrolls vertically.
    const scrollerRect = scroller.getBoundingClientRect();
    const tabRect = tab.getBoundingClientRect();
    if (tabRect.left < scrollerRect.left) {
      scroller.scrollLeft -= scrollerRect.left - tabRect.left;
    } else if (tabRect.right > scrollerRect.right) {
      scroller.scrollLeft += tabRect.right - scrollerRect.right;
    }
  }, []);

  useEffect(() => {
    if (selectedIdProp !== undefined || uncontrolledSelectedId === selectedId) return;
    setUncontrolledSelectedId(selectedId);
  }, [selectedId, selectedIdProp, uncontrolledSelectedId]);

  useEffect(() => {
    lastRequestedIdRef.current = requestedSelectedId;
  }, [requestedSelectedId]);

  // Base UI models disabled composite tabs with aria-disabled. Preserve this
  // wrapper's established native-button contract for consumers and tests.
  useLayoutEffect(() => {
    for (const tab of tabs) {
      const element = tabRefs.current.get(tab.id);
      if (element instanceof HTMLButtonElement) element.disabled = Boolean(tab.disabled);
    }
  }, [tabs, tabsLayoutKey]);

  useEffect(() => {
    if (selectedId) revealTab(selectedId);
  }, [revealTab, selectedId]);

  useEffect(() => {
    updateScrollState();
  }, [tabsLayoutKey, updateScrollState]);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const scrollElement = tabsScrollRef.current;
    const tabList = scrollElement?.firstElementChild;
    if (!scrollElement || !(tabList instanceof HTMLElement)) return;

    scrollElement.addEventListener("scroll", updateScrollState, { passive: true });
    scrollElement.addEventListener("wheel", handleWheel, { passive: false });
    window.addEventListener("resize", updateScrollState);

    const resizeObserver =
      typeof ResizeObserver === "undefined" ? null : new ResizeObserver(updateScrollState);
    resizeObserver?.observe(scrollElement);
    resizeObserver?.observe(tabList);

    const mutationObserver =
      typeof MutationObserver === "undefined" ? null : new MutationObserver(updateScrollState);
    mutationObserver?.observe(tabList, {
      attributeFilter: ["class", "disabled", "style"],
      attributes: true,
      characterData: true,
      childList: true,
      subtree: true,
    });

    updateScrollState();
    return () => {
      scrollElement.removeEventListener("scroll", updateScrollState);
      scrollElement.removeEventListener("wheel", handleWheel);
      window.removeEventListener("resize", updateScrollState);
      resizeObserver?.disconnect();
      mutationObserver?.disconnect();
    };
  }, [handleWheel, updateScrollState]);

  const activateTab = useCallback(
    (tabId: string, moveFocus = false) => {
      const tab = tabs.find((candidate) => candidate.id === tabId);
      if (!tab || tab.disabled) return;

      const currentRequestedId = lastRequestedIdRef.current;
      if (selectedIdProp === undefined && currentRequestedId !== tab.id) {
        setUncontrolledSelectedId(tab.id);
      }
      if (currentRequestedId !== tab.id) {
        lastRequestedIdRef.current = tab.id;
        onSelectedIdChange?.(tab.id);
      }
      if (moveFocus) {
        tabRefs.current.get(tabId)?.focus();
      }
    },
    [onSelectedIdChange, selectedIdProp, tabs],
  );

  const handleTabKeyDown = useCallback(
    (event: KeyboardEvent<HTMLElement>, tabId: string) => {
      const currentIndex = enabledTabs.findIndex((tab) => tab.id === tabId);
      if (currentIndex < 0) return;

      let nextIndex: number;
      if (event.key === "ArrowRight" || event.key === "ArrowDown") {
        nextIndex = (currentIndex + 1) % enabledTabs.length;
      } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
        nextIndex = (currentIndex - 1 + enabledTabs.length) % enabledTabs.length;
      } else if (event.key === "Home") {
        nextIndex = 0;
      } else if (event.key === "End") {
        nextIndex = enabledTabs.length - 1;
      } else {
        return;
      }

      event.preventDefault();
      activateTab(enabledTabs[nextIndex].id, true);
    },
    [activateTab, enabledTabs],
  );

  const scrollTabs = (direction: -1 | 1) => {
    const scrollElement = tabsScrollRef.current;
    if (!scrollElement) return;

    const maxScrollLeft = Math.max(0, scrollElement.scrollWidth - scrollElement.clientWidth);
    const distance = Math.max(scrollElement.clientWidth - 48, 1);
    const targetScrollLeft = Math.min(
      maxScrollLeft,
      Math.max(0, scrollElement.scrollLeft + direction * distance),
    );

    if (targetScrollLeft === scrollElement.scrollLeft) return;

    scrollElement.scrollLeft = targetScrollLeft;
    setScrollStateIfChanged(scrollStateFor(scrollElement, targetScrollLeft));
  };

  return (
    <BaseTabs.Root
      {...rest}
      className={[styles.tabs, className].filter(Boolean).join(" ")}
      data-testid="tabs"
      value={selectedId ?? null}
      onValueChange={(nextValue) => {
        if (typeof nextValue === "string") activateTab(nextValue);
      }}
    >
      <span
        className={styles.visuallyHidden}
        aria-live="polite"
        data-selection-status
        data-testid="tabs-selection-status"
      >
        Active tab: {selectedTabDefinition?.label ?? "None"}
      </span>

      <div
        className={styles.tabsNavigation}
        data-overflow={scrollState.hasOverflow ? "true" : "false"}
        data-testid="tabs-navigation"
      >
        {scrollState.hasOverflow ? (
          <button
            className={styles.scrollButton}
            type="button"
            aria-label="Scroll tabs left"
            disabled={!scrollState.canScrollStart}
            onClick={() => scrollTabs(-1)}
          >
            <ChevronLeft aria-hidden="true" focusable="false" />
          </button>
        ) : null}

        <div
          className={styles.tabsViewport}
          data-hidden-start={scrollState.canScrollStart ? "true" : "false"}
          data-hidden-end={scrollState.canScrollEnd ? "true" : "false"}
        >
          <div ref={tabsScrollRef} className={styles.tabsScroll} data-testid="tabs-scroll">
            <BaseTabs.List
              className={styles.tabList}
              aria-label={ariaLabel}
              aria-orientation="horizontal"
            >
              {tabs.map((tab) => {
                const tabId = domIdFor(idPrefix, tab.id, "tab");
                const panelId = domIdFor(idPrefix, tab.id, "panel");

                return (
                  <BaseTabs.Tab
                    key={tab.id}
                    ref={(element) => {
                      if (element) {
                        tabRefs.current.set(tab.id, element);
                      } else {
                        tabRefs.current.delete(tab.id);
                      }
                    }}
                    className={styles.tab}
                    id={tabId}
                    value={tab.id}
                    aria-controls={panelId}
                    disabled={tab.disabled}
                    onKeyDown={(event) => handleTabKeyDown(event, tab.id)}
                    onFocus={() => revealTab(tab.id)}
                  >
                    {tab.label}
                  </BaseTabs.Tab>
                );
              })}
            </BaseTabs.List>
          </div>
        </div>

        {scrollState.hasOverflow ? (
          <button
            className={styles.scrollButton}
            type="button"
            aria-label="Scroll tabs right"
            disabled={!scrollState.canScrollEnd}
            onClick={() => scrollTabs(1)}
          >
            <ChevronRight aria-hidden="true" focusable="false" />
          </button>
        ) : null}
      </div>

      <div className={styles.panelViewport}>
        {tabs.map((tab) => {
          const tabId = domIdFor(idPrefix, tab.id, "tab");
          const panelId = domIdFor(idPrefix, tab.id, "panel");

          return (
            <BaseTabs.Panel
              key={tab.id}
              id={panelId}
              className={styles.tabPanel}
              value={tab.id}
              keepMounted
              render={<section />}
              aria-labelledby={tabId}
              tabIndex={0}
              data-tab-panel={tab.id}
              data-testid={`tabs-panel-${tab.id}`}
            >
              {tab.content}
            </BaseTabs.Panel>
          );
        })}
      </div>
    </BaseTabs.Root>
  );
}
