import { Button, Flex, Select } from "antd";
import { useState } from "react";
import { useCategories } from "@/features/categories/useCategories";
import { useWallets } from "@/features/wallets/useWallets";
import { FiltersDialog } from "@/shared/ui";
import { EMPTY_SPENDING_FILTERS, type SpendingFilters } from "./spendingFilters";

const ALL = "all";

export interface SpendingFiltersPopupProps {
  open: boolean;
  onClose: () => void;
  value: SpendingFilters;
  onApply: (value: SpendingFilters) => void;
}

type FiltersFormProps = Omit<SpendingFiltersPopupProps, "open">;

/** Черновик фильтров: форма создаётся заново при каждом открытии окна, поэтому стартует с применённых значений. */
function FiltersForm({ onClose, value, onApply }: FiltersFormProps) {
  const [draft, setDraft] = useState(value);
  const { data: wallets = [] } = useWallets();
  const { data: categories = [] } = useCategories("expense");

  const apply = (next: SpendingFilters) => {
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
      <Select
        aria-label="Категория"
        value={draft.categoryId ?? ALL}
        options={[
          { value: ALL, label: "Все категории" },
          ...categories.map((category) => ({ value: category.id, label: category.name })),
        ]}
        onChange={(next) => setDraft({ ...draft, categoryId: next === ALL ? undefined : next })}
      />
      <Flex gap={8}>
        <Button block onClick={() => apply(EMPTY_SPENDING_FILTERS)}>
          Сбросить
        </Button>
        <Button type="primary" block onClick={() => apply(draft)}>
          Применить
        </Button>
      </Flex>
    </Flex>
  );
}

/** Окно фильтров режима «Трата»: изменения применяются только кнопкой «Применить». */
export function SpendingFiltersPopup({ open, ...formProps }: SpendingFiltersPopupProps) {
  return (
    <FiltersDialog open={open} onClose={formProps.onClose}>
      <FiltersForm {...formProps} />
    </FiltersDialog>
  );
}
