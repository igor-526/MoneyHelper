import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { ToastProvider } from "@/shared/ui";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import { RequireWorkspace } from "./RequireWorkspace";
import { useCurrentWorkspaceId } from "./WorkspaceContext";
import { workspaceStorage } from "./workspaceStorage";

function workspacesPage(items: unknown[]) {
  return { items, total: items.length, limit: 100, offset: 0 };
}

const WORKSPACES = [
  { id: "1", name: "Личное", created_at: "2026-01-01T00:00:00Z", updated_at: null },
  { id: "2", name: "Поездка в Китай", created_at: "2026-01-02T00:00:00Z", updated_at: null },
];

/** Пробный потребитель контекста — печатает текущий `workspace_id`. */
function Probe() {
  return <span>workspace: {useCurrentWorkspaceId()}</span>;
}

function setup(handler: FakeHandler) {
  const api = new FakeApiClient(handler);
  const toast = createToastSpy();
  const client = createQueryClient(toast);
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>
      <ApiClientProvider client={api}>
        <ToastProvider>{children}</ToastProvider>
      </ApiClientProvider>
    </QueryClientProvider>
  );
  return { api, wrapper };
}

describe("RequireWorkspace", () => {
  it("пустой список — EmptyState с формой создания; успешное создание рендерит children", async () => {
    const created = {
      id: "new",
      name: "Первый воркспейс",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: null,
    };
    let workspaces: unknown[] = [];
    const { api, wrapper } = setup((request) => {
      if (request.method === "GET") return workspacesPage(workspaces);
      if (request.method === "POST") {
        workspaces = [created];
        return created;
      }
      throw new Error(`unexpected request: ${request.method} ${request.path}`);
    });

    render(
      <RequireWorkspace>
        <Probe />
      </RequireWorkspace>,
      { wrapper },
    );

    expect(await screen.findByText("Воркспейсов пока нет")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Создать воркспейс" }));
    await userEvent.type(screen.getByLabelText("Название"), "Первый воркспейс");
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));

    expect(await screen.findByText("workspace: new")).toBeInTheDocument();
    expect(api.requests.some((r) => r.method === "POST" && r.path === "/api/workspaces")).toBe(
      true,
    );
  });

  it("сохранённый id отсутствует среди воркспейсов — список выбора; клик переключает", async () => {
    const { wrapper } = setup(() => workspacesPage(WORKSPACES));

    render(
      <RequireWorkspace>
        <Probe />
      </RequireWorkspace>,
      { wrapper },
    );

    expect(await screen.findByText("Выберите воркспейс")).toBeInTheDocument();
    expect(screen.getByText("Личное")).toBeInTheDocument();
    expect(screen.getByText("Поездка в Китай")).toBeInTheDocument();

    await userEvent.click(screen.getByText("Поездка в Китай"));

    expect(await screen.findByText("workspace: 2")).toBeInTheDocument();
    expect(workspaceStorage.get()).toBe("2");
  });

  it("единственный воркспейс без сохранённого id выбирается автоматически (без персистенции — derived)", async () => {
    const { wrapper } = setup(() => workspacesPage([WORKSPACES[0]]));

    render(
      <RequireWorkspace>
        <Probe />
      </RequireWorkspace>,
      { wrapper },
    );

    expect(await screen.findByText("workspace: 1")).toBeInTheDocument();
    expect(workspaceStorage.get()).toBeNull();
  });

  it("валидный сохранённый id сразу рендерит children с контекстом", async () => {
    workspaceStorage.set("1");
    const { wrapper } = setup(() => workspacesPage(WORKSPACES));

    render(
      <RequireWorkspace>
        <Probe />
      </RequireWorkspace>,
      { wrapper },
    );

    await waitFor(() => expect(screen.getByText("workspace: 1")).toBeInTheDocument());
  });
});
