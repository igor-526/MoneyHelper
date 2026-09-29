from core.entities.base import Entity


class Currency(Entity):
    code: str
    name: str
    decimal_places: int
