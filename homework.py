"""
Бот-ассистент.
Telegram-бот, который обращается к API сервиса Практикум.Домашка для
получения статуса домашней работы и отправки результата Telegram-пользователю.
"""

__author__ = 'Alexander Makeev'

import logging
import os
import requests
import sys
import time

from dotenv import load_dotenv

import telegram

load_dotenv()
logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    encoding='UTF-8',
    format='%(asctime)s [%(levelname)s] %(message)s'
)
handler = logging.StreamHandler(stream=sys.stdout)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

ENV_VARS = (
    (PRACTICUM_TOKEN, 'PRACTICUM_TOKEN'),
    (TELEGRAM_TOKEN, 'TELEGRAM_TOKEN'),
    (TELEGRAM_CHAT_ID, 'TELEGRAM_CHAT_ID'),
)

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

HOMEWORK_KEYS = ('status', 'homework_name',)

# Статус последней домашней работы
homework_status = ''


def check_tokens() -> bool:
    """Проверяет доступность переменных окружения."""
    logging.debug('Вызов функции check_tokens()')
    result = True
    for var, name in ENV_VARS:
        if var is None:
            result = False
            logging.critical(
                f'Отсутствует обязательная переменная окружения: "{name}"')
    if result:
        logging.info('Переменные окружения доступны')
    if not (PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID):
        logging.critical('Останов программы')
        sys.exit('Выход из программы')
    return result


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    logging.debug('Вызов функции send_message()')
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except telegram.TelegramError:
        logging.error(telegram.TelegramError)


def get_api_answer(timestamp) -> dict:
    """Делает запрос к единственному эндпоинту API-сервиса."""
    logging.debug('Вызов функции get_api_answer()')
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params={'from_date': timestamp})
    except requests.RequestException:
        pass

    if (response.status_code != 200):
        raise Exception('Ошибка в получении данных от API')
    return response.json()


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    logging.debug('Вызов функции check_response()')
    if type(response) != dict:
        raise TypeError
    homeworks = response.get('homeworks')
    if type(homeworks) != list:
        raise TypeError
    if homeworks is None:
        raise Exception('Отсутствие ключа "homeworks" в ответе API')
    if len(homeworks) == 0:
        raise Exception('Отсутствие данных в ключе "homeworks" в ответе API')
    for elem in HOMEWORK_KEYS:
        if homeworks[0].get(elem) is None:
            raise Exception(f'Отсутствие ключа "{elem}" в ответе API')
    logging.info('Ожидаемые ключи найдены в ответе API')


def parse_status(homework) -> str:
    """Извлекает из информации о конкретной домашней работе её статус."""
    logging.debug('Вызов функции parse_status()')
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise Exception('Нет ключа "homework_name"')
    status = homework.get('status')
    if status in HOMEWORK_VERDICTS:
        if homework_status != status:
            verdict = HOMEWORK_VERDICTS.get(status)
            return (f'Изменился статус проверки работы "{homework_name}".'
                    f'{verdict}')
        else:
            logging.debug('Отсутствие в ответе новых статусов')
    else:
        raise Exception('Неожиданный статус домашней работы')
    return None


def main():
    """Основная логика работы бота."""
    logging.info('Старт программы')
    if not check_tokens():
        logging.critical('Останов программы')
        sys.exit('Выход из программы')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            # print(response.get('homeworks')[0])
            message = parse_status(response.get('homeworks')[0])
            send_message(bot, message)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logging.error(message)

        time.sleep(RETRY_PERIOD)
    # logging.info('Останов программы')


if __name__ == '__main__':
    main()
