import { Alert, Button } from "antd";
import { Icon } from "../ui/Icon";
import { useOnlineStatus } from "./useOnlineStatus";
import { usePwaUpdate } from "./usePwaUpdate";
import styles from "./PwaBanners.module.css";

/**
 * Баннеры «нет соединения» и «доступна новая версия». `aboveTabBar` поднимает их над нижней панелью
 * навигации на телефоне; отступы учитывают безопасные зоны экрана.
 */
export function PwaBanners({ aboveTabBar = false }: { aboveTabBar?: boolean }) {
  const online = useOnlineStatus();
  const { needRefresh, update } = usePwaUpdate();

  if (online && !needRefresh) return null;

  return (
    <div className={aboveTabBar ? `${styles.stack} ${styles.aboveTabBar}` : styles.stack}>
      {!online && (
        <Alert
          type="warning"
          showIcon
          icon={<Icon name="wifi-off" />}
          title="Нет соединения. Данные могут быть недоступны"
        />
      )}
      {needRefresh && (
        <Alert
          type="info"
          showIcon
          title="Доступна новая версия"
          action={
            <Button type="primary" onClick={() => void update()}>
              Обновить
            </Button>
          }
        />
      )}
    </div>
  );
}
