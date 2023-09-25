from datetime import datetime, timedelta, date
from typing import Union, Optional

import yaml
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery)
from aiogram.types import Message
from entities import (
    get_booking_options, is_spot_free, get_parking_spot_by_name, get_user_by_username, get_user_by_name, get_user_role,
    create_reservation, Reservation, User, Role, ParkingSpot)

""" Текст, который будет выводить бот в сообщениях """
TEXT_BUTTON_1 = "Забронируй мне место"
TEXT_BUTTON_2 = "Отправь отчёт по брони"
TEXT_BUTTON_3 = "Отмени бронь"
START_MESSAGE = "Привет!\nМеня зовут Анна.\nПомогу забронировать место на парковке."
HELP_MESSAGE = "/start - и мы начнём диалог сначала 👀\n/help - выводит данную подсказку 💁🏻‍♀️"
ALL_SPOT_ARE_BUSY_MESSAGE = "к сожалению, все места заняты 😢"
DATE_REQUEST_MESSAGE = 'Сейчас посмотрим, что я могу Вам предложить'
ACCESS_IS_NOT_ALLOWED_MESSAGE = "Нет 🙅🏻‍♀️"
UNKNOWN_USER_MESSAGE_1 = "Простите, я с незнакомцами не разговариваю 🙄"
UNKNOWN_USER_MESSAGE_2 = "💅🏻"
BEFORE_SEND_REPORT_MESSAGE = "Конечно! Вот Ваш отчёт:\n\n"
UNKNOWN_TEXT_MESSAGE = "Эммм ... 👀"
UNKNOWN_ERROR_MESSAGE = "Произошла какая-то ошибка. Мне так жаль 😢"
NO_RESERVATIONS_MESSAGE = "Кажется, пока никто ничего не забронировал 😒"
CANCEL_SUCCESS_MESSAGE = "Хорошо, удалила. 🫴🏻"

ROLE_ADMINISTRATOR = "ADMINISTRATOR"
ROLE_AUDITOR = "AUDITOR"
ROLE_CLIENT = "CLIENT"

all_roles_obj = []
all_users_obj = []
all_spots_obj = []

# Получаем данные из файла настроек
with open('settings.yml', 'r') as file:
    CONSTANTS = yaml.safe_load(file)

TODAY_DEADLINE_CLOCK = CONSTANTS["TODAY_DEADLINE_CLOCK"]


def get_inline_keyboard_for_booking(
        available_spots: list[ParkingSpot],
        available_date: datetime.date) -> InlineKeyboardMarkup:
    buttons_list = []

    """ Создаём кнопку для каждой доступной даты """
    for one_spot in available_spots:
        available_date_str = available_date.strftime("%Y-%m-%d")
        one_button: InlineKeyboardButton = InlineKeyboardButton(
            text=one_spot.name,
            callback_data=f'book {one_spot.name} {available_date_str}')
        buttons_list.append(one_button)

    """ Создаем объект инлайн-клавиатуры """
    keyboard: InlineKeyboardMarkup = InlineKeyboardMarkup(
        inline_keyboard=[buttons_list])
    return keyboard


""" Получаем данные из файла настроек """
with open('settings.yml', 'r') as file:
    CONSTANTS = yaml.safe_load(file)
API_TOKEN = CONSTANTS['API_TOKEN']

bot: Bot = Bot(token=API_TOKEN)
dp: Dispatcher = Dispatcher()


def is_message_from_unknown_user(message: Union[Message, CallbackQuery]) -> bool:
    requester_username = message.from_user.username
    if requester_username is None:
        requester_username = ""
    requester_user = get_user_by_username(requester_username)

    if requester_user is None:
        """ Либо такого пользователя нет, либо у нашего пользователя нет username """
        requester_first_name = message.from_user.first_name
        requester_last_name = message.from_user.last_name
        requester_user = get_user_by_name(requester_first_name, requester_last_name)
        if requester_user is None:
            """ Вообще нет такого пользователя """
            return True
        if requester_user.username == message.from_user.username:
            """ username у пользователей совпадают. Это наш пользователь. """
            return False
        else:
            """ username отличаются """
            return True
    else:
        return False


