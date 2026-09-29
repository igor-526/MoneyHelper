import { Button, Flex, Segmented, Spin, Typography } from "antd";
import { useState } from "react";
import { EmptyState, useIsMobile } from "@/shared/ui";
import type { Category, CategoryType } from "./Category";
import { CategoryCard } from "./CategoryCard";
import { CategoryForm } from "./CategoryForm";
import { useCategories } from "./useCategories";

type FilterValue = "all" | CategoryType;

interface FormState {
  open: boolean;
  category?: Category;
}

const FILTER_OPTIONS: { label: string; value: FilterValue }[] = [
  { label: "Все", value: "all" },
  { label: "Доход", value: "income" },
  { label: "Расход", value: "expense" },
];

export function CategoriesPage() {
  const [filter, setFilter] = useState<FilterValue>("all");
  const categoriesQuery = useCategories(filter === "all" ? undefined : filter);
  const isMobile = useIsMobile();
  const [formState, setFormState] = useState<FormState>({ open: false });

  const openCreate = () => setFormState({ open: true, category: undefined });
  const openEdit = (category: Category) => setFormState({ open: true, category });
  const closeForm = () => setFormState({ open: false });

  const categories = categoriesQuery.data ?? [];

  return (
    <Flex vertical gap={16}>
      <Typography.Title level={3} style={{ margin: 0 }}>
        Категории
      </Typography.Title>
      <Segmented
        aria-label="Фильтр по типу"
        options={FILTER_OPTIONS}
        value={filter}
        onChange={(value) => setFilter(value as FilterValue)}
      />
      {categoriesQuery.isPending ? (
        <Spin />
      ) : categories.length === 0 ? (
        <EmptyState
          icon="coins"
          title="Категорий пока нет"
          action={{ label: "Создать категорию", onClick: openCreate }}
        />
      ) : (
        <>
          <Button
            type="primary"
            block={isMobile}
            onClick={openCreate}
            style={{ alignSelf: "flex-start" }}
          >
            Создать категорию
          </Button>
          <Flex vertical gap={12}>
            {categories.map((category) => (
              <CategoryCard key={category.id} category={category} onEdit={openEdit} />
            ))}
          </Flex>
        </>
      )}
      <CategoryForm
        open={formState.open}
        category={formState.category}
        defaultType={filter === "all" ? undefined : filter}
        onClose={closeForm}
      />
    </Flex>
  );
}
