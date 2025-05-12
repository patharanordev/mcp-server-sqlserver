from models.enum import AutoStrEnum

class AppTransport(AutoStrEnum):
    """
    Enum for application transport protocols.
    """
    STDIO = "stdio"
    STREAM = "streamable-http"
    SSE = "sse"
