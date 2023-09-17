from datetime import datetime, timedelta
import yaml
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery)
from aiogram.types import Message
from entities import (
    get_booking_options, is_spot_free, get_parking_spot_by_name, get_user_by_username,
    create_reservation, is_user_admin, Reservation, ParkingSpot)

""" Текст, который будет выводить бот в сообщениях """
TEXT_BUTTON_1 = "Забронируй мне место на парковке"
TEXT_BUTTON_2 = "Отправь отчёт по брони"
START_MESSAGE = "Привет!\nМеня зовут Анна.\nПомогу забронировать место на парковке."
HELP_MESSAGE = "Напиши мне что-нибудь"
ALL_SPOT_ARE_BUSY_MESSAGE = "К сожалению, все места заняты 😢"
DATE_REQUEST_MESSAGE = 'Сейчас посмотрим, что я могу Вам предложить...'
ACCESS_IS_NOT_ALLOWED_MESSAGE = "Обмануть меня захотели? Ваш логин я записала и передам руководству какой Вы хулиган!"
BEFORE_SEND_REPORT_MESSAGE = "Конечно! Вот Ваш отчёт:\n\n"

all_roles_obj = []
all_users_obj = []
all_spots_obj = []


def get_inline_keyboard_for_booking(available_options: dict) -> InlineKeyboardMarkup:
    buttons_list = []

    # Создаём кнопку для каждой доступной даты
    for key, value in available_options.items():
        one_button: InlineKeyboardButton = InlineKeyboardButton(
            text=key.strftime("%d/%m/%Y"),
            callback_data=f'book {key} {value[0]}')
        buttons_list.append(one_button)

    # Создаем объект инлайн-клавиатуры
    keyboard: InlineKeyboardMarkup = InlineKeyboardMarkup(
        inline_keyboard=[buttons_list])
    return keyboard


# Получаем данные из файла настроек
with open('settings.yml', 'r') as file:
    CONSTANTS = yaml.safe_load(file)
API_TOKEN = CONSTANTS['API_TOKEN']

bot: Bot = Bot(token=API_TOKEN)
dp: Dispatcher = Dispatcher()


def create_main_menu_keyboard(is_show_full_version: bool) -> ReplyKeyboardMarkup:
    """ Создаёт клавиатуру, которая будет выводиться на команду /start """
    button_1: KeyboardButton = KeyboardButton(text=TEXT_BUTTON_1)
    button_2: KeyboardButton = KeyboardButton(text=TEXT_BUTTON_2)

    buttons_list = [button_1]

    if is_show_full_version:
        buttons_list.append(button_2)

    # Создаем объект клавиатуры, добавляя в него кнопки
    keyboard: ReplyKeyboardMarkup = ReplyKeyboardMarkup(
        keyboard=[buttons_list],
        resize_keyboard=True
    )

    return keyboard


@dp.message(Command(commands=["start"]))
async def process_start_command(message: Message):
    """ Этот хэндлер обрабатывает команду "/start" """
    requester_username = message.from_user.username
    requester_is_admin = False

    if is_user_admin(requester_username):
        requester_is_admin = True

    await message.answer(
        START_MESSAGE,
        reply_markup=create_main_menu_keyboard(is_show_full_version=requester_is_admin)
    )


# Этот хэндлер будет срабатывать на команду "/help"
@dp.message(Command(commands=['help']))
async def process_help_command(message: Message):
    await message.answer(HELP_MESSAGE)


# Этот хэндлер будет срабатывать на просьбу забронировать место
@dp.message(F.text == TEXT_BUTTON_1)
async def process_answer(message: Message):
    available_options = get_booking_options()
    print(available_options)

    if len(available_options) > 0:
        inline_keyboard = get_inline_keyboard_for_booking(available_options)

        await message.reply(
            text=DATE_REQUEST_MESSAGE,
            reply_markup=inline_keyboard
        )
    else:
        await message.reply(
            text=ALL_SPOT_ARE_BUSY_MESSAGE,
            reply_markup=ReplyKeyboardRemove()
        )


@dp.callback_query(lambda c: c.data.startswith('book'))
async def process_button_callback(callback_query: CallbackQuery):
    """ Обработчик события нажатия на inline-кнопку с предлагаемой датой брони """
    # Получаем данные из нажатой кнопки
    button_data = callback_query.data

    query_data = button_data.split()
    booking_date = query_data[1]
    booking_spot = query_data[2]
    requester_username = callback_query.from_user.username

    if requester_username == "":
        requester_username = callback_query.from_user.first_name

    booking_spot_obj = get_parking_spot_by_name(booking_spot, all_spots_obj)
    if booking_spot_obj is None:
        print("Ошибка. Парковочное место не найдено.")

    #
    # Если у пользователя нет username, будет ошибка
    #
    requester_user = get_user_by_username(requester_username, all_users_obj)
    if type(requester_user) is str:
        # Отправляем ответ пользователю
        await bot.send_message(
            chat_id=callback_query.message.chat.id,
            text=f'Проищошла какая-то ошибка Т_Т'
        )

    # Проверяем, что слот свободен.
    # Если это так, то создаём запись в БД
    if is_spot_free(booking_spot_obj, booking_date):
        create_reservation(
            spot_id=booking_spot_obj.id,
            date=booking_date,
            user=requester_user
        )

    # Отправляем ответ пользователю
    await bot.send_message(
        chat_id=callback_query.message.chat.id,
        text=f'Хорошо)\nЗабронировала Вам место "{booking_spot}" на {booking_date}'
    )


if __name__ == '__main__':
    dp.run_polling(bot)


def run_bot(data: dict):
    global all_users_obj
    global all_roles_obj
    global all_spots_obj
    all_users_obj = data["all_users_obj"]
    all_roles_obj = data["all_roles_obj"]
    all_spots_obj = data["all_spots_obj"]

    print("Запускаю бота...")
    dp.run_polling(bot)


# Обработчик запроса на выгрузку отчёта по занятым местам
@dp.message(F.text == TEXT_BUTTON_2)
async def process_answer(message: Message):
    requester_username = message.from_user.username
    is_allowed = is_user_admin(requester_username)

    if not is_allowed:
        await bot.send_message(
            chat_id=message.chat.id,
            text=ACCESS_IS_NOT_ALLOWED_MESSAGE
        )
        return
    # Вычисление даты две недели назад
    two_weeks_ago = datetime.now() - timedelta(weeks=2)
    # Выполнение запроса на выборку
    reservations = Reservation.select().where(Reservation.booking_date >= two_weeks_ago)
    report = ""

    # Вывод результатов
    for reservation in reservations:
        report += f"Дата бронирования: {reservation.booking_date}. "
        report += f"Место: {reservation.parking_spot_id.name}. "
        report += f"Пользователь: {reservation.username}.\n\n"

    await bot.send_message(
        chat_id=message.chat.id,
        text=f"{BEFORE_SEND_REPORT_MESSAGE}{report}"
    )