def create_start_menu_keyboard(
        is_show_book_button: bool,
        is_show_report_button: bool,
        is_show_cancel_button: bool,
) -> ReplyKeyboardMarkup:
    """ Создаёт клавиатуру, которая будет выводиться на команду /start """
    book_button: KeyboardButton = KeyboardButton(text=TEXT_BUTTON_1)
    report_button: KeyboardButton = KeyboardButton(text=TEXT_BUTTON_2)
    cancel_reservation_button: KeyboardButton = KeyboardButton(text=TEXT_BUTTON_3)

    buttons_list = []

    if is_show_book_button:
        buttons_list.append(book_button)
    if is_show_report_button:
        buttons_list.append(report_button)
    if is_show_cancel_button:
        buttons_list.append(cancel_reservation_button)

    # Создаем объект клавиатуры, добавляя в него кнопки
    keyboard: ReplyKeyboardMarkup = ReplyKeyboardMarkup(
        keyboard=[buttons_list],
        resize_keyboard=True
    )

    return keyboard


@dp.message(Command(commands=["start"]))
async def process_start_command(message: Message):
    """ Этот хэндлер обрабатывает команду "/start" """

    if is_message_from_unknown_user(message):
        await message.reply(
            UNKNOWN_USER_MESSAGE_1
        )
        await message.answer(
            UNKNOWN_USER_MESSAGE_2
        )
        return 0

    show_book_button = False
    show_report_button = False
    show_cancel_button = False

    """ Топорно пропишем полномочия на кнопки меню """
    user_role = get_user_role(message)
    if user_role == ROLE_ADMINISTRATOR:
        show_book_button = True
        show_report_button = True
    elif user_role == ROLE_AUDITOR:
        show_report_button = True
    elif user_role == ROLE_CLIENT:
        show_book_button = True

    requester = get_user_by_username(message.from_user.username)
    if requester is None:
        requester = get_user_by_name(message.from_user.first_name, message.from_user.last_name)
        if requester is None:
            print("Ошибка")
            return 0

    current_date = date.today()
    current_time = datetime.now().time()

    if current_time.hour >= TODAY_DEADLINE_CLOCK:
        checking_date = current_date + timedelta(days=1)
    else:
        checking_date = current_date

    reserved_spots = Reservation.select().where(
        Reservation.booking_date == checking_date,
        Reservation.user_id == requester.id
    ).count()

    if reserved_spots > 0:
        show_cancel_button = True

    await message.answer(
        START_MESSAGE,
        reply_markup=create_start_menu_keyboard(show_book_button, show_report_button, show_cancel_button)
    )


@dp.message(Command(commands=['help']))
async def process_help_command(message: Message):
    """ Этот хэндлер будет срабатывать на команду "/help" """
    await message.answer(HELP_MESSAGE)


@dp.message(F.text == TEXT_BUTTON_1)
async def process_answer(message: Message):
    """ Этот хэндлер срабатывает на просьбу забронировать место """
    if is_message_from_unknown_user(message):
        await message.reply(
            UNKNOWN_USER_MESSAGE_1
        )
        await message.answer(
            UNKNOWN_USER_MESSAGE_2
        )
        return 0

    if get_user_role(message) == ROLE_AUDITOR:
        await message.reply(
            ACCESS_IS_NOT_ALLOWED_MESSAGE
        )
        return 0

    requester = get_user_by_username(message.from_user.username)
    if requester is None:
        requester = get_user_by_name(message.from_user.first_name, message.from_user.last_name)
        if requester is None:
            print("Ошибка")
            return 0

    current_date = date.today()
    current_time = datetime.now().time()

    if current_time.hour >= TODAY_DEADLINE_CLOCK:
        checking_date = current_date + timedelta(days=1)
    else:
        checking_date = current_date

    reservations_by_user_count = Reservation.select(Reservation, User).join(User).where(
        Reservation.user_id == requester.id,
        Reservation.user_id.first_name == requester.first_name,
        Reservation.booking_date == checking_date
    ).count()

    if reservations_by_user_count > 0:
        await message.reply(
            text=f"У Вас уже есть забронированное место:",
            reply_markup=ReplyKeyboardRemove()
        )
        reserved_place = Reservation.get(
            Reservation.booking_date == checking_date,
            Reservation.user_id == requester.id
        )
        await message.answer(
            text=f"Место: {reserved_place.parking_spot_id.name}, дата: {reserved_place.booking_date}"
        )
        return 0

    available_spots, available_date = get_booking_options()

    if len(available_spots) > 0:
        inline_keyboard = get_inline_keyboard_for_booking(available_spots, available_date)

        await message.reply(
            text=" ".join([DATE_REQUEST_MESSAGE, "на", str(checking_date)]),
            reply_markup=inline_keyboard
        )
    else:
        await message.reply(
            text=f"Такс ...\nНа {checking_date}, {ALL_SPOT_ARE_BUSY_MESSAGE}",
            reply_markup=ReplyKeyboardRemove()
        )


