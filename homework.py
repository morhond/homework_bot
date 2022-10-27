import time
import logging
import os

import requests
import telegram

from dotenv import load_dotenv


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):  # DONE
    """Отправляет сообщение в Telegram чат,
    определяемый переменной окружения TELEGRAM_CHAT_ID"""
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)


def get_api_answer(current_timestamp):  # DONE
    """Делает запрос к единственному эндпоинту API-сервиса"""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT,
                            headers=HEADERS,
                            params=params)
    return response.json()


def check_response(response):  # DONE
    """Проверяет ответ API на корректность"""
    if type(response) is dict:
        return response.get('homeworks')
    return f'Data type of the responce is incorrect: {type(response)}'


def parse_status(homework):
    """Извлекает из информации о конкретной домашней
    работе статус этой работы"""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():  # DONE
    """Проверяет доступность переменных окружения,
    которые необходимы для работы программы"""
    if (PRACTICUM_TOKEN or TELEGRAM_TOKEN or TELEGRAM_CHAT_ID) is None:
        return False
    return True


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:

            current_timestamp = 1666874792-60*60*24*30
            # Проверяем токены.
            check_tokens()
            # Сделать запрос к API.
            response = get_api_answer(current_timestamp)
            # Проверить ответ.
            homeworks = check_response(response)
            # Если есть обновления — получить статус работы из
            # обновления и отправить сообщение в Telegram.
            hw_result = parse_status(homeworks[0])
            send_message(bot=bot, message=hw_result)

            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            print(message)
            time.sleep(RETRY_TIME)
        else:
            print('WTF?')


if __name__ == '__main__':
    main()
