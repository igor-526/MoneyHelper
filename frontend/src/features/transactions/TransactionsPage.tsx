import { Badge, Button, Flex, Input, Tabs, Typography } from "antd";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Icon } from "@/shared/ui";
import { OperationFiltersPopup } from "./OperationFiltersPopup";
import {
  countActiveFilters,
  EMPTY_OPERATION_FILTERS,
  type OperationFiltersState,
} from "./operationFilters";
import { findOperationKind, OPERATION_KINDS } from "./operationKinds";

const TAB_PARAM = "tab";

export function TransactionsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const kind = findOperationKind(searchParams.get(TAB_PARAM));
  // Фильтры хранятся по вкладкам: при переключении вкладок фильтры каждой сохраняются.
  const [filtersByTab, setFiltersByTab] = useState<Record<string, OperationFiltersState>>({});
  const [filtersOpen, setFiltersOpen] = useState(false);

  const filtersOf = (key: string) => filtersByTab[key] ?? EMPTY_OPERATION_FILTERS;
  const activeCount = countActiveFilters(filtersOf(kind.key));

  const tabItems = OPERATION_KINDS.map((item) => ({
    key: item.key,
    label: item.label,
    children: <item.Panel filters={filtersOf(item.key)} />,
  }));

  return (
    <Flex vertical gap={16}>
      <Typography.Title level={3} style={{ margin: 0 }}>
        Операции
      </Typography.Title>
      <Flex gap={8} align="center">
        <Input
          aria-label="Поиск по описанию"
          placeholder="Поиск по описанию"
          maxLength={1000}
          allowClear
          value={filtersOf(kind.key).commentQuery ?? ""}
          onChange={(event) =>
            setFiltersByTab((prev) => ({
              ...prev,
              [kind.key]: { ...filtersOf(kind.key), commentQuery: event.target.value },
            }))
          }
        />
        <Badge count={activeCount} size="small">
          <Button
            aria-label="Фильтры"
            icon={<Icon name="funnel" />}
            onClick={() => setFiltersOpen(true)}
          />
        </Badge>
      </Flex>
      <Tabs
        activeKey={kind.key}
        items={tabItems}
        onChange={(key) => setSearchParams({ [TAB_PARAM]: key }, { replace: true })}
      />
      <OperationFiltersPopup
        open={filtersOpen}
        onClose={() => setFiltersOpen(false)}
        value={filtersOf(kind.key)}
        categoryType={kind.categoryType}
        onApply={(next) => setFiltersByTab((prev) => ({ ...prev, [kind.key]: next }))}
      />
    </Flex>
  );
}
