import {
  Banknote,
  Briefcase,
  Bus,
  Car,
  CircleHelp,
  Coins,
  CreditCard,
  Download,
  Film,
  Gamepad2,
  Gift,
  GraduationCap,
  HeartPulse,
  House,
  Landmark,
  LogOut,
  type LucideIcon,
  Moon,
  PiggyBank,
  Plane,
  Settings,
  Share,
  Shirt,
  ShoppingCart,
  Smartphone,
  Sun,
  TrendingDown,
  TrendingUp,
  Utensils,
  Wallet,
  WifiOff,
  Zap,
} from "lucide-react";

/**
 * Бизнес-иконки категорий и кошельков — синхронизированы с backend/src/core/icons.json
 * (проверяется тестом icons.sync.test.ts). Изменение состава требует правки обоих файлов.
 */
const BUSINESS_ICONS: Record<string, LucideIcon> = {
  banknote: Banknote,
  briefcase: Briefcase,
  bus: Bus,
  car: Car,
  coins: Coins,
  "credit-card": CreditCard,
  film: Film,
  "gamepad-2": Gamepad2,
  gift: Gift,
  "graduation-cap": GraduationCap,
  "heart-pulse": HeartPulse,
  house: House,
  landmark: Landmark,
  "piggy-bank": PiggyBank,
  plane: Plane,
  shirt: Shirt,
  "shopping-cart": ShoppingCart,
  smartphone: Smartphone,
  "trending-down": TrendingDown,
  "trending-up": TrendingUp,
  utensils: Utensils,
  wallet: Wallet,
  zap: Zap,
};

/** Иконки интерфейса приложения — не относятся к категориям/кошелькам, вне реестра iconpack. */
const UI_ICONS: Record<string, LucideIcon> = {
  settings: Settings,
  sun: Sun,
  moon: Moon,
  "log-out": LogOut,
  download: Download,
  share: Share,
  "wifi-off": WifiOff,
};

/**
 * Закрытый набор иконок Lucide по именам (kebab-case), как они хранятся в БД.
 * Статическая карта (а не динамическая подгрузка) нужна, чтобы бандл и precache PWA не раздувались.
 */
export const ICONS: Record<string, LucideIcon> = { ...BUSINESS_ICONS, ...UI_ICONS };

/** Имена бизнес-иконок — для сверки с backend/src/core/icons.json (см. icons.sync.test.ts). */
export const BUSINESS_ICON_NAMES: readonly string[] = Object.keys(BUSINESS_ICONS);

export const FALLBACK_ICON: LucideIcon = CircleHelp;

export function resolveIcon(name: string): LucideIcon {
  return ICONS[name.trim().toLowerCase()] ?? FALLBACK_ICON;
}
