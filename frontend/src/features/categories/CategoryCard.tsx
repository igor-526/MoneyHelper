import { Button, Card, Flex, Popconfirm, Tag, Typography } from "antd";
import { Icon } from "@/shared/ui";
import type { Category, CategoryType } from "./Category";
import { useDeleteCategory } from "./useDeleteCategory";

export interface CategoryCardProps {
  category: Category;
  onEdit: (category: Category) => void;
}

const TYPE_TAG: Record<CategoryType, { label: string; color: "success" | "error" }> = {
  income: { label: "Доход", color: "success" },
  expense: { label: "Расход", color: "error" },
};

/** Сама владеет удалением (по образцу `WalletCard`) — не получает мутацию от родителя. */
export function CategoryCard({ category, onEdit }: CategoryCardProps) {
  const deleteCategory = useDeleteCategory();
  const typeTag = TYPE_TAG[category.type];

  return (
    <Card>
      <Flex vertical gap={12}>
        <Flex align="center" gap={8}>
          <Icon name={category.icon} />
          <Typography.Text strong>{category.name}</Typography.Text>
          <Tag color={typeTag.color}>{typeTag.label}</Tag>
        </Flex>
        <Flex gap={8}>
          <Button onClick={() => onEdit(category)}>Редактировать</Button>
          <Popconfirm
            title={`Удалить категорию «${category.name}»?`}
            okText="Удалить"
            okType="danger"
            cancelText="Отмена"
            onConfirm={() => deleteCategory.mutate(category.id)}
          >
            <Button danger loading={deleteCategory.isPending}>
              Удалить
            </Button>
          </Popconfirm>
        </Flex>
      </Flex>
    </Card>
  );
}
