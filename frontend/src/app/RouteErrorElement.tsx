import { useRouteError } from "react-router-dom";
import { FatalError } from "@/shared/errors";

/** Ошибка рендеринга внутри маршрута: react-router перехватывает её раньше корневого error boundary. */
export function RouteErrorElement() {
  const error = useRouteError();
  console.error("Ошибка рендеринга маршрута", error);
  return <FatalError />;
}
