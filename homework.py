import sys
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

PERIOD_MONTH = 60 * 60 * 24 * 30
RETRY_TIME = 600  # default 600
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
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    logger.info(
        msg=f'Отправлено сообщение {message} в чат {TELEGRAM_CHAT_ID}.')


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса"""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT,
                            headers=HEADERS,
                            params=params)
    return response.json()


def check_response(response, bot):
    """Проверяет ответ API на корректность"""
    if type(response) is dict:
        return response.get('homeworks')
    logger.error(msg='Сбой при запросе к эндпоинту.')
    send_message(bot, 'Сбой при запросе к эндпоинту.')
    return f'Data type of the response may be incorrect: {type(response)}'


def parse_status(homework):
    """Извлекает из информации о конкретной домашней
    работе статус этой работы"""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES[homework_status]
    return (f'Изменился статус проверки работы "{homework_name}".'
            f'{verdict}')


def check_tokens():
    """Проверяет доступность переменных окружения,
    которые необходимы для работы программы"""
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
    current_timestamp = int(time.time())
    old_status = ''
    old_error = ''

    while True:
        try:
            # Выбираем временной период
            current_timestamp = current_timestamp - PERIOD_MONTH
            # Проверяем токены. Ошибка в них вызывает лавину ошибок,
            # поэтому их проверяем отдельно и прерываем выполнение программы
            if not check_tokens():
                print('Ошибка токенов, всё пропало!')
                exit()
            # Назначаем бота
            bot = telegram.Bot(token=TELEGRAM_TOKEN)
            # Сделать запрос к API.
            response = get_api_answer(current_timestamp)
            # Проверить ответ.
            homeworks = check_response(response, bot=bot)
            # Если есть обновления — получить статус работы из
            # обновления и отправить сообщение в Telegram.
            hw_result = parse_status(homeworks[0])

            if hw_result == old_status:
                logger.debug('В ответе нет новых статусов')
                old_status = hw_result
            else:
                send_message(bot=bot, message=hw_result)
                old_status = hw_result

        except TypeError as error:
            logger.critical(f'{error}')
        except UnboundLocalError as error:
            logger.critical(error)
        except ConnectionError as error:
            logger.error(error)
        except KeyError as error:
            logger.error(f'{error}, вероятно что-то не так с ответом API.')
            if error != old_error:
                send_message(bot, error)
                old_error = error
        except Exception as error:
            if error != old_error:
                send_message(bot, error)
                old_error = error
            message = f'{error}'
            print(message)
            logging.error(f'{error}')

        else:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