@dp.callback_query(lambda c: c.data.startswith('book'))
async def process_button_callback(callback_query: CallbackQuery):
    """ Обработчик события нажатия на inline-кнопку с предлагаемой датой брони """
    if is_message_from_unknown_user(callback_query):
        await callback_query.reply(
            UNKNOWN_USER_MESSAGE_1
        )
        await callback_query.answer(
            UNKNOWN_USER_MESSAGE_2
        )
        return 0

    """ Получаем данные из нажатой кнопки """
    button_data = callback_query.data
    query_data = button_data.split()
    booking_spot = query_data[1]  # <- Выбранное парковочное место
    booking_date = query_data[2]  # <- Выбранная дата бронирования
    requester_username = callback_query.from_user.username

    print("query_data: ", query_data)

    if requester_username == "":
        requester_username = callback_query.from_user.first_name

    all_spots = ParkingSpot.select()
    booking_spot_obj = get_parking_spot_by_name(booking_spot, all_spots)
    print("booking_spot_obj: ", booking_spot_obj)
    if booking_spot_obj is None:
        print("Ошибка. Парковочное место не найдено.")
        return 0

    requester_user = get_user_by_username(requester_username)
    if requester_user is None:
        requester_first_name = callback_query.from_user.first_name
        requester_last_name = callback_query.from_user.last_name
        requester_user = get_user_by_name(requester_first_name, requester_last_name)
        if requester_user is None:
            await bot.send_message(
                chat_id=callback_query.message.chat.id,
                text=UNKNOWN_ERROR_MESSAGE)
            return 0

    """ Проверяем, что слот свободен. Если да, то создаём запись в БД """
    if is_spot_free(booking_spot_obj, booking_date):
        create_reservation(
            spot_id=booking_spot_obj.id,
            date=booking_date,
            user=requester_user
        )

    """ Отправляем ответ пользователю """
    await bot.send_message(
        chat_id=callback_query.message.chat.id,
        text=f'Хорошо 😊 \nЗабронировала Вам место "{booking_spot}" на {booking_date}',
        reply_markup=ReplyKeyboardRemove()
    )

    """ Удаляем кнопки у предыдущего сообщения с вариантами бронирования """
    await callback_query.message.edit_reply_markup(
        reply_markup=None
    )

    """ Обрабатываем полученный callback по правилам хорошего тона и чтобы кнопка не моргала постоянно """
    await callback_query.answer(
        text=f'Успешно!'
    )


if __name__ == '__main__':
    dp.run_polling(bot)


def run_bot(data: dict):
    """ Функция запуска бота """
    global all_users_obj
    global all_roles_obj
    global all_spots_obj
    all_users_obj = data["all_users_obj"]
    all_roles_obj = data["all_roles_obj"]
    all_spots_obj = data["all_spots_obj"]

    print("Запускаю бота...")
    dp.run_polling(bot)


