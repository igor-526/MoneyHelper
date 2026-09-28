import { Outlet } from "react-router-dom";
import { useIsMobile } from "@/shared/ui/useIsMobile";
import { DesktopShell } from "./DesktopShell";
import { MobileShell } from "./MobileShell";

export function AppLayout() {
  const isMobile = useIsMobile();
  const Shell = isMobile ? MobileShell : DesktopShell;
  return (
    <Shell>
      <Outlet />
    </Shell>
  );
}
