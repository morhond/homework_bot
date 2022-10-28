import sys
import time
import logging
import os

import requests
import telegram
from telegram import TelegramError

from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

PERIOD_MONTH = 60 * 60 * 24 * 30
RETRY_TIME = 2  # default 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s',
    filename='hw_log.log',
    level=logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
logger = logging.getLogger(__name__)
logger.addHandler(handler)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат,
    определяемый переменной окружения TELEGRAM_CHAT_ID"""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info(
            msg=f'Отправлено сообщение {message} в чат {TELEGRAM_CHAT_ID}.')
    except ConnectionError:
        logger.error(msg='Сбой отправки сообщения, вероятно сбой соединения.')
    except TelegramError:
        logger.error(msg='Сбой отправки сообщения.')


def get_api_answer(current_timestamp, bot):
    """Делает запрос к единственному эндпоинту API-сервиса"""
    try:
        timestamp = current_timestamp or int(time.time())
        params = {'from_date': timestamp}
        response = requests.get(ENDPOINT,
                                headers=HEADERS,
                                params=params)
        return response.json()
    except ConnectionError:
        logger.error('Недоступность эндпоинта')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text='Недоступность эндпоинта')


def check_response(response, bot):
    """Проверяет ответ API на корректность"""
    if type(response) is dict:
        return response.get('homeworks')
    logger.error(msg='Сбой при запросе к эндпоинту.')
    bot.send_message(chat_id=TELEGRAM_CHAT_ID,
                     text='Сбой при запросе к эндпоинту.')
    return f'Data type of the response may be incorrect: {type(response)}'


def parse_status(homework, bot):
    """Извлекает из информации о конкретной домашней
    работе статус этой работы"""
    try:
        homework_name = homework['homework_name']
    except KeyError:
        logger.error(msg='Отсутствие ожидаемых ключей в ответе API')
    try:
        homework_status = homework['status']
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except KeyError:
        logger.error(msg='Недокументированный статус домашней работы,'
                         'обнаруженный в ответе API')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID,
                         text='Недокументированный статус домашней работы,'
                         'обнаруженный в ответе API')


def check_tokens(bot):
    """Проверяет доступность переменных окружения,
    которые необходимы для работы программы"""
    if (
            isinstance(PRACTICUM_TOKEN, type(None)) or
            isinstance(TELEGRAM_TOKEN, type(None)) or
            isinstance(TELEGRAM_CHAT_ID, type(None))
    ):
        logger.critical(msg='Не найден один из токенов!')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID,
                         text='Не найден один из токенов!')
        return False
    return True


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    old_status = ''

    while True:
        try:
            # Выбираем временной период
            current_timestamp = current_timestamp - PERIOD_MONTH
            # Проверяем токены.
            check_tokens(bot=bot)
            # Сделать запрос к API.
            response = get_api_answer(current_timestamp, bot=bot)
            # Проверить ответ.
            homeworks = check_response(response, bot=bot)
            # Если есть обновления — получить статус работы из
            # обновления и отправить сообщение в Telegram.
            hw_result = parse_status(homeworks[0], bot=bot)

            if hw_result == old_status:
                logger.debug('В ответе нет новых статусов')
                old_status = hw_result
            else:
                send_message(bot=bot, message=hw_result)
                old_status = hw_result

            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            print(message)
            logging.error(f'Сбой в работе программы: {error}')
            time.sleep(RETRY_TIME)
        else:
            # выполняется в случае, если не срабатывает исключение
            print('Why is it here?')


if __name__ == '__main__':
    main()
