import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeEach } from "vitest";
import { resetMatchMedia } from "./matchMedia";

// jsdom не реализует ResizeObserver, а antd (Menu, Segmented и др.) его использует
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver ??= ResizeObserverStub;

beforeEach(() => {
  resetMatchMedia();
  window.localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
});

afterEach(() => {
  cleanup();
});

// Таймеры задержки popup/tooltip antd (rc-trigger, 100 мс) не отменяются при размонтировании и срабатывают после
// остановки jsdom (`window is not defined`); ждём их, чтобы тестовый файл не завершился раньше
afterAll(() => new Promise((resolve) => setTimeout(resolve, 200)));
