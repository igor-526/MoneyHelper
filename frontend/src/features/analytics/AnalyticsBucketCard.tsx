import { Card, Flex, Typography } from "antd";
import type { AnalyticsBucket } from "./Analytics";

export interface AnalyticsBucketCardProps {
  label: string;
  bucket: AnalyticsBucket;
}

/** Единый простой рендер независимо от `group_by` — без иконки/тега типа (в отличие от `TransactionCard`). */
export function AnalyticsBucketCard({ label, bucket }: AnalyticsBucketCardProps) {
  return (
    <Card>
      <Flex vertical gap={8}>
        <Typography.Text strong>{label}</Typography.Text>
        <Flex gap={16}>
          <Typography.Text type="success">Доход: {bucket.income}</Typography.Text>
          <Typography.Text type="danger">Расход: {bucket.expense}</Typography.Text>
        </Flex>
      </Flex>
    </Card>
  );
}
