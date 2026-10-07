from core.protocols import Clock, IdGenerator, OperationClock
from utils.clock import SystemClock
from utils.id_generator import UuidGenerator
from utils.operation_clock import ShanghaiOperationClock


def get_clock() -> Clock:
    return SystemClock()


def get_id_generator() -> IdGenerator:
    return UuidGenerator()


def get_operation_clock() -> OperationClock:
    return ShanghaiOperationClock()
