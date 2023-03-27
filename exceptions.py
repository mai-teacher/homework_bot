class InvalidResponseCode(Exception):
    """Неверный код ответа."""

    def __init__(self, code, reason, text,
                 message='Ошибка в получении данных от API'):
        """Конструктор."""
        self.code = code
        self.reason = reason
        self.text = text
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        """переопределяем метод '__str__'."""
        return (f'Ошибка с кодом {self.code} по причине {self.reason} '
                f'в получении данных от API {self.text}')


class EmptyResponseFromAPI(Exception):
    """Пустой ответ от API."""

    pass
