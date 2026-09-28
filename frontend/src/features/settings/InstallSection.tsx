import { Button, Typography } from "antd";
import { useInstallPrompt } from "@/shared/pwa/installPrompt";
import { Icon } from "@/shared/ui/Icon";
import { useToast } from "@/shared/ui/toast/ToastProvider";

/** Установка PWA: кнопка (Chrome/Android/десктоп) или инструкция (iOS Safari); в режиме standalone скрыта. */
export function InstallSection() {
  const { canInstall, install, isStandalone, isIos } = useInstallPrompt();
  const toast = useToast();

  if (isStandalone) return null;

  const handleInstall = () => {
    install().catch(() => toast.error("Не удалось открыть установку приложения"));
  };

  if (canInstall) {
    return (
      <Button block type="primary" icon={<Icon name="download" />} onClick={handleInstall}>
        Установить приложение
      </Button>
    );
  }
  if (isIos) {
    return (
      <Typography.Paragraph style={{ marginBottom: 0 }}>
        Чтобы установить приложение, нажмите <Icon name="share" size={16} /> «Поделиться» в Safari и
        выберите «На экран Домой».
      </Typography.Paragraph>
    );
  }
  return null;
}
