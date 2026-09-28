import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { setMedia } from "@/test/matchMedia";
import { DARK_QUERY, ThemeProvider, useThemeMode } from "./ThemeProvider";
import { THEME_COLOR } from "./mode";

function Probe() {
  const { mode, resolved, setMode } = useThemeMode();
  return (
    <div>
      <span data-testid="state">{`${mode}/${resolved}`}</span>
      <button onClick={() => setMode("dark")}>dark</button>
      <button onClick={() => setMode("light")}>light</button>
      <button onClick={() => setMode("system")}>system</button>
    </div>
  );
}

function renderProbe() {
  return render(
    <ThemeProvider>
      <Probe />
    </ThemeProvider>,
  );
}

const state = () => screen.getByTestId("state").textContent;

describe("ThemeProvider", () => {
  it("по умолчанию следует системной тёмной теме", () => {
    setMedia(DARK_QUERY, true);
    renderProbe();
    expect(state()).toBe("system/dark");
    expect(document.documentElement).toHaveAttribute("data-theme", "dark");
    expect(document.documentElement.style.colorScheme).toBe("dark");
  });

  it("меняет тему на лету при смене системной настройки", () => {
    setMedia(DARK_QUERY, false);
    renderProbe();
    expect(state()).toBe("system/light");
    act(() => setMedia(DARK_QUERY, true));
    expect(state()).toBe("system/dark");
  });

  it("явный выбор не зависит от системной настройки", async () => {
    setMedia(DARK_QUERY, false);
    renderProbe();
    await userEvent.click(screen.getByText("dark"));
    expect(state()).toBe("dark/dark");
    act(() => setMedia(DARK_QUERY, false));
    expect(state()).toBe("dark/dark");
  });

  it("сохраняет выбор и восстанавливает после перезапуска", async () => {
    setMedia(DARK_QUERY, false);
    const first = renderProbe();
    await userEvent.click(screen.getByText("dark"));
    first.unmount();
    renderProbe();
    expect(state()).toBe("dark/dark");
  });

  it("при недопустимом сохранённом значении использует system", () => {
    window.localStorage.setItem("moneyhelper.theme", "blue");
    setMedia(DARK_QUERY, false);
    renderProbe();
    expect(state()).toBe("system/light");
  });

  it("обновляет theme-color по текущей теме", async () => {
    document.head.innerHTML =
      '<meta name="theme-color" content="#f5f5f5" media="(prefers-color-scheme: light)">';
    setMedia(DARK_QUERY, false);
    renderProbe();
    const meta = document.head.querySelector<HTMLMetaElement>('meta[name="theme-color"]');
    expect(meta?.content).toBe(THEME_COLOR.light);
    await userEvent.click(screen.getByText("dark"));
    expect(meta?.content).toBe(THEME_COLOR.dark);
    expect(meta?.hasAttribute("media")).toBe(false);
    document.head.innerHTML = "";
  });

  it("вне провайдера useThemeMode бросает понятную ошибку", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    expect(() => render(<Probe />)).toThrow(/ThemeProvider/);
    spy.mockRestore();
  });
});
