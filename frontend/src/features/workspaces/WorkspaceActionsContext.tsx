import { createContext, useContext } from "react";

export interface WorkspaceActions {
  switchWorkspace: (id: string) => void;
}

export const WorkspaceActionsContext = createContext<WorkspaceActions | null>(null);

/** Единственный потребитель — `WorkspacesSection` в «Настройках» (design.md, раздел 6). */
export function useWorkspaceActions(): WorkspaceActions {
  const actions = useContext(WorkspaceActionsContext);
  if (actions === null) {
    throw new Error("useWorkspaceActions нужно вызывать внутри WorkspaceActionsContext.Provider");
  }
  return actions;
}
