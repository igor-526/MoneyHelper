import { Button, Flex, Popconfirm, Tag, Typography } from "antd";
import { useState } from "react";
import { useCurrentWorkspaceId } from "./WorkspaceContext";
import { useWorkspaceActions } from "./WorkspaceActionsContext";
import { WorkspaceForm } from "./WorkspaceForm";
import type { Workspace } from "./Workspace";
import { useDeleteWorkspace } from "./useDeleteWorkspace";
import { useWorkspaces } from "./useWorkspaces";

interface FormState {
  open: boolean;
  workspace?: Workspace;
}

/** Строка одного воркспейса: переключение/переименование/удаление. Сама владеет удалением (образец `WalletCard`). */
function WorkspaceRow({
  workspace,
  isCurrent,
  onEdit,
}: {
  workspace: Workspace;
  isCurrent: boolean;
  onEdit: (workspace: Workspace) => void;
}) {
  const { switchWorkspace } = useWorkspaceActions();
  const deleteWorkspace = useDeleteWorkspace();

  return (
    <Flex align="center" gap={8} wrap>
      <Typography.Text strong={isCurrent}>{workspace.name}</Typography.Text>
      {isCurrent ? <Tag color="blue">текущий</Tag> : null}
      <Flex gap={8} style={{ marginLeft: "auto" }}>
        {isCurrent ? null : (
          <Button size="small" onClick={() => switchWorkspace(workspace.id)}>
            Переключить
          </Button>
        )}
        <Button size="small" onClick={() => onEdit(workspace)}>
          Переименовать
        </Button>
        <Popconfirm
          title={`Удалить воркспейс «${workspace.name}»? Все его кошельки, категории и операции будут удалены.`}
          okText="Удалить"
          okType="danger"
          cancelText="Отмена"
          onConfirm={() => deleteWorkspace.mutate(workspace.id)}
        >
          <Button size="small" danger loading={deleteWorkspace.isPending}>
            Удалить
          </Button>
        </Popconfirm>
      </Flex>
    </Flex>
  );
}

/** Секция управления воркспейсами в «Настройках» (design.md, раздел 6). */
export function WorkspacesSection() {
  const workspacesQuery = useWorkspaces();
  const currentWorkspaceId = useCurrentWorkspaceId();
  const [formState, setFormState] = useState<FormState>({ open: false });

  const openCreate = () => setFormState({ open: true, workspace: undefined });
  const openEdit = (workspace: Workspace) => setFormState({ open: true, workspace });
  const closeForm = () => setFormState({ open: false });

  const workspaces = workspacesQuery.data ?? [];

  return (
    <Flex vertical gap={12}>
      <Flex vertical gap={8}>
        {workspaces.map((workspace) => (
          <WorkspaceRow
            key={workspace.id}
            workspace={workspace}
            isCurrent={workspace.id === currentWorkspaceId}
            onEdit={openEdit}
          />
        ))}
      </Flex>
      <Button onClick={openCreate} style={{ alignSelf: "flex-start" }}>
        Создать воркспейс
      </Button>
      <WorkspaceForm open={formState.open} workspace={formState.workspace} onClose={closeForm} />
    </Flex>
  );
}
