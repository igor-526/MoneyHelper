import { Button, Drawer, Form, Input, Modal } from "antd";
import { useEffect } from "react";
import { applyFieldErrors, resolveErrorMessage, toApiError } from "@/shared/errors";
import { useIsMobile, useToast } from "@/shared/ui";
import type { Workspace, WorkspaceFormValues } from "./Workspace";
import { useCreateWorkspace } from "./useCreateWorkspace";
import { useRenameWorkspace } from "./useRenameWorkspace";

export interface WorkspaceFormProps {
  open: boolean;
  onClose: () => void;
  /** `undefined` — форма создания; заданный `Workspace` — форма переименования. */
  workspace?: Workspace;
  /** Вызывается после успешного создания/переименования (например, чтобы сразу переключиться на созданный). */
  onSuccess?: (workspace: Workspace) => void;
}

const KNOWN_FIELDS = ["name"] as const;

/** Один компонент для создания и переименования воркспейса (design.md, раздел 6). */
export function WorkspaceForm({ open, onClose, workspace, onSuccess }: WorkspaceFormProps) {
  const [form] = Form.useForm<WorkspaceFormValues>();
  const isMobile = useIsMobile();
  const toast = useToast();
  const createWorkspace = useCreateWorkspace();
  const renameWorkspace = useRenameWorkspace();
  const mutation = workspace ? renameWorkspace : createWorkspace;

  useEffect(() => {
    if (!open) return;
    if (workspace) {
      form.setFieldsValue({ name: workspace.name });
    } else {
      form.resetFields();
    }
  }, [open, workspace, form]);

  const handleSubmit = (values: WorkspaceFormValues) => {
    const onError = (submitError: unknown) => {
      const apiError = toApiError(submitError);

      if (apiError.kind === "validation") {
        const { byField, toastMessage } = applyFieldErrors(apiError, KNOWN_FIELDS);
        for (const [name, errors] of Object.entries(byField)) {
          form.setFields([{ name: name as keyof WorkspaceFormValues, errors }]);
        }
        toast.error(toastMessage);
        return;
      }
      toast.error(resolveErrorMessage(apiError));
    };

    const handleSuccess = (created: Workspace) => {
      toast.success(workspace ? "Воркспейс переименован" : "Воркспейс создан");
      onSuccess?.(created);
      onClose();
    };

    if (workspace) {
      renameWorkspace.mutate({ id: workspace.id, values }, { onSuccess: handleSuccess, onError });
    } else {
      createWorkspace.mutate(values, { onSuccess: handleSuccess, onError });
    }
  };

  const title = workspace ? "Переименовать воркспейс" : "Создать воркспейс";
  const content = (
    <Form form={form} layout="vertical" onFinish={handleSubmit} disabled={mutation.isPending}>
      <Form.Item
        name="name"
        label="Название"
        rules={[{ required: true, message: "Введите название" }]}
      >
        <Input maxLength={100} />
      </Form.Item>
      <Form.Item style={{ marginBottom: 0 }}>
        <Button type="primary" htmlType="submit" block loading={mutation.isPending}>
          {workspace ? "Сохранить" : "Создать"}
        </Button>
      </Form.Item>
    </Form>
  );

  return isMobile ? (
    <Drawer placement="bottom" height="40vh" open={open} onClose={onClose} title={title}>
      {content}
    </Drawer>
  ) : (
    <Modal open={open} onCancel={onClose} footer={null} width={480} title={title} destroyOnClose>
      {content}
    </Modal>
  );
}
