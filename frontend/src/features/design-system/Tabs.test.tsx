import { cleanup, createEvent, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Tabs, type TabDefinition } from "./Tabs";

afterEach(() => {
  cleanup();
});

const here = dirname(fileURLToPath(import.meta.url));
const moduleCss = readFileSync(join(here, "Tabs.module.css"), "utf8");

function ruleBlock(css: string, selector: string): string {
  const match = css.match(new RegExp(`${selector}\\s*\\{[^}]*\\}`));
  return match ? match[0] : "";
}

const OVERFLOW_TABS: readonly TabDefinition[] = [
  { id: "overview", label: "Overview", content: "Overview copy." },
  { id: "activity", label: "Activity", content: "Activity copy." },
  { id: "details", label: "Details", content: "Details copy." },
  { id: "notes", label: "Notes", content: "Notes copy." },
  { id: "schedule", label: "Schedule", content: "Schedule copy." },
  { id: "insights", label: "Insights", content: "Insights copy." },
  { id: "history", label: "History", content: "History copy." },
  { id: "settings", label: "Settings", content: "Settings copy." },
];

const BASE_TABS: readonly TabDefinition[] = [
  {
    id: "overview",
    label: "Overview",
    content: <div data-testid="overview-content">Overview component</div>,
  },
  {
    id: "activity",
    label: "Activity",
    content: <div data-testid="activity-content">Activity component</div>,
  },
  {
    id: "details",
    label: "Details",
    content: <div data-testid="details-content">Details component</div>,
  },
  {
    id: "notes",
    label: "Notes",
    content: <div data-testid="notes-content">Notes component</div>,
  },
];

const DISABLED_TABS: readonly TabDefinition[] = [
  BASE_TABS[0],
  { ...BASE_TABS[1], disabled: true },
  BASE_TABS[2],
  { ...BASE_TABS[3], disabled: true },
];

function mockScrollMetrics(
  scrollElement: HTMLElement,
  initial: { clientWidth: number; scrollWidth: number; scrollLeft?: number },
) {
  let clientWidth = initial.clientWidth;
  let scrollWidth = initial.scrollWidth;
  let scrollLeft = initial.scrollLeft ?? 0;

  Object.defineProperties(scrollElement, {
    clientWidth: { configurable: true, get: () => clientWidth },
    scrollWidth: { configurable: true, get: () => scrollWidth },
    scrollLeft: {
      configurable: true,
      get: () => scrollLeft,
      set: (value: number) => {
        scrollLeft = value;
      },
    },
    scrollTo: {
      configurable: true,
      value: ({ left }: { left: number }) => {
        scrollLeft = left;
      },
    },
  });

  return {
    setClientWidth: (value: number) => {
      clientWidth = value;
    },
    setScrollWidth: (value: number) => {
      scrollWidth = value;
    },
    setScrollLeft: (value: number) => {
      scrollLeft = value;
    },
    getScrollLeft: () => scrollLeft,
  };
}

