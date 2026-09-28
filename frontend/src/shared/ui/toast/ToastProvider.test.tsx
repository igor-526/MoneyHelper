import { act, fireEvent, render, screen } from "@testing-library/react";
import { useEffect } from "react";
import { ConfigProvider } from "antd";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ToastProvider, useToast } from "./ToastProvider";
import type { ToastApi } from "./types";

let api: ToastApi;

function Capture() {
  const toast = useToast();
  useEffect(() => {
    api = toast;
  }, [toast]);
  return null;
}

function renderToasts() {
  return render(
    <ConfigProvider theme={{ token: { motion: false } }}>
      <ToastProvider>
        <Capture />
      </ToastProvider>
    </ConfigProvider>,
  );
}

const show = (fn: () => void) => act(fn);

beforeEach(() => vi.useFakeTimers());
afterEach(() => {
  vi.runOnlyPendingTimers();
  vi.useRealTimers();
});

describe("ToastProvider", () => {
  it("показывает уведомление об ошибке с role=alert", () => {
    renderToasts();
    show(() => api.error("Не удалось сохранить"));
    expect(screen.getByRole("alert")).toHaveTextContent("Не удалось сохранить");
  });

  it("успех и предупреждение имеют role=status", () => {
    renderToasts();
    show(() => {
      api.success("Готово");
      api.warning("Внимание");
    });
    expect(screen.getAllByRole("status").map((el) => el.textContent)).toEqual([
      "Готово",
      "Внимание",
    ]);
  });

  it("скрывает успех через 4 секунды, ошибку — через 8", () => {
    renderToasts();
    show(() => {
      api.success("Готово");
      api.error("Сбой");
    });
    act(() => void vi.advanceTimersByTime(4100));
    expect(screen.queryByText("Готово")).not.toBeInTheDocument();
    expect(screen.getByText("Сбой")).toBeInTheDocument();
    act(() => void vi.advanceTimersByTime(4100));
    expect(screen.queryByText("Сбой")).not.toBeInTheDocument();
  });

  it("закрывается нажатием", () => {
    renderToasts();
    show(() => api.error("Сбой"));
    fireEvent.click(screen.getByText("Сбой"));
    expect(screen.queryByText("Сбой")).not.toBeInTheDocument();
  });

  it("не дублирует одинаковое уведомление и продлевает время показа", () => {
    renderToasts();
    show(() => api.error("Сбой"));
    act(() => void vi.advanceTimersByTime(6000));
    show(() => api.error("Сбой"));
    expect(screen.getAllByText("Сбой")).toHaveLength(1);
    act(() => void vi.advanceTimersByTime(6000));
    expect(screen.getByText("Сбой")).toBeInTheDocument();
  });

  it("показывает не более трёх уведомлений, вытесняя старые", () => {
    renderToasts();
    show(() => {
      ["Первое", "Второе", "Третье", "Четвёртое"].forEach((text) => api.warning(text));
    });
    expect(screen.queryByText("Первое")).not.toBeInTheDocument();
    ["Второе", "Третье", "Четвёртое"].forEach((text) =>
      expect(screen.getByText(text)).toBeInTheDocument(),
    );
  });

  it("dismiss закрывает уведомление по идентификатору", () => {
    renderToasts();
    let id = "";
    show(() => {
      id = api.error("Сбой");
    });
    show(() => api.dismiss(id));
    expect(screen.queryByText("Сбой")).not.toBeInTheDocument();
  });

  it("useToast вне провайдера бросает понятную ошибку", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    expect(() => render(<Capture />)).toThrow(/ToastProvider/);
    spy.mockRestore();
  });
});
