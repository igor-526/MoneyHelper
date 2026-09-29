/** Форма ответа backend (`CurrencyOut`) — только внутренний тип, наружу компонента не выходит. */
export interface CurrencyDto {
  id: string;
  code: string;
  name: string;
  decimal_places: number;
}

export interface Currency {
  id: string;
  code: string;
  name: string;
  decimalPlaces: number;
}

export function mapCurrency(dto: CurrencyDto): Currency {
  return { id: dto.id, code: dto.code, name: dto.name, decimalPlaces: dto.decimal_places };
}
