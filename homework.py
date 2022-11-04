import sys
import time
import logging
import os
import requests
import telegram

from http import HTTPStatus
from dotenv import load_dotenv

import exceptions


load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

PERIOD_MONTH = 60 * 60 * 24 * 30
RETRY_TIME = 60 * 10  # in seconds, default 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}', 'Accept': 'application/json'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

handler = logging.StreamHandler(stream=sys.stdout)
logger = logging.getLogger(__name__)
logger.addHandler(handler)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info(
            msg=f'Отправлено сообщение {message} в чат {TELEGRAM_CHAT_ID}.')
    except telegram.TelegramError as error:
        logger.exception(error)


def get_api_answer(current_timestamp):  # добавить проверку на !=200
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT,
                                headers=HEADERS,
                                params=params)
        # --- это не работает ---
        # response_json = response.json()
        # if set(response_json.keys()) == {'error', 'code'}: # ругается на
        # AttributeError: 'list' object has no attribute 'keys'
        # но это абсолютная чушь, response_json это словарь, я проверял
        #     raise custom_exceptions.CustomException('Alles kaputt!')
        # raise ResponseException(...)
        # --------------------

        if response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR:
            logger.error('Внутренняя ошибка API (код 500).')
            raise exceptions.CustomException(
                'Внутренняя ошибка API (код 500).')
        if response.status_code == HTTPStatus.REQUEST_TIMEOUT:
            logger.error('Ошибка API (TIMEOUT).')
            raise exceptions.CustomException('Ошибка API (TIMEOUT).')

        # --- это работает ---
        # if response.status_code != HTTPStatus.OK:
        #     raise Exception('Проблемы с подключением к API.')
        # --------------------

    except requests.exceptions.RequestException as error:
        logger.exception(error)
    #except ConnectionError as error:
    #    logger.exception(error)
    #except requests.exceptions.HTTPError as error:
    #    logger.exception(error)
    #except requests.exceptions.TooManyRedirects as error:
    #    logger.exception(error)
    #except TimeoutError as error:
    #    logger.exception(error)
    return response.json()


def check_response(response):
    """Проверяет ответ API на корректность."""
    # проверяем ответ API на TypeError
    if not isinstance(response, dict):
        logger.exception('Неверный тип данных в ответе API.')
        raise TypeError()
    # проверяем полученный словарь на KeyError
    try:
        response.get('homeworks')
    except KeyError as error:
        logger.exception(error)
    # если KeyError не случился, проверяем на TypeError содержимое словаря
    if not isinstance(response.get('homeworks'), list):
        logger.exception('Неверный тип данных в ответе API по ключу "homeworks".')
        raise TypeError()
    return response.get('homeworks')



def parse_status(homework):
    """Извлекает из домашней работы статус этой работы."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    try:
        verdict = HOMEWORK_STATUSES[homework_status]
    except KeyError as error:
        logger.exception(error)
    return (f'Изменился статус проверки работы "{homework_name}".'
            f'{verdict}')


def check_tokens():
    """Проверяет доступность переменных окружения."""
    if isinstance(PRACTICUM_TOKEN, type(None)):
        logger.critical(msg='Не найден токен API!')
        return False
    if isinstance(TELEGRAM_TOKEN, type(None)):
        logger.critical(msg='Не найден токен бота Telegram!')
        return False
    if isinstance(TELEGRAM_CHAT_ID, type(None)):
        logger.critical(msg='Не найден токен чата Telegram!')
        return False
    return True


def main():
    """Основная логика работы бота."""
    logging.basicConfig(
        format='%(asctime)s [%(levelname)s] %(message)s',
        filename='hw_log.log',
        level=logging.DEBUG)
    current_timestamp = int(time.time())
    old_status = ''
    old_error = ''

    while True:
        try:
            # Назначаем бота
            bot = telegram.Bot(token=TELEGRAM_TOKEN)
            # Выбираем временной период
            current_timestamp = current_timestamp - PERIOD_MONTH
            # Проверяем токены. Ошибка в них вызывает лавину ошибок,
            # поэтому их проверяем отдельно и прерываем выполнение программы
            if not check_tokens():
                print('Ошибка токенов, всё пропало!')
                return 0
            # Сделать запрос к API.
            response = get_api_answer(current_timestamp)
            # Проверить ответ.
            homeworks = check_response(response)
            # Если есть обновления — получить статус работы из
            # обновления и отправить сообщение в Telegram.
            hw_result = parse_status(homeworks[0])

            if hw_result == old_status:
                logger.debug('В ответе нет новых статусов')
                old_status = hw_result
            else:
                send_message(bot=bot, message=hw_result)
                old_status = hw_result

        except Exception as error:
            if error != old_error:
                send_message(bot, error)
                old_error = error
            message = f'{error}'
            print(message)
            logging.error(f'{error}')

        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
