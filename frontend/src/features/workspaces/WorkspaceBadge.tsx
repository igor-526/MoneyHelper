import { Tag, theme } from "antd";
import { Link } from "react-router-dom";
import { Icon, useCurrencies } from "@/shared/ui";
import { useCurrentWorkspace } from "./useCurrentWorkspace";

/**
 * Индикатор текущего воркспейса в оболочке: название и код валюты, ссылка на «Настройки» (там он переключается).
 * `color` нужен на тёмной шапке, где цвет текста по умолчанию не контрастен.
 */
export function WorkspaceBadge({ color }: { color?: string }) {
  const { token } = theme.useToken();
  const workspace = useCurrentWorkspace();
  const { data: currencies } = useCurrencies();
  if (!workspace) return null;
  const currency = currencies?.find((item) => item.id === workspace.currency_id);

  return (
    <Link
      to="/settings"
      aria-label={`Текущий воркспейс: ${workspace.name}`}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        minHeight: 44,
        maxWidth: "100%",
        color: color ?? token.colorText,
        textDecoration: "none",
      }}
    >
      <Icon name="briefcase" size={18} />
      <span
        style={{ minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
      >
        {workspace.name}
      </span>
      {currency ? <Tag style={{ margin: 0, color: "inherit" }}>{currency.code}</Tag> : null}
    </Link>
  );
}
