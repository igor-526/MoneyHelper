export function unconvertedMessage(unconvertedCodes: string[], workspaceCode: string): string {
  return `Операции в валютах ${unconvertedCodes.join(", ")} не вошли в итоги: в воркспейсе нет пополнений, по которым можно вычислить курс к ${workspaceCode}.`;
}
