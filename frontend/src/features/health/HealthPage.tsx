import { Button, Card, Spin, Tag, Typography } from "antd";
import { Icon } from "@/shared/ui/Icon";
import { useHealth } from "./useHealth";

/** Страница-заглушка: показывает, доступен ли backend (`GET /health`). */
export function HealthPage() {
  const { isPending, isError, isFetching, refetch } = useHealth();

  return (
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
  );
}
