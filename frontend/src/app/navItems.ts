export interface NavItem {
  key: string;
  path: string;
  label: string;
  /** Имя иконки Lucide (kebab-case). */
  icon: string;
}

/** Пункты навигации задаются конфигурацией; на телефоне нижняя панель вмещает не более 5 пунктов. */
export const navItems: readonly NavItem[] = [
  { key: "home", path: "/", label: "Главная", icon: "house" },
  { key: "wallets", path: "/wallets", label: "Кошельки", icon: "wallet" },
  { key: "transactions", path: "/transactions", label: "Операции", icon: "banknote" },
  { key: "settings", path: "/settings", label: "Настройки", icon: "settings" },
];

export function activeNavKey(pathname: string): string | undefined {
  return navItems.find((item) => item.path === pathname)?.key;
}
