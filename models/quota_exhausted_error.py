class QuotaExhaustedError(Exception):

    def __init__(
        self,
        retry_after: float,
        key: str,
        message: str
    ):
        super().__init__(message)
        self.retry_after = retry_after
        self.key = key
        self.message = message