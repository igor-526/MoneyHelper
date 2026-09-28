import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ThemeProvider } from "@/shared/ui/theme/ThemeProvider";
import { DESKTOP_QUERY } from "@/shared/ui/useIsMobile";
import { setMedia } from "@/test/matchMedia";
import { ThemeSwitch } from "./ThemeSwitch";

function renderSwitch(mobile: boolean) {
  setMedia(DESKTOP_QUERY, !mobile);
  return render(
    <ThemeProvider>
      <ThemeSwitch />
    </ThemeProvider>,
  );
}

describe("ThemeSwitch", () => {
  it("на телефоне варианты идут столбиком, чтобы подписи не обрезались", () => {
    const { container } = renderSwitch(true);
    expect(container.querySelector(".ant-segmented-vertical")).toBeInTheDocument();
  });

  it("на широком экране варианты идут в ряд", () => {
    const { container } = renderSwitch(false);
    expect(container.querySelector(".ant-segmented-vertical")).not.toBeInTheDocument();
  });
});
