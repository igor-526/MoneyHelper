import { Card, Flex, Typography } from "antd";
import { InstallSection } from "./InstallSection";
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
      <Card title="Приложение">
        <Flex vertical gap={12}>
          <InstallSection />
          <Typography.Text type="secondary">Версия {__APP_VERSION__}</Typography.Text>
        </Flex>
      </Card>
    </Flex>
  );
}
