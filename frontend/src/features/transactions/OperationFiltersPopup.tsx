import { Button, DatePicker, Flex, Select } from "antd";
import { useState } from "react";
import type { CategoryType } from "@/features/categories/Category";
import { useCategories } from "@/features/categories/useCategories";
import { useWallets } from "@/features/wallets/useWallets";
import { FiltersDialog } from "@/shared/ui";
import { EMPTY_OPERATION_FILTERS, type OperationFiltersState } from "./operationFilters";

const ALL = "all";

export interface OperationFiltersPopupProps {
  open: boolean;
  onClose: () => void;
  value: OperationFiltersState;
  /** `undefined` — у вкладки нет категорий, фильтр категории не показывается. */
  categoryType: CategoryType | undefined;
  onApply: (value: OperationFiltersState) => void;
}

type FiltersFormProps = Omit<OperationFiltersPopupProps, "open">;

/** Черновик фильтров: форма создаётся заново при каждом открытии окна, поэтому стартует с применённых значений. */
function FiltersForm({ onClose, value, categoryType, onApply }: FiltersFormProps) {
  const [draft, setDraft] = useState(value);
  const { data: wallets = [] } = useWallets();
  const { data: categories = [] } = useCategories(categoryType);

  const apply = (next: OperationFiltersState) => {
    onApply(next);
    onClose();
  };

  return (
    <Flex vertical gap={12}>
      <Select
        aria-label="Кошелёк"
        value={draft.walletId ?? ALL}
        options={[
          { value: ALL, label: "Все кошельки" },
          ...wallets.map((wallet) => ({ value: wallet.id, label: wallet.name })),
        ]}
        onChange={(next) => setDraft({ ...draft, walletId: next === ALL ? undefined : next })}
      />
      {categoryType !== undefined ? (
        <Select
          aria-label="Категория"
          value={draft.categoryId ?? ALL}
          options={[
            { value: ALL, label: "Все категории" },
            ...categories.map((category) => ({ value: category.id, label: category.name })),
          ]}
          onChange={(next) => setDraft({ ...draft, categoryId: next === ALL ? undefined : next })}
        />
      ) : null}
      <DatePicker.RangePicker
        aria-label="Диапазон дат"
        placeholder={["Дата от", "Дата до"]}
        value={draft.dateRange}
        onChange={(dates) =>
          setDraft({
            ...draft,
            dateRange: dates && dates[0] && dates[1] ? [dates[0], dates[1]] : null,
          })
        }
        allowClear
      />
      <Flex gap={8}>
        <Button block onClick={() => apply(EMPTY_OPERATION_FILTERS)}>
          Сбросить
        </Button>
        <Button type="primary" block onClick={() => apply(draft)}>
          Применить
        </Button>
      </Flex>
    </Flex>
  );
}

/** Окно фильтров вкладки: изменения применяются только кнопкой «Применить». */
export function OperationFiltersPopup({ open, ...formProps }: OperationFiltersPopupProps) {
  return (
    <FiltersDialog open={open} onClose={formProps.onClose}>
      <FiltersForm {...formProps} />
    </FiltersDialog>
  );
}
