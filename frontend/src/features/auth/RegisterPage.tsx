import { Alert, Button, Card, Form, Input, Typography } from "antd";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { applyFieldErrors, resolveErrorMessage, toApiError } from "@/shared/errors";
import { useToast } from "@/shared/ui";
import { useRegister } from "./useRegister";

interface RegisterFormValues {
  email: string;
  password: string;
}

const KNOWN_FIELDS = ["email", "password"] as const;

export function RegisterPage() {
  const [form] = Form.useForm<RegisterFormValues>();
  const register = useRegister();
  const toast = useToast();
  const navigate = useNavigate();
  const [disabled, setDisabled] = useState(false);

  const handleSubmit = (values: RegisterFormValues) => {
    register.mutate(values, {
      onSuccess: () => {
        toast.success("Регистрация выполнена, войдите");
        navigate("/login", { replace: true });
      },
      onError: (submitError) => {
        const apiError = toApiError(submitError);

        if (apiError.kind === "validation") {
          const { byField, toastMessage } = applyFieldErrors(apiError, KNOWN_FIELDS);
          for (const [name, errors] of Object.entries(byField)) {
            form.setFields([{ name: name as keyof RegisterFormValues, errors }]);
          }
          toast.error(toastMessage);
          return;
        }
        if (apiError.kind === "conflict") {
          form.setFields([{ name: "email", errors: ["Такой email уже зарегистрирован"] }]);
          return;
        }
        if (apiError.kind === "forbidden") {
          setDisabled(true);
          return;
        }
        toast.error(resolveErrorMessage(apiError));
      },
    });
  };

  if (disabled) {
    return (
      <div style={{ maxWidth: 360, margin: "0 auto", padding: "24px 16px" }}>
        <Card>
          <Alert type="warning" showIcon message="Регистрация недоступна" role="alert" />
          <Typography.Paragraph style={{ marginTop: 16, marginBottom: 0 }}>
            Уже есть аккаунт? <Link to="/login">Войти</Link>
          </Typography.Paragraph>
        </Card>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 360, margin: "0 auto", padding: "24px 16px" }}>
      <Card>
        <Typography.Title level={3} style={{ marginTop: 0 }}>
          Регистрация
        </Typography.Title>
        <Form form={form} layout="vertical" onFinish={handleSubmit} disabled={register.isPending}>
          <Form.Item
            name="email"
            label="Email"
            rules={[{ required: true, type: "email", message: "Введите корректный email" }]}
          >
            <Input type="email" inputMode="email" autoComplete="username" />
          </Form.Item>
          <Form.Item
            name="password"
            label="Пароль"
            extra="Не менее 8 символов"
            rules={[{ required: true, min: 8, message: "Пароль должен быть не короче 8 символов" }]}
          >
            <Input.Password autoComplete="new-password" />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0 }}>
            <Button type="primary" htmlType="submit" block loading={register.isPending}>
              Зарегистрироваться
            </Button>
          </Form.Item>
        </Form>
        <Typography.Paragraph style={{ marginTop: 16, marginBottom: 0 }}>
          Уже есть аккаунт? <Link to="/login">Войти</Link>
        </Typography.Paragraph>
      </Card>
    </div>
  );
}
