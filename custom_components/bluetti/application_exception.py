class ApplicationRuntimeException(BaseException):
    """The runtime exception for BLUETTI integration"""

    message: str = "An unknown error has occurred."
    msgCode: int
    data: dict | str | None = None

    def __init__(self, msgCode: int, data: dict | str | None = None):
        self.msgCode = msgCode
        self.data = data

        super().__init__(self.message)
