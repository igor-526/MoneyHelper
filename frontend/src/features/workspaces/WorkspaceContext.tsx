import { createContext, useContext } from "react";

export const WorkspaceContext = createContext<string | null>(null);

/** Текущий `workspace_id` — синхронно нужен ~20 потребителям ниже (design.md), поэтому Context, не Query. */
export function useCurrentWorkspaceId(): string {
  const workspaceId = useContext(WorkspaceContext);
  if (workspaceId === null) {
    throw new Error("useCurrentWorkspaceId нужно вызывать внутри WorkspaceContext.Provider");
  }
  return workspaceId;
}
