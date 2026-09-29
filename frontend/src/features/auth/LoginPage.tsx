import { Alert, Button, Card, Form, Input, Typography } from "antd";
import { Link } from "react-router-dom";
import { resolveErrorMessage, toApiError } from "@/shared/errors";
import { useToast } from "@/shared/ui";
import { useLogin } from "./useLogin";

interface LoginFormValues {
  email: string;
  password: string;
}

export function LoginPage() {
  const [form] = Form.useForm<LoginFormValues>();
  const login = useLogin();
  const toast = useToast();

  const error = login.error ? toApiError(login.error) : null;
  const inlineMessage =
    error?.kind === "unauthorized" ? (error.detail ?? "Неверный email или пароль") : null;

  const handleSubmit = (values: LoginFormValues) => {
    // Успех обновляет кэш сессии (см. useLogin) — переход «туда, куда шёл пользователь» выполняет
    // GuestOnly, реагируя на это же изменение: два редиректа на одно событие гонялись бы друг с другом.
    login.mutate(values, {
      onError: (submitError) => {
        const apiError = toApiError(submitError);
        if (apiError.kind === "unauthorized") {
          form.setFieldValue("password", "");
          return;
        }
        toast.error(resolveErrorMessage(apiError));
      },
    });
  };

  return (
    <div style={{ maxWidth: 360, margin: "0 auto", padding: "24px 16px" }}>
      <Card>
        <Typography.Title level={3} style={{ marginTop: 0 }}>
          Вход
        </Typography.Title>
        {inlineMessage && (
          <Alert
            type="error"
            showIcon
            message={inlineMessage}
            style={{ marginBottom: 16 }}
            role="alert"
          />
        )}
        <Form form={form} layout="vertical" onFinish={handleSubmit} disabled={login.isPending}>
          <Form.Item
            name="email"
            label="Email"
            rules={[{ required: true, message: "Введите email" }]}
          >
            <Input type="email" inputMode="email" autoComplete="username" />
          </Form.Item>
          <Form.Item
            name="password"
            label="Пароль"
            rules={[{ required: true, message: "Введите пароль" }]}
          >
            <Input.Password autoComplete="current-password" />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0 }}>
            <Button type="primary" htmlType="submit" block loading={login.isPending}>
              Войти
            </Button>
          </Form.Item>
        </Form>
        <Typography.Paragraph style={{ marginTop: 16, marginBottom: 0 }}>
          Нет аккаунта? <Link to="/register">Зарегистрироваться</Link>
        </Typography.Paragraph>
      </Card>
    </div>
  );
}
