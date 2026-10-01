import { Button, Card, Flex, Spin, Typography } from "antd";
import { type ReactNode, useState } from "react";
import { EmptyState } from "@/shared/ui";
import { WorkspaceActionsContext } from "./WorkspaceActionsContext";
import { WorkspaceContext } from "./WorkspaceContext";
import { WorkspaceForm } from "./WorkspaceForm";
import type { Workspace } from "./Workspace";
import { useWorkspaces } from "./useWorkspaces";
import { workspaceStorage } from "./workspaceStorage";

/** Центрирование на весь экран — тот же приём, что `FullscreenSpinner` в `RequireAuth`, здесь без AppLayout. */
function FullscreenCentered({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        display: "flex",
        minHeight: "100dvh",
        alignItems: "center",
        justifyContent: "center",
        padding: 16,
      }}
    >
      <div style={{ width: "100%", maxWidth: 480 }}>{children}</div>
    </div>
  );
}

/**
 * Оборачивает защищённые маршруты между `RequireAuth` и `AppLayout` (design.md, Decision 2). Три состояния:
 * загрузка списка воркспейсов, пустой список (создание первого) и отсутствующий/невалидный сохранённый
 * `workspace_id` (выбор одного из существующих). Иначе — предоставляет `WorkspaceContext`/`WorkspaceActionsContext`.
 */
export function RequireWorkspace({ children }: { children: ReactNode }) {
  const workspacesQuery = useWorkspaces();
  const [workspaceId, setWorkspaceId] = useState<string | null>(() => workspaceStorage.get());
  const [formOpen, setFormOpen] = useState(false);
  const workspaces = workspacesQuery.data ?? [];

  const switchWorkspace = (id: string) => {
    workspaceStorage.set(id);
    setWorkspaceId(id);
  };

  if (workspacesQuery.isPending) {
    return (
      <FullscreenCentered>
        <Flex justify="center">
          <Spin size="large" />
        </Flex>
      </FullscreenCentered>
    );
  }

  if (workspaces.length === 0) {
    return (
      <FullscreenCentered>
        <EmptyState
          icon="briefcase"
          title="Воркспейсов пока нет"
          description="Создайте воркспейс, чтобы вести кошельки, категории и операции — например, отдельно по поездке."
          action={{ label: "Создать воркспейс", onClick: () => setFormOpen(true) }}
        />
        <WorkspaceForm
          open={formOpen}
          onClose={() => setFormOpen(false)}
          onSuccess={(created: Workspace) => switchWorkspace(created.id)}
        />
      </FullscreenCentered>
    );
  }

  // Единственный воркспейс и ничего (валидного) не сохранено — выбирать нечего, выбираем сами; ничего не
  // персистится в `workspaceStorage` для этого случая — он и так детерминированно выводится заново на каждом
  // рендере, пока воркспейс остаётся единственным (derived value, не эффект — design.md, уточнение к Decision 2).
  const storedWorkspace = workspaces.find((workspace) => workspace.id === workspaceId);
  const currentWorkspace = storedWorkspace ?? (workspaces.length === 1 ? workspaces[0] : undefined);

  if (!currentWorkspace) {
    return (
      <FullscreenCentered>
        <Flex vertical gap={16}>
          <Typography.Title level={4} style={{ margin: 0 }}>
            Выберите воркспейс
          </Typography.Title>
          <Card styles={{ body: { padding: 0 } }}>
            <Flex vertical>
              {workspaces.map((workspace) => (
                <Button
                  key={workspace.id}
                  type="text"
                  block
                  style={{ height: 48, justifyContent: "flex-start" }}
                  onClick={() => switchWorkspace(workspace.id)}
                >
                  {workspace.name}
                </Button>
              ))}
            </Flex>
          </Card>
        </Flex>
      </FullscreenCentered>
    );
  }

  return (
    <WorkspaceActionsContext.Provider value={{ switchWorkspace }}>
      <WorkspaceContext.Provider value={currentWorkspace.id}>{children}</WorkspaceContext.Provider>
    </WorkspaceActionsContext.Provider>
  );
}
