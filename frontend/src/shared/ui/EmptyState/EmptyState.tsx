import { Button, Typography } from "antd";
import { Icon } from "../Icon";
import { useIsMobile } from "../useIsMobile";

export interface EmptyStateProps {
  /** Имя иконки Lucide (kebab-case), как в БД. */
  icon: string;
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };
}

/** Пустое состояние списка: иконка + заголовок обязательны, без иллюстраций. */
export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  const isMobile = useIsMobile();

  return (
    <div style={{ textAlign: "center", padding: "32px 16px" }}>
      <Icon name={icon} size={32} />
      <Typography.Title level={5} style={{ marginTop: 16 }}>
        {title}
      </Typography.Title>
      {description ? <Typography.Text type="secondary">{description}</Typography.Text> : null}
      {action ? (
        <div style={{ marginTop: 16 }}>
          <Button type="primary" block={isMobile} onClick={action.onClick}>
            {action.label}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
