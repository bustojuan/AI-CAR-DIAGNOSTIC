import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach, vi } from "vitest";

// jsdom has no viewport scrolling; real keyboard/scroll behavior is covered in Playwright.
Object.defineProperty(window, "scrollTo", { value: vi.fn(), writable: true });

// Native dialog focus trapping is covered in Playwright; jsdom needs its API shim.
Object.defineProperties(HTMLDialogElement.prototype, {
  showModal: {
    configurable: true,
    value() {
      this.setAttribute("open", "");
    },
  },
  close: {
    configurable: true,
    value() {
      this.removeAttribute("open");
    },
  },
});

beforeEach(() => {
  Object.defineProperty(window, "innerWidth", {
    value: 1440,
    writable: true,
    configurable: true,
  });
});

afterEach(() => {
  cleanup();
  localStorage.clear();
  window.location.hash = "";
});
