import { Button, Popconfirm } from "antd";

export interface ConfirmDeleteButtonProps {
  title: string;
  loading: boolean;
  onConfirm: () => void;
}

/** Кнопка «Удалить» с подтверждением; само удаление выполняет вызывающий. */
export function ConfirmDeleteButton({ title, loading, onConfirm }: ConfirmDeleteButtonProps) {
  return (
    <Popconfirm
      title={title}
      okText="Удалить"
      okType="danger"
      cancelText="Отмена"
      onConfirm={onConfirm}
    >
      <Button danger block loading={loading}>
        Удалить
      </Button>
    </Popconfirm>
  );
}
