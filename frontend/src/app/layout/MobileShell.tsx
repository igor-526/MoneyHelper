import { theme } from "antd";
import type { CSSProperties, ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { PwaBanners } from "@/shared/pwa/PwaBanners";
import { Icon } from "@/shared/ui/Icon";
import { navItems } from "../navItems";
import styles from "./MobileShell.module.css";

/** Телефон: контент на всю ширину и фиксированная нижняя панель навигации с учётом безопасной зоны. */
export function MobileShell({ children }: { children: ReactNode }) {
  const { token } = theme.useToken();
  const vars = {
    "--shell-bg": token.colorBgLayout,
    "--bar-bg": token.colorBgContainer,
    "--bar-border": token.colorBorderSecondary,
    "--item-color": token.colorTextSecondary,
    "--item-active": token.colorPrimary,
  } as CSSProperties;

  return (
    <div className={styles.shell} style={vars} data-testid="mobile-shell">
      <main className={styles.main}>{children}</main>
      <nav className={styles.tabBar} aria-label="Основная навигация">
        {navItems.map((item) => (
          <NavLink
            key={item.key}
            to={item.path}
            end
            className={({ isActive }) =>
              isActive ? `${styles.item} ${styles.active}` : styles.item
            }
          >
            <Icon name={item.icon} size={22} />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
      <PwaBanners aboveTabBar />
    </div>
  );
}
