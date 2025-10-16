class ApplicationRuntimeException(BaseException):
    """The runtime exception for BLUETTI integration"""

    message: str = "An unknown error has occurred."
    msgCode: int
    data: dict | str | None = None

    def __init__(self, msgCode: int, data: dict | str | None = None, errMessage: str = None):
        self.msgCode = msgCode
        self.data = data

        if errMessage is not None:
            self.message = errMessage

        super().__init__(self.message)
