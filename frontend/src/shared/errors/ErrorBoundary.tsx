import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  /** Перезагрузка страницы; подменяется в тестах. */
  onReload?: () => void;
}

interface State {
  failed: boolean;
}

/** Экран критической ошибки: без antd, цвета из CSS-переменных (корректен в обеих темах). */
export function FatalError({ onReload }: { onReload?: () => void }) {
  const reload = onReload ?? (() => window.location.reload());
  return (
    <main className="fatal" role="alert">
      <h1>Что-то пошло не так</h1>
      <p>Произошла непредвиденная ошибка. Перезагрузите приложение.</p>
      <button type="button" onClick={reload}>
        Перезагрузить
      </button>
    </main>
  );
}

/**
 * Корневой error boundary для ошибок рендеринга. Не зависит от antd и провайдеров, чтобы экран ошибки
 * работал даже при их сбое.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("Ошибка рендеринга", error, info.componentStack);
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return <FatalError onReload={this.props.onReload} />;
  }
}
