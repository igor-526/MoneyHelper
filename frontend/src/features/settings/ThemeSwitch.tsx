import { Segmented } from "antd";
import { Icon } from "@/shared/ui/Icon";
import { useIsMobile } from "@/shared/ui/useIsMobile";
import { useThemeMode } from "@/shared/ui/theme/ThemeProvider";
import type { ThemeMode } from "@/shared/ui/theme/mode";

const OPTIONS: { value: ThemeMode; label: string; icon: string }[] = [
  { value: "light", label: "Светлая", icon: "sun" },
  { value: "dark", label: "Тёмная", icon: "moon" },
  { value: "system", label: "Как в системе", icon: "smartphone" },
];

export function ThemeSwitch() {
  const { mode, setMode } = useThemeMode();
  // На узком экране три подписи в ряд не помещаются, поэтому варианты идут столбиком
  const isMobile = useIsMobile();
  return (
    <Segmented<ThemeMode>
      block
      vertical={isMobile}
      size="large"
      aria-label="Тема оформления"
      value={mode}
      onChange={setMode}
      options={OPTIONS.map(({ value, label, icon }) => ({
        value,
        label: (
          <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
            <Icon name={icon} size={16} />
            {label}
          </span>
        ),
      }))}
    />
  );
}
