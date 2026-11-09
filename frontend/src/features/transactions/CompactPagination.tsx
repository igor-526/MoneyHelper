import { Button, Flex } from "antd";

export function pageWindow(current: number, total: number): number[] {
  return Array.from(
    { length: Math.min(total, current + 1) - Math.max(1, current - 1) + 1 },
    (_, index) => Math.max(1, current - 1) + index,
  );
}

export function CompactPagination({
  current,
  total,
  onChange,
}: {
  current: number;
  total: number;
  onChange: (page: number) => void;
}) {
  if (total <= 1) return null;
  return (
    <nav aria-label="Страницы операций" style={{ maxWidth: "100%", overflowX: "auto" }}>
      <Flex gap={8} style={{ width: "max-content" }}>
        {current > 2 ? (
          <Button aria-label="Первая страница" onClick={() => onChange(1)}>
            «
          </Button>
        ) : null}
        {pageWindow(current, total).map((page) => (
          <Button
            key={page}
            type={page === current ? "primary" : "default"}
            aria-current={page === current ? "page" : undefined}
            onClick={() => onChange(page)}
          >
            {page}
          </Button>
        ))}
        {current < total - 1 ? (
          <Button aria-label="Последняя страница" onClick={() => onChange(total)}>
            »
          </Button>
        ) : null}
      </Flex>
    </nav>
  );
}
