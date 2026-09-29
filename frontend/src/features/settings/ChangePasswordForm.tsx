import { Button, Form, Input } from "antd";
import { applyFieldErrors, resolveErrorMessage, toApiError } from "@/shared/errors";
import { useToast } from "@/shared/ui";
import { useChangePassword } from "./useChangePassword";

interface ChangePasswordFormValues {
  current_password: string;
  new_password: string;
}

const KNOWN_FIELDS = ["current_password", "new_password"] as const;

export function ChangePasswordForm() {
  const [form] = Form.useForm<ChangePasswordFormValues>();
  const changePassword = useChangePassword();
  const toast = useToast();

  const handleSubmit = (values: ChangePasswordFormValues) => {
    changePassword.mutate(values, {
      onSuccess: () => {
        toast.success("Пароль изменён");
        form.resetFields();
      },
      onError: (submitError) => {
        const apiError = toApiError(submitError);

        if (apiError.kind === "validation") {
          const { byField, toastMessage } = applyFieldErrors(apiError, KNOWN_FIELDS);
          for (const [name, errors] of Object.entries(byField)) {
            form.setFields([{ name: name as keyof ChangePasswordFormValues, errors }]);
          }
          toast.error(toastMessage);
          return;
        }
        if (apiError.kind === "unauthorized") {
          form.setFields([{ name: "current_password", errors: ["Текущий пароль указан неверно"] }]);
          return;
        }
        toast.error(resolveErrorMessage(apiError));
      },
    });
  };

  return (
    <Form form={form} layout="vertical" onFinish={handleSubmit} disabled={changePassword.isPending}>
      <Form.Item
        name="current_password"
        label="Текущий пароль"
        rules={[{ required: true, message: "Введите текущий пароль" }]}
      >
        <Input.Password autoComplete="current-password" />
      </Form.Item>
      <Form.Item
        name="new_password"
        label="Новый пароль"
        extra="Не менее 8 символов"
        rules={[{ required: true, min: 8, message: "Пароль должен быть не короче 8 символов" }]}
      >
        <Input.Password autoComplete="new-password" />
      </Form.Item>
      <Form.Item style={{ marginBottom: 0 }}>
        <Button type="primary" htmlType="submit" loading={changePassword.isPending}>
          Сменить пароль
        </Button>
      </Form.Item>
    </Form>
  );
}
