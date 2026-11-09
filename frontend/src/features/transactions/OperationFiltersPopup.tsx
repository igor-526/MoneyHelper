import { FilterMultiSelect } from "@/shared/ui/FilterMultiSelect";
import { MobileDateRange } from "@/shared/ui/MobileDateRange";
import { Button, Flex } from "antd";
import { useState } from "react";
import type { CategoryType } from "@/features/categories/Category";
import { useCategories } from "@/features/categories/useCategories";
import { useWallets } from "@/features/wallets/useWallets";
import { FiltersDialog } from "@/shared/ui";
import { EMPTY_OPERATION_FILTERS, type OperationFiltersState } from "./operationFilters";

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
      <FilterMultiSelect
        label="Кошелёк"
        value={draft.walletIds}
        options={wallets.map((wallet) => ({ value: wallet.id, label: wallet.name }))}
        onChange={(walletIds) => setDraft({ ...draft, walletIds })}
      />
      {categoryType !== undefined ? (
        <FilterMultiSelect
          label="Категория"
          value={draft.categoryIds}
          options={categories.map((category) => ({ value: category.id, label: category.name }))}
          onChange={(categoryIds) => setDraft({ ...draft, categoryIds })}
        />
      ) : null}
      <MobileDateRange
        value={draft.dateRange}
        onChange={(dateRange) => setDraft({ ...draft, dateRange })}
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