@dp.message(F.text == TEXT_BUTTON_2)
async def process_answer(message: Message):
    """ Обработчик запроса на выгрузку отчёта по занятым местам """

    if is_message_from_unknown_user(message):
        await message.reply(
            UNKNOWN_USER_MESSAGE_1
        )
        await message.answer(
            UNKNOWN_USER_MESSAGE_2
        )
        return 0

    if get_user_role(message) == ROLE_CLIENT:
        await message.reply(
            ACCESS_IS_NOT_ALLOWED_MESSAGE
        )
        return 0

    """ Вычисление даты две недели назад """
    two_weeks_ago = datetime.now() - timedelta(weeks=2)
    """ Выполнение запроса на выборку """
    reservations = Reservation.select().where(Reservation.booking_date >= two_weeks_ago)
    report = ""
    """ Вывод результатов """
    for reservation in reservations:
        user_name = reservation.user_id.username
        if (user_name == "") or (user_name is None):
            user_name = " ".join([reservation.user_id.first_name, reservation.user_id.last_name])
        report += f"Дата бронирования: {reservation.booking_date}. "
        report += f"Место: {reservation.parking_spot_id.name}. "
        report += f"Пользователь: {user_name}.\n\n"

    if report == "":
        await bot.send_message(
            chat_id=message.chat.id,
            text=NO_RESERVATIONS_MESSAGE
        )
        return 0

    await bot.send_message(
        chat_id=message.chat.id,
        text=f"{BEFORE_SEND_REPORT_MESSAGE}{report}",
        reply_markup=ReplyKeyboardRemove()
    )


@dp.message(F.text == TEXT_BUTTON_3)
async def process_cancel(message: Message):
    """ Этот хэндлер срабатывает на просьбу отменить бронь """
    if is_message_from_unknown_user(message):
        await message.reply(
            UNKNOWN_USER_MESSAGE_1
        )
        await message.answer(
            UNKNOWN_USER_MESSAGE_2
        )
        return 0

    if get_user_role(message) == ROLE_AUDITOR:
        await message.reply(
            ACCESS_IS_NOT_ALLOWED_MESSAGE
        )
        return 0

    requester = get_user_by_username(message.from_user.username)
    if requester is None:
        requester = get_user_by_name(message.from_user.first_name, message.from_user.last_name)
        if requester is None:
            print("Ошибка")
            return 0

    current_date = date.today()
    current_time = datetime.now().time()

    if current_time.hour >= TODAY_DEADLINE_CLOCK:
        checking_date = current_date + timedelta(days=1)
    else:
        checking_date = current_date

    reservation_by_user = Reservation.select().where(
        Reservation.user_id == requester.id,
        Reservation.booking_date == checking_date
    ).first()

    if reservation_by_user is None:
        await message.answer(text="У Вас нет брони")
        return 0
    else:
        one_button: InlineKeyboardButton = InlineKeyboardButton(
            text="Отменить",
            callback_data=f'cancel {reservation_by_user.id}')

        """ Создаем объект инлайн-клавиатуры """
        keyboard: InlineKeyboardMarkup = InlineKeyboardMarkup(
                inline_keyboard=[[one_button]])
        await message.answer(
            text=" ".join(["У Вас есть бронь места:", reservation_by_user.parking_spot_id.name, "на", str(checking_date)]),
            reply_markup=keyboard
        )


@dp.callback_query(lambda c: c.data.startswith('cancel'))
async def process_button_cancel(callback_query: CallbackQuery):

    """ Получаем данные из нажатой кнопки """
    button_data = callback_query.data
    query_data = button_data.split()
    reservation_id = query_data[1]
    Reservation.delete().where(Reservation.id == reservation_id).execute()

    await callback_query.answer(
        text=CANCEL_SUCCESS_MESSAGE,
        reply_markup=ReplyKeyboardRemove()
    )

    await callback_query.answer(
        text="Успешно",
        reply_markup=ReplyKeyboardRemove()
    )

    """ Отправляем ответ пользователю """
    await bot.send_message(
        chat_id=callback_query.message.chat.id,
        text=CANCEL_SUCCESS_MESSAGE,
        reply_markup=ReplyKeyboardRemove()
    )


@dp.message()
async def process_other_messages(message: Message):
    """ Обработчик остальных сообщений. Выводит сообщение и вызывает обработчик /help """
    await message.answer(text=UNKNOWN_TEXT_MESSAGE)
    await process_help_command(message)
