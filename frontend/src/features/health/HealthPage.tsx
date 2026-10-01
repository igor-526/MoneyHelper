import { Button, Card, Flex, Spin, Tag, Typography } from "antd";
import { Icon } from "@/shared/ui/Icon";
import { WorkspacesSection } from "@/features/workspaces/WorkspacesSection";
import { useHealth } from "./useHealth";

/** Главная: статус backend и переключение/управление воркспейсами (поездками). */
export function HealthPage() {
  const { isPending, isError, isFetching, refetch } = useHealth();

  return (
    <Flex vertical gap={16}>
      <Card>
        <Typography.Title level={3} style={{ marginTop: 0 }}>
          MoneyHelper
        </Typography.Title>
        <Typography.Paragraph type="secondary">Учёт личных финансов</Typography.Paragraph>

        {isPending && (
          <Spin description="Проверяем backend…">
            <div style={{ minHeight: 44 }} />
          </Spin>
        )}
        {!isPending && !isError && (
          <Tag color="success" icon={<Icon name="wallet" size={14} />}>
            Backend доступен
          </Tag>
        )}
        {isError && (
          <>
            <Tag color="error">Backend недоступен</Tag>
            <Button
              block
              type="primary"
              loading={isFetching}
              onClick={() => void refetch()}
              style={{ marginTop: 16 }}
            >
              Повторить
            </Button>
          </>
        )}
      </Card>
      <Card title="Воркспейсы">
        <WorkspacesSection />
      </Card>
    </Flex>
  );
}
