from datetime import datetime
from zoneinfo import ZoneInfo

OPERATION_TIMEZONE = ZoneInfo("Asia/Shanghai")


class ShanghaiOperationClock:
    def now(self) -> datetime:
        return datetime.now(OPERATION_TIMEZONE).replace(tzinfo=None)
