import { Drawer, Modal } from "antd";
import type { ReactNode } from "react";
import { useIsMobile } from "../useIsMobile";

export interface FiltersDialogProps {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
}

/** Оболочка окна фильтров: нижний Drawer на телефоне, Modal на широком экране. Содержимое создаётся заново при открытии. */
export function FiltersDialog({ open, onClose, children }: FiltersDialogProps) {
  const isMobile = useIsMobile();

  return isMobile ? (
    <Drawer
      placement="bottom"
      size="auto"
      open={open}
      onClose={onClose}
      title="Фильтры"
      destroyOnHidden
    >
      {children}
    </Drawer>
  ) : (
    <Modal open={open} onCancel={onClose} footer={null} width={480} title="Фильтры" destroyOnHidden>
      {children}
    </Modal>
  );
}
