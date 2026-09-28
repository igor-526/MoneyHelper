import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { pwaMock, updateServiceWorker } from "@/test/pwa-register-react";
import { PwaBanners } from "./PwaBanners";

let onLine: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  pwaMock.reset();
  onLine = vi.spyOn(window.navigator, "onLine", "get").mockReturnValue(true);
});
afterEach(() => vi.restoreAllMocks());

describe("PwaBanners", () => {
  it("ничего не показывает, если сеть есть и обновлений нет", () => {
    const { container } = render(<PwaBanners />);
    expect(container).toBeEmptyDOMElement();
  });

  it("показывает баннер офлайн и скрывает его при возврате сети", () => {
    render(<PwaBanners />);
    onLine.mockReturnValue(false);
    act(() => void window.dispatchEvent(new Event("offline")));
    expect(screen.getByText(/Нет соединения/)).toBeInTheDocument();

    onLine.mockReturnValue(true);
    act(() => void window.dispatchEvent(new Event("online")));
    expect(screen.queryByText(/Нет соединения/)).not.toBeInTheDocument();
  });

  it("показывает баннер новой версии без автоматической перезагрузки", () => {
    render(<PwaBanners />);
    act(() => pwaMock.set({ needRefresh: true }));
    expect(screen.getByText("Доступна новая версия")).toBeInTheDocument();
    expect(updateServiceWorker).not.toHaveBeenCalled();
  });

  it("кнопка «Обновить» активирует новую версию", async () => {
    render(<PwaBanners />);
    act(() => pwaMock.set({ needRefresh: true }));
    await userEvent.click(screen.getByRole("button", { name: "Обновить" }));
    expect(updateServiceWorker).toHaveBeenCalledWith(true);
  });
});
