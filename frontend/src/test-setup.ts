import "@testing-library/jest-dom/vitest";

// jsdom does not implement canvas rendering. axe-core's color-contrast and
// icon-ligature checks call HTMLCanvasElement.prototype.getContext while
// matching rules, which makes jsdom emit "Not implemented:
// HTMLCanvasElement.prototype.getContext (without installing the canvas npm
// package)" noise on every axe.run() in unit tests. jsdom already returns null
// from this method, and axe converts the downstream rule error into an
// incomplete result, so returning null keeps axe outcomes unchanged while
// removing the console noise. The Storybook project runs in a real browser and
// is unaffected.
if (typeof HTMLCanvasElement !== "undefined") {
  HTMLCanvasElement.prototype.getContext = () => null;
}

// jsdom's selector engine (nwsapi) implements the top-layer pseudo-classes
// :modal and :fullscreen by probing for a native implementation that jsdom
// does not have: its isModal/isFullscreen asserts call back into
// Element.matches, which re-enters nwsapi, and every failed probe unwinds
// through try/catch and re-descends, so one matches() call runs for minutes
// inside a single synchronous computation. Floating UI's positioning code
// calls element.matches(':modal') on every popover position pass while
// probing for top-layer elements (isTopLayer) and expects unsupported
// selectors to fail fast, so any test that opens a Base UI Popover blocks
// the event loop and hangs. jsdom has no fullscreen or modal top layer at
// all, so "not matched" is the correct answer for a bare top-layer
// pseudo-class; all other selectors keep using jsdom's normal matching.
// The Storybook project runs in a real browser and is unaffected.
const topLayerPseudoSelectors = new Set([":modal", ":fullscreen"]);
const elementProto = Element.prototype as unknown as {
  matches?: (selector: string) => boolean;
  webkitMatchesSelector?: (selector: string) => boolean;
};

for (const method of ["matches", "webkitMatchesSelector"] as const) {
  const original = elementProto[method];
  if (typeof original === "function") {
    elementProto[method] = function matchesWithoutTopLayerPseudos(selector: string) {
      if (topLayerPseudoSelectors.has(selector)) {
        return false;
      }
      return original.call(this, selector);
    };
  }
}
