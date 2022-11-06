class ServiceDenial(BaseException):
    """Endpoint вернул ошибку."""

    def __init__(self, code):
        self.code = code
        if code == 'UnknownError':
            self.message = (f'Ошибка: {code}, '
                            f'проверьте "params".')
        elif code == 'not_authenticated':
            self.message = (f'Ошибка: {code}, '
                            f'проверьте "headers".')
        super().__init__(self.message)


class ResponseException(BaseException):
    """Неожиданный код ответа."""
