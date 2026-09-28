import { Layout, Menu } from "antd";
import type { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { PwaBanners } from "@/shared/pwa/PwaBanners";
import { Icon } from "@/shared/ui/Icon";
import { activeNavKey, navItems } from "../navItems";

/** Широкий экран: верхняя навигация, контент центрирован и ограничен по ширине. */
export function DesktopShell({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  const selected = activeNavKey(pathname);

  return (
    <Layout style={{ minHeight: "100dvh" }} data-testid="desktop-shell">
      <Layout.Header style={{ display: "flex", alignItems: "center", gap: 24, padding: "0 24px" }}>
        <strong style={{ color: "#fff", fontSize: 18 }}>MoneyHelper</strong>
        <Menu
          theme="dark"
          mode="horizontal"
          aria-label="Основная навигация"
          selectedKeys={selected ? [selected] : []}
          style={{ flex: 1, minWidth: 0 }}
          items={navItems.map((item) => ({
            key: item.key,
            icon: <Icon name={item.icon} />,
            label: <Link to={item.path}>{item.label}</Link>,
          }))}
        />
      </Layout.Header>
      <Layout.Content style={{ width: "100%", maxWidth: 960, margin: "0 auto", padding: 24 }}>
        {children}
      </Layout.Content>
      <PwaBanners />
    </Layout>
  );
}
