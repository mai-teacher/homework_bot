"""
Бот-ассистент.
Telegram-бот, который обращается к API сервиса Практикум.Домашка для
получения статуса домашней работы и отправки результата Telegram-пользователю.
"""

__author__ = 'Alexander Makeev'

import logging
import os
import sys
import time
from http import HTTPStatus

from dotenv import load_dotenv
import requests
import telegram

from exceptions import InvalidResponseCode, EmptyResponseFromAPI

load_dotenv()
logger = logging.getLogger(__name__)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения."""
    ENV_VARS = (
        (PRACTICUM_TOKEN, 'PRACTICUM_TOKEN'),
        (TELEGRAM_TOKEN, 'TELEGRAM_TOKEN'),
        (TELEGRAM_CHAT_ID, 'TELEGRAM_CHAT_ID'),
    )

    logger.debug('Вызов функции check_tokens()')
    result = True
    for var, name in ENV_VARS:
        if not var:
            result = False
            logger.critical(
                f'Отсутствует обязательная переменная окружения: "{name}"')
    if not result:
        logger.critical('Останов программы ***************')
        raise SystemExit('Выход из программы')

    logger.info('Переменные окружения доступны')


def send_message(bot, message) -> bool:
    """Отправляет сообщение в Telegram чат."""
    logger.debug(f'Попытка отправки сообщения "{message}"')
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except telegram.error.TelegramError as error:
        logger.error(error)
        return False
    logger.debug(f'Успешно отправлено сообщение "{message}"')
    return True


def get_api_answer(timestamp) -> dict:
    """Делает запрос к единственному эндпоинту API-сервиса."""
    REQUEST = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp}
    }
    logger.debug('Делаем попытку запроса к API ЯП "{url}" с параметрами '
                 '{headers}, {params}'.format(**REQUEST))
    try:
        response: requests.models.Response = requests.get(**REQUEST)
        if response.status_code != HTTPStatus.OK:
            raise InvalidResponseCode(
                response.status_code,
                response.reason,
                response.text,
                'Ошибка в получении данных от API'
            )
        return response.json()
    except Exception:
        raise ConnectionError('Ошибка подключения "{url}", {headers}, {params}'
                              .format(**REQUEST))


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    logger.debug('Начинаем проверять ответ API ЯП')
    if not isinstance(response, dict):
        raise TypeError('Полученный ответ не является словарём')
    homeworks = response.get('homeworks')
    if not homeworks:
        raise EmptyResponseFromAPI('Пришёл пустой ответ от API')
    if not isinstance(homeworks, list):
        raise TypeError('Полученный ответ не является списком')
    logger.info('Ожидаемые ключи найдены в ответе API')
    return homeworks


def parse_status(homework) -> str:
    """Извлекает из информации о конкретной домашней работе её статус."""
    logger.debug('Начинаем разбор статуса домашней работы')
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise KeyError('Нет ключа "homework_name"')
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS:
        raise ValueError('Неожиданный статус домашней работы')
    verdict = HOMEWORK_VERDICTS.get(status)
    return (f'Изменился статус проверки работы "{homework_name}".'
            f'{verdict}')


def main():
    """Основная логика работы бота."""
    logger.info('Старт программы ***************')
    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = 0
    current_report = {
        'name': '',
        'message': '',
    }
    prev_report = current_report.copy()

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                homework = homeworks[0]
                current_report['name'] = homework['homework_name']
                current_report['message'] = parse_status(homework)
            else:
                current_report['message'] = ('Отсутствие в ответе новых'
                                             ' статусов')
            if current_report != prev_report:
                if send_message(bot, current_report['message']):
                    prev_report = current_report.copy()
                    timestamp = response.get('current_date', timestamp)
            else:
                logger.debug('Отсутствие в ответе новых статусов')

        except EmptyResponseFromAPI as error:
            logger.error(error)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            current_report['message'] = message
            logger.error(message)
            if current_report != prev_report:
                send_message(bot, current_report['message'])
                prev_report = current_report.copy()
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    formatter = ('%(asctime)s [%(levelname)s] <%(name)s> "%(filename)s".'
                 '%(funcName)s(%(lineno)d) - %(message)s')
    logging.basicConfig(
        level=logging.DEBUG,
        encoding='UTF-8',
        format=formatter
    )
    handler = logging.StreamHandler(stream=sys.stdout)
    file_handler = logging.FileHandler(__file__ + '.log', encoding='UTF-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(formatter))
    logger.addHandler(handler)
    logger.addHandler(file_handler)

    try:
        main()
    except KeyboardInterrupt:
        logger.info('Останов программы ***************')
