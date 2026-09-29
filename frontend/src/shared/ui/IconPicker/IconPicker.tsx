import { Button, Drawer, Modal, theme as antdTheme } from "antd";
import { useState } from "react";
import { Icon } from "../Icon";
import { BUSINESS_ICON_NAMES } from "../icons";
import { useIsMobile } from "../useIsMobile";

export interface IconPickerProps {
  value: string | undefined;
  onChange: (name: string) => void;
  /** Подпись для скринридера триггера, по умолчанию «Иконка». */
  label?: string;
}

const GRID_STYLE = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fill, minmax(44px, 1fr))",
  gap: 8,
};

/** Выбор одной иконки из закрытого списка `BUSINESS_ICON_NAMES`; контейнер — `Drawer`/`Modal` по `useIsMobile`. */
export function IconPicker({ value, onChange, label = "Иконка" }: IconPickerProps) {
  const isMobile = useIsMobile();
  const { token } = antdTheme.useToken();
  const [open, setOpen] = useState(false);

  const handleSelect = (name: string) => {
    onChange(name);
    setOpen(false);
  };

  const list = (
    <div style={GRID_STYLE} role="listbox" aria-label={label}>
      {BUSINESS_ICON_NAMES.map((name) => {
        const selected = name === value;
        return (
          <Button
            key={name}
            role="option"
            aria-selected={selected}
            aria-label={name}
            onClick={() => handleSelect(name)}
            style={{
              width: 44,
              height: 44,
              padding: 0,
              color: selected ? token.colorPrimary : undefined,
              backgroundColor: selected ? token.colorPrimaryBg : undefined,
              borderColor: selected ? token.colorPrimary : undefined,
            }}
          >
            <Icon name={name} />
          </Button>
        );
      })}
    </div>
  );

  return (
    <>
      <Button block onClick={() => setOpen(true)}>
        {value ? <Icon name={value} label={label} /> : "Иконка не выбрана"}
      </Button>
      {isMobile ? (
        <Drawer
          placement="bottom"
          height="80vh"
          open={open}
          onClose={() => setOpen(false)}
          title={label}
        >
          {list}
        </Drawer>
      ) : (
        <Modal open={open} onCancel={() => setOpen(false)} footer={null} width={960} title={label}>
          {list}
        </Modal>
      )}
    </>
  );
}
