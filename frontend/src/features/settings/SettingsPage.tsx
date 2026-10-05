import { Button, Card, Flex, Typography } from "antd";
import { Link } from "react-router-dom";
import { WorkspacesSection } from "@/features/workspaces/WorkspacesSection";
import { ChangePasswordForm } from "./ChangePasswordForm";
import { InstallSection } from "./InstallSection";
import { LogoutButton } from "./LogoutButton";
import { ThemeSwitch } from "./ThemeSwitch";

export function SettingsPage() {
  return (
    <Flex vertical gap={16}>
      <Typography.Title level={3} style={{ margin: 0 }}>
        Настройки
      </Typography.Title>
      <Card title="Тема оформления">
        <ThemeSwitch />
      </Card>
      <Card title="Воркспейсы">
        <WorkspacesSection />
      </Card>
      <Card title="Категории">
        <Link to="/categories">
          <Button type="primary">Открыть</Button>
        </Link>
      </Card>
      <Card title="Смена пароля">
        <ChangePasswordForm />
      </Card>
      <Card title="Аккаунт">
        <LogoutButton />
      </Card>
      <Card title="Приложение">
        <Flex vertical gap={12}>
          <InstallSection />
          <Typography.Text type="secondary">Версия {__APP_VERSION__}</Typography.Text>
        </Flex>
      </Card>
    </Flex>
  );
}
