import type { LucideProps } from "lucide-react";
import { createElement } from "react";
import { resolveIcon } from "./icons";

interface IconProps {
  /** Имя иконки Lucide в том виде, в каком оно хранится в БД (kebab-case). */
  name: string;
  size?: number;
  /** Подпись для скринридера; без неё иконка декоративная. */
  label?: string;
}

export function Icon({ name, size = 20, label }: IconProps) {
  const props: LucideProps & { "data-icon": string } = {
    size,
    "aria-hidden": label ? undefined : true,
    "aria-label": label,
    role: label ? "img" : undefined,
    "data-icon": name,
  };
  return createElement(resolveIcon(name), props);
}
