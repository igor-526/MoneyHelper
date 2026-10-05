import { useCurrentWorkspaceId } from "./WorkspaceContext";
import { useWorkspaces } from "./useWorkspaces";

/** Текущий воркспейс целиком (название, валюта); `undefined`, пока список не загружен. */
export function useCurrentWorkspace() {
  const workspaceId = useCurrentWorkspaceId();
  const { data } = useWorkspaces();
  return data?.find((workspace) => workspace.id === workspaceId);
}
