import {
  Banknote,
  Bus,
  Car,
  CircleHelp,
  Coins,
  CreditCard,
  Gift,
  Landmark,
  type LucideIcon,
  PiggyBank,
  ShoppingCart,
  Smartphone,
  Utensils,
  Wallet,
  House,
  Settings,
  Briefcase,
  HeartPulse,
  Plane,
  Shirt,
  GraduationCap,
  Gamepad2,
  Film,
  TrendingDown,
  TrendingUp,
  Zap,
  WifiOff,
  Download,
  Share,
  Sun,
  Moon,
  LogOut,
} from "lucide-react";

/**
 * Закрытый набор иконок Lucide по именам (kebab-case), как они хранятся в БД.
 * Статическая карта (а не динамическая подгрузка) нужна, чтобы бандл и precache PWA не раздувались;
 * полный набор для категорий и кошельков будет определён в задаче «Iconpack».
 */
export const ICONS: Record<string, LucideIcon> = {
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
  settings: Settings,
  shirt: Shirt,
  "shopping-cart": ShoppingCart,
  smartphone: Smartphone,
  "trending-down": TrendingDown,
  "trending-up": TrendingUp,
  utensils: Utensils,
  wallet: Wallet,
  zap: Zap,
  "wifi-off": WifiOff,
  download: Download,
  share: Share,
  sun: Sun,
  moon: Moon,
  "log-out": LogOut,
};

export const FALLBACK_ICON: LucideIcon = CircleHelp;

export function resolveIcon(name: string): LucideIcon {
  return ICONS[name.trim().toLowerCase()] ?? FALLBACK_ICON;
}
