import { Flex, Tabs, Typography } from "antd";
import { useSearchParams } from "react-router-dom";
import { findOperationKind, OPERATION_KINDS } from "./operationKinds";

const TAB_PARAM = "tab";

const TAB_ITEMS = OPERATION_KINDS.map((kind) => ({
  key: kind.key,
  label: kind.label,
  children: <kind.Panel />,
}));

export function TransactionsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const activeKey = findOperationKind(searchParams.get(TAB_PARAM)).key;

  return (
    <Flex vertical gap={16}>
      <Typography.Title level={3} style={{ margin: 0 }}>
        Операции
      </Typography.Title>
      <Tabs
        activeKey={activeKey}
        items={TAB_ITEMS}
        onChange={(key) => setSearchParams({ [TAB_PARAM]: key }, { replace: true })}
      />
    </Flex>
  );
}
