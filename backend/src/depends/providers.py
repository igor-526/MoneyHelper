from core.protocols import Clock, IdGenerator
from utils.clock import SystemClock
from utils.id_generator import UuidGenerator


def get_clock() -> Clock:
    return SystemClock()


def get_id_generator() -> IdGenerator:
    return UuidGenerator()
