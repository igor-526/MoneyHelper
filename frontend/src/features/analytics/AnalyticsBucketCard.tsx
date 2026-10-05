import { Card, Flex, Typography } from "antd";
import { formatAmount } from "@/shared/ui";
import type { AnalyticsBucket } from "./Analytics";

export interface AnalyticsBucketCardProps {
  label: string;
  bucket: AnalyticsBucket;
  /** Код валюты отображения; `undefined`, пока справочник валют не загружен. */
  currencyCode: string | undefined;
}

/** Единый простой рендер независимо от `group_by` — без иконки/тега типа (в отличие от `TransactionCard`). */
export function AnalyticsBucketCard({ label, bucket, currencyCode }: AnalyticsBucketCardProps) {
  return (
    <Card>
      <Flex vertical gap={8}>
        <Typography.Text strong>{label}</Typography.Text>
        <Flex gap={16}>
          <Typography.Text type="success">
            Доход: {formatAmount(bucket.income)} {currencyCode}
          </Typography.Text>
          <Typography.Text type="danger">
            Расход: {formatAmount(bucket.expense)} {currencyCode}
          </Typography.Text>
        </Flex>
      </Flex>
    </Card>
  );
}
