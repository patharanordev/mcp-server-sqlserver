from enum import Enum

class AutoStrEnum(Enum):
    def __str__(self):
        return self.value