describe("Tabs", () => {
  it("supports generic string IDs, custom labeling, forwarded root props, and stable relationships", () => {
    const stringIdTabs: readonly TabDefinition[] = [
      { id: "first line/one", label: "First", content: "First content" },
      { id: "second-line two", label: "Second", content: "Second content" },
    ];
    const view = render(
      <Tabs
        ariaLabel="Section tabs"
        className="consumer-tabs"
        data-owner="sections"
        id="section-tabs"
        tabs={stringIdTabs}
        title="Section tab set"
      />,
    );

    const root = screen.getByTestId("tabs");
    expect(root).toHaveClass("consumer-tabs");
    expect(root).toHaveAttribute("data-owner", "sections");
    expect(root).toHaveAttribute("id", "section-tabs");
    expect(root).toHaveAttribute("title", "Section tab set");
    expect(screen.getByRole("tablist", { name: "Section tabs" })).toBeInTheDocument();

    const relationshipsByLabel = new Map(
      screen
        .getAllByRole("tab")
        .map((tab) => [
          tab.textContent,
          { tabId: tab.id, panelId: tab.getAttribute("aria-controls") },
        ]),
    );
    expect(new Set([...relationshipsByLabel.values()].map(({ tabId }) => tabId)).size).toBe(2);
    expect(new Set([...relationshipsByLabel.values()].map(({ panelId }) => panelId)).size).toBe(2);

    view.rerender(
      <Tabs
        ariaLabel="Section tabs"
        className="consumer-tabs"
        data-owner="sections"
        id="section-tabs"
        tabs={[...stringIdTabs].reverse()}
        title="Section tab set"
      />,
    );

    for (const [label, relationship] of relationshipsByLabel) {
      const tab = screen.getByRole("tab", { name: label ?? "" });
      expect(tab).toHaveAttribute("id", relationship.tabId);
      expect(tab).toHaveAttribute("aria-controls", relationship.panelId);
      expect(document.getElementById(relationship.panelId ?? "")).toHaveAttribute(
        "aria-labelledby",
        relationship.tabId,
      );
    }

    render(<Tabs tabs={stringIdTabs} />);
    const allTabIds = screen.getAllByRole("tab").map((tab) => tab.id);
    const allPanelIds = screen.getAllByRole("tabpanel", { hidden: true }).map((panel) => panel.id);
    expect(new Set(allTabIds).size).toBe(allTabIds.length);
    expect(new Set(allPanelIds).size).toBe(allPanelIds.length);
  });

  it("renders only caller-owned panel content without navigation links", () => {
    render(<Tabs tabs={BASE_TABS} />);

    expect(screen.queryByRole("link")).not.toBeInTheDocument();

    const announcement = screen.getByTestId("tabs-selection-status");
    expect(announcement).toHaveAttribute("aria-live", "polite");
    expect(announcement).toHaveAttribute("data-selection-status");
    expect(screen.getByRole("tablist", { name: "Tabs" })).toBeVisible();
    expect(screen.getByTestId("overview-content")).toBeVisible();
    expect(screen.getByTestId("activity-content")).not.toBeVisible();
  });

  it("hosts arbitrary caller content in only the selected panel", async () => {
    const user = userEvent.setup();
    render(<Tabs tabs={BASE_TABS} />);

    expect(screen.getByTestId("overview-content")).toBeVisible();
    expect(screen.getByTestId("activity-content")).not.toBeVisible();

    await user.click(screen.getByRole("tab", { name: "Activity" }));

    expect(screen.getByTestId("activity-content")).toBeVisible();
    expect(screen.getByTestId("overview-content")).not.toBeVisible();
  });

  it("keeps mounted caller content current while hiding every inactive panel", async () => {
    const user = userEvent.setup();
    const view = render(<Tabs tabs={BASE_TABS} />);

    await user.click(screen.getByRole("tab", { name: "Activity" }));
    view.rerender(
      <Tabs
        tabs={BASE_TABS.map((tab) =>
          tab.id === "activity"
            ? { ...tab, content: <div data-testid="activity-content">Updated activity</div> }
            : tab,
        )}
      />,
    );

    expect(screen.getByTestId("activity-content")).toHaveTextContent("Updated activity");
    expect(screen.getByTestId("activity-content")).toBeVisible();
    expect(screen.getByTestId("overview-content")).toBeInTheDocument();
    expect(screen.getByTestId("overview-content")).not.toBeVisible();
    expect(
      screen.getAllByRole("tabpanel", { hidden: true }).filter((panel) => !panel.hidden),
    ).toHaveLength(1);
  });

  it("uses the first enabled tab for an invalid or disabled default", () => {
    render(<Tabs defaultSelectedId="activity" tabs={DISABLED_TABS} />);

    expect(screen.getByRole("tab", { name: "Overview", selected: true })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Activity" })).toBeDisabled();
    expect(screen.getByRole("tab", { name: "Activity" })).not.toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("falls back when an uncontrolled selected tab is removed or disabled", async () => {
    const view = render(<Tabs defaultSelectedId="details" tabs={BASE_TABS} />);

    expect(screen.getByRole("tab", { name: "Details", selected: true })).toBeInTheDocument();

    view.rerender(<Tabs tabs={BASE_TABS.filter((tab) => tab.id !== "details")} />);
    await waitFor(() => {
      expect(screen.getByRole("tab", { name: "Overview", selected: true })).toBeInTheDocument();
    });

    view.rerender(
      <Tabs
        tabs={BASE_TABS.map((tab) => (tab.id === "overview" ? { ...tab, disabled: true } : tab))}
      />,
    );
    await waitFor(() => {
      expect(screen.getByRole("tab", { name: "Activity", selected: true })).toBeInTheDocument();
    });
  });

  it("uses an enabled fallback for invalid and removed controlled selections", async () => {
    const view = render(<Tabs selectedId="missing" tabs={DISABLED_TABS} />);

    expect(screen.getByRole("tab", { name: "Overview", selected: true })).toBeInTheDocument();

    view.rerender(<Tabs selectedId="details" tabs={DISABLED_TABS} />);
    expect(screen.getByRole("tab", { name: "Details", selected: true })).toBeInTheDocument();

    view.rerender(
      <Tabs selectedId="details" tabs={DISABLED_TABS.filter((tab) => tab.id !== "details")} />,
    );
    await waitFor(() => {
      expect(screen.getByRole("tab", { name: "Overview", selected: true })).toBeInTheDocument();
    });
  });

  it("keeps controlled selection unchanged until the caller rerenders and reports only changes", async () => {
    const user = userEvent.setup();
    const onSelectedIdChange = vi.fn();
    const view = render(
      <Tabs onSelectedIdChange={onSelectedIdChange} selectedId="overview" tabs={BASE_TABS} />,
    );

    await user.click(screen.getByRole("tab", { name: "Activity" }));
    expect(onSelectedIdChange).toHaveBeenCalledOnce();
    expect(onSelectedIdChange).toHaveBeenLastCalledWith("activity");
    expect(screen.getByRole("tab", { name: "Overview", selected: true })).toBeInTheDocument();

    view.rerender(
      <Tabs onSelectedIdChange={onSelectedIdChange} selectedId="activity" tabs={BASE_TABS} />,
    );
    expect(screen.getByRole("tab", { name: "Activity", selected: true })).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Activity" }));
    expect(onSelectedIdChange).toHaveBeenCalledOnce();

    await user.click(screen.getByRole("tab", { name: "Overview" }));
    expect(onSelectedIdChange).toHaveBeenCalledTimes(2);
    expect(onSelectedIdChange).toHaveBeenLastCalledWith("overview");
    expect(screen.getByRole("tab", { name: "Activity", selected: true })).toBeInTheDocument();
  });

  it("prevents disabled activation and skips disabled tabs during roving navigation", async () => {
    const user = userEvent.setup();
    const onSelectedIdChange = vi.fn();
    render(<Tabs onSelectedIdChange={onSelectedIdChange} tabs={DISABLED_TABS} />);

    const overview = screen.getByRole("tab", { name: "Overview" });
    const activity = screen.getByRole("tab", { name: "Activity" });
    const details = screen.getByRole("tab", { name: "Details" });
    const notes = screen.getByRole("tab", { name: "Notes" });

    expect(activity).toBeDisabled();
    await user.click(activity);
    expect(overview).toHaveAttribute("aria-selected", "true");
    expect(onSelectedIdChange).not.toHaveBeenCalled();

    await overview.focus();
    await user.keyboard("{ArrowRight}");
    expect(details).toHaveFocus();
    expect(details).toHaveAttribute("aria-selected", "true");

    await user.keyboard("{ArrowDown}");
    expect(overview).toHaveFocus();
    expect(overview).toHaveAttribute("aria-selected", "true");
    expect(activity).toHaveAttribute("tabindex", "-1");
    expect(notes).toHaveAttribute("tabindex", "-1");
  });

  it("renders one selected tab and one visible associated panel", () => {
    render(<Tabs tabs={BASE_TABS} />);

    const tabs = screen.getAllByRole("tab");
    expect(tabs).toHaveLength(4);
    expect(tabs.filter((tab) => tab.getAttribute("aria-selected") === "true")).toHaveLength(1);

    const selected = screen.getByRole("tab", { name: "Overview" });
    const selectedPanelId = selected.getAttribute("aria-controls");
    expect(selectedPanelId).not.toBeNull();
    expect(document.getElementById(selectedPanelId ?? "")).toBeVisible();
    expect(screen.getByTestId("tabs-selection-status")).toHaveAttribute("aria-live", "polite");

    const panels = screen.getAllByRole("tabpanel", { hidden: true });
    expect(panels).toHaveLength(4);
    expect(panels.filter((panel) => !panel.hasAttribute("hidden"))).toHaveLength(1);
  });

  it("updates the selected panel and polite readout on click", async () => {
    const user = userEvent.setup();
    render(<Tabs tabs={BASE_TABS} />);

    const activity = screen.getByRole("tab", { name: "Activity" });
    await user.click(activity);

    expect(activity).toHaveFocus();
    expect(activity).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("tabs-selection-status")).toHaveTextContent("Active tab: Activity");
    expect(screen.getByTestId("tabs-selection-status")).toHaveAttribute("data-selection-status");
    expect(screen.getByRole("tabpanel", { name: "Activity" })).toBeVisible();
    expect(screen.getByTestId("tabs-panel-overview")).toHaveAttribute("hidden");
    expect(screen.getAllByRole("tab", { selected: true })).toHaveLength(1);
  });

  it("supports roving keyboard navigation with wrapping and jumps", async () => {
    const user = userEvent.setup();
    render(<Tabs tabs={BASE_TABS} />);

    const overview = screen.getByRole("tab", { name: "Overview" });
    const activity = screen.getByRole("tab", { name: "Activity" });
    const details = screen.getByRole("tab", { name: "Details" });
    const notes = screen.getByRole("tab", { name: "Notes" });

    await overview.focus();
    await user.keyboard("{ArrowLeft}");
    expect(notes).toHaveFocus();
    expect(notes).toHaveAttribute("aria-selected", "true");

    await user.keyboard("{ArrowUp}");
    expect(details).toHaveFocus();
    expect(details).toHaveAttribute("aria-selected", "true");

    await user.keyboard("{Home}");
    expect(overview).toHaveFocus();
    expect(overview).toHaveAttribute("aria-selected", "true");

    await user.keyboard("{End}");
    expect(notes).toHaveFocus();
    expect(notes).toHaveAttribute("aria-selected", "true");

    await activity.focus();
    await user.keyboard("{Enter}");
    expect(activity).toHaveAttribute("aria-selected", "true");

    await details.focus();
    await user.keyboard(" ");
    expect(details).toHaveAttribute("aria-selected", "true");
    expect(screen.getAllByRole("tab", { selected: true })).toHaveLength(1);

    await user.keyboard("{ArrowRight}");
    expect(notes).toHaveFocus();
    await user.keyboard("{ArrowDown}");
    expect(overview).toHaveFocus();
  });

  it("keeps tab and panel relationships explicit in the accessibility tree", () => {
    render(<Tabs defaultSelectedId="details" tabs={BASE_TABS} />);

    const tablist = screen.getByRole("tablist", { name: "Tabs" });
    expect(tablist).toHaveAttribute("aria-orientation", "horizontal");

    for (const tab of screen.getAllByRole("tab")) {
      const panelId = tab.getAttribute("aria-controls");
      expect(panelId).not.toBeNull();
      const panel = document.getElementById(panelId ?? "");
      expect(panel).not.toBeNull();
      expect(panel).toHaveAttribute("role", "tabpanel");
      expect(panel).toHaveAttribute("aria-labelledby", tab.id);
      expect(tab).toHaveAttribute(
        "tabindex",
        tab.getAttribute("aria-selected") === "true" ? "0" : "-1",
      );
    }

    expect(screen.getByTestId("tabs-selection-status")).toHaveAttribute("aria-live", "polite");
  });

  it("shows directional controls and edge cues only while tabs overflow", async () => {
    const { rerender } = render(<Tabs tabs={BASE_TABS} />);
    const fittingScroll = screen.getByTestId("tabs-scroll");
    const fittingMetrics = mockScrollMetrics(fittingScroll, { clientWidth: 320, scrollWidth: 320 });

    fireEvent.resize(window);
    expect(screen.getByTestId("tabs-navigation")).toHaveAttribute("data-overflow", "false");
    expect(screen.queryByRole("button", { name: "Scroll tabs left" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Scroll tabs right" })).not.toBeInTheDocument();
    expect(fittingScroll.parentElement).toHaveAttribute("data-hidden-start", "false");
    expect(fittingScroll.parentElement).toHaveAttribute("data-hidden-end", "false");

    fittingMetrics.setScrollWidth(920);
    rerender(<Tabs tabs={OVERFLOW_TABS} />);

    await waitFor(() => {
      expect(screen.getByTestId("tabs-navigation")).toHaveAttribute("data-overflow", "true");
    });

    const previous = screen.getByRole("button", { name: "Scroll tabs left" });
    const next = screen.getByRole("button", { name: "Scroll tabs right" });
    expect(previous).toBeDisabled();
    expect(next).toBeEnabled();
    expect(screen.getByTestId("tabs-scroll").parentElement).toHaveAttribute(
      "data-hidden-end",
      "true",
    );

    await userEvent.setup().click(next);
    expect(fittingMetrics.getScrollLeft()).toBe(272);
    expect(previous).toBeEnabled();
    expect(next).toBeEnabled();

    fittingMetrics.setScrollLeft(600);
    fireEvent.scroll(screen.getByTestId("tabs-scroll"));
    expect(previous).toBeEnabled();
    expect(next).toBeDisabled();
    expect(screen.getByTestId("tabs-scroll").parentElement).toHaveAttribute(
      "data-hidden-end",
      "false",
    );
  });

  it("converts only movable vertical wheel input and leaves native horizontal input alone", () => {
    render(<Tabs tabs={OVERFLOW_TABS} />);
    const scrollElement = screen.getByTestId("tabs-scroll");
    const metrics = mockScrollMetrics(scrollElement, {
      clientWidth: 320,
      scrollWidth: 920,
    });
    fireEvent.resize(window);

    const wheelEvent = createEvent.wheel(scrollElement, { deltaY: 120 });
    const preventDefault = vi.spyOn(wheelEvent, "preventDefault");
    fireEvent(scrollElement, wheelEvent);
    expect(preventDefault).toHaveBeenCalledOnce();
    expect(metrics.getScrollLeft()).toBe(120);

    const horizontalEvent = createEvent.wheel(scrollElement, { deltaX: 80, deltaY: 0 });
    const horizontalPreventDefault = vi.spyOn(horizontalEvent, "preventDefault");
    fireEvent(scrollElement, horizontalEvent);
    expect(horizontalPreventDefault).not.toHaveBeenCalled();
    expect(metrics.getScrollLeft()).toBe(120);

    metrics.setScrollLeft(600);
    fireEvent.scroll(scrollElement);
    const edgeEvent = createEvent.wheel(scrollElement, { deltaY: 120 });
    const edgePreventDefault = vi.spyOn(edgeEvent, "preventDefault");
    fireEvent(scrollElement, edgeEvent);
    expect(edgePreventDefault).not.toHaveBeenCalled();
    expect(metrics.getScrollLeft()).toBe(600);
  });

  it("reveals selected and programmatically focused tabs without changing tab semantics", async () => {
    const user = userEvent.setup();
    render(<Tabs tabs={OVERFLOW_TABS} />);

    const details = screen.getByRole("tab", { name: "Details" });
    const detailsScrollIntoView = vi.fn();
    Object.defineProperty(details, "scrollIntoView", {
      configurable: true,
      value: detailsScrollIntoView,
    });

    await user.click(details);
    expect(details).toHaveAttribute("aria-selected", "true");
    expect(detailsScrollIntoView).not.toHaveBeenCalled();

    const settings = screen.getByRole("tab", { name: "Settings" });
    const settingsScrollIntoView = vi.fn();
    Object.defineProperty(settings, "scrollIntoView", {
      configurable: true,
      value: settingsScrollIntoView,
    });
    await settings.focus();

    expect(settingsScrollIntoView).not.toHaveBeenCalled();
    expect(settings).toHaveAttribute("aria-selected", "false");
    expect(screen.getByTestId("tabs-selection-status")).toHaveTextContent("Active tab: Details");
  });

  it("updates overflow from available observers without resubscribing and disconnects them", async () => {
    const resizeCallbacks: Array<() => void> = [];
    const mutationCallbacks: Array<() => void> = [];
    const resizeTargets: Element[][] = [];
    const mutationTargets: Array<Array<{ target: Node; options?: MutationObserverInit }>> = [];
    const resizeDisconnected: number[] = [];
    const mutationDisconnected: number[] = [];
    const originalResizeObserver = globalThis.ResizeObserver;
    const originalMutationObserver = globalThis.MutationObserver;

    class TestResizeObserver {
      private readonly index: number;

      constructor(callback: ResizeObserverCallback) {
        this.index = resizeCallbacks.length;
        resizeCallbacks.push(() => callback([], this));
        resizeTargets.push([]);
      }

      observe(element: Element) {
        resizeTargets[this.index].push(element);
      }

      unobserve() {}

      disconnect() {
        resizeDisconnected.push(this.index);
      }
    }

    class TestMutationObserver {
      private readonly index: number;

      constructor(callback: MutationCallback) {
        this.index = mutationCallbacks.length;
        mutationCallbacks.push(() => callback([], this));
        mutationTargets.push([]);
      }

      observe(target: Node, options?: MutationObserverInit) {
        mutationTargets[this.index].push({ target, options });
      }

      disconnect() {
        mutationDisconnected.push(this.index);
      }

      takeRecords() {
        return [];
      }
    }

    vi.stubGlobal("ResizeObserver", TestResizeObserver);
    vi.stubGlobal("MutationObserver", TestMutationObserver);

    let view: ReturnType<typeof render> | undefined;
    try {
      view = render(<Tabs tabs={BASE_TABS} />);
      const scrollElement = screen.getByTestId("tabs-scroll");
      const metrics = mockScrollMetrics(scrollElement, { clientWidth: 320, scrollWidth: 920 });
      const tabList = scrollElement.firstElementChild;
      const resizeObserverIndex = resizeTargets.findIndex((targets) =>
        targets.includes(scrollElement),
      );
      const mutationObserverIndex = mutationTargets.findIndex((records) =>
        records.some(
          (record) => record.target === tabList && record.options?.attributeFilter !== undefined,
        ),
      );

      expect(resizeObserverIndex).toBeGreaterThanOrEqual(0);
      expect(resizeTargets[resizeObserverIndex]).toEqual([scrollElement, tabList]);
      expect(mutationObserverIndex).toBeGreaterThanOrEqual(0);
      expect(mutationTargets[mutationObserverIndex][0].options).toMatchObject({
        attributeFilter: ["class", "disabled", "style"],
        attributes: true,
        childList: true,
        subtree: true,
      });

      resizeCallbacks[resizeObserverIndex]?.();
      await waitFor(() => {
        expect(screen.getByTestId("tabs-navigation")).toHaveAttribute("data-overflow", "true");
      });

      metrics.setScrollLeft(400);
      mutationCallbacks[mutationObserverIndex]?.();
      await waitFor(() => {
        expect(screen.getByRole("button", { name: "Scroll tabs left" })).toBeEnabled();
      });

      const resizeObserversBeforeRerender = resizeTargets.filter((targets) =>
        targets.includes(scrollElement),
      ).length;
      const mutationObserversBeforeRerender = mutationTargets.filter((records) =>
        records.some(
          (record) => record.target === tabList && record.options?.attributeFilter !== undefined,
        ),
      ).length;
      view.rerender(<Tabs tabs={BASE_TABS} />);
      expect(resizeTargets.filter((targets) => targets.includes(scrollElement))).toHaveLength(
        resizeObserversBeforeRerender,
      );
      expect(
        mutationTargets.filter((records) =>
          records.some(
            (record) => record.target === tabList && record.options?.attributeFilter !== undefined,
          ),
        ),
      ).toHaveLength(mutationObserversBeforeRerender);

      view.unmount();
      expect(resizeDisconnected).toContain(resizeObserverIndex);
      expect(mutationDisconnected).toContain(mutationObserverIndex);
    } finally {
      view?.unmount();
      vi.stubGlobal("ResizeObserver", originalResizeObserver);
      vi.stubGlobal("MutationObserver", originalMutationObserver);
    }
  });

  it("does not require browser observers in jsdom", () => {
    const originalResizeObserver = globalThis.ResizeObserver;
    const originalMutationObserver = globalThis.MutationObserver;
    vi.stubGlobal("ResizeObserver", undefined);
    vi.stubGlobal("MutationObserver", undefined);

    let view: ReturnType<typeof render> | undefined;
    try {
      expect(() => {
        view = render(<Tabs tabs={BASE_TABS} />);
      }).not.toThrow();
    } finally {
      view?.unmount();
      vi.stubGlobal("ResizeObserver", originalResizeObserver);
      vi.stubGlobal("MutationObserver", originalMutationObserver);
    }
  });

  it("uses centralized tokens and the selected responsive/accessibility boundaries", () => {
    expect(moduleCss).toContain("var(--app-spacing-16)");
    expect(moduleCss).toContain("var(--app-focus-ring-width)");
    expect(moduleCss).toContain("var(--md-sys-color-surface-container)");
    const frameBlock = ruleBlock(moduleCss, "\\.tabs");
    expect(frameBlock).toContain("overflow: hidden;");
    expect(frameBlock).toContain("border: 1px solid var(--md-sys-color-outline-variant);");
    expect(frameBlock).toContain("border-radius: var(--app-radius-12);");
    expect(frameBlock).toContain("background: var(--md-sys-color-surface-container);");
    expect(frameBlock).toContain("box-shadow: var(--app-elevation-e1);");
    const navigationBlock = ruleBlock(moduleCss, "\\.tabsNavigation");
    expect(navigationBlock).toContain(
      "border-bottom: 1px solid var(--md-sys-color-outline-variant);",
    );
    expect(navigationBlock).not.toContain("border-radius");
    const hiddenBlock = ruleBlock(moduleCss, "\\.visuallyHidden");
    expect(hiddenBlock).toContain("position: absolute;");
    expect(hiddenBlock).toContain("clip-path: inset(50%);");
    expect(moduleCss).toContain("@media (prefers-reduced-motion: reduce)");
    expect(moduleCss).toContain("@media (forced-colors: active)");
    expect(moduleCss).toContain("pointer-events: none;");

    const tabBlock = ruleBlock(moduleCss, '\\.tab\\[aria-selected=\\"true\\"\\]::after');
    expect(tabBlock).toContain("background: var(--md-sys-color-primary);");
    const focusBlock = ruleBlock(moduleCss, "\\.tab:focus-visible");
    expect(focusBlock).toContain(
      "outline: var(--app-focus-ring-width) solid var(--app-focus-ring-color);",
    );
    expect(focusBlock).toContain("outline-offset: var(--app-focus-ring-separation);");

    const panelBlock = ruleBlock(moduleCss, "\\.tabPanel");
    expect(panelBlock).toContain("min-inline-size: 0;");
    expect(panelBlock).not.toContain("padding");
    expect(panelBlock).not.toContain("background");
    expect(panelBlock).not.toContain("border");
    expect(moduleCss).not.toMatch(/\.panel(Header|Heading|Title|Status|Body|Copy|statusDot)/);
    expect(moduleCss).not.toContain("--app-success-accent");

    expect(moduleCss).not.toMatch(/--app-[a-z0-9-]*\s*:/);
    expect(moduleCss).not.toMatch(/--md-sys-[a-z0-9-]*\s*:/);
  });
});
