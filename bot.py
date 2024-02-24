from datetime import datetime, timedelta, date

import yaml
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State, default_state
from aiogram.types import Message
from aiogram.types import (
    ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery)

from entities import Reservation, User, ParkingSpot, Guest, Role

from peewee import DoesNotExist

""" Текст, который будет выводить бот в сообщениях """
TEXT_BUTTON_1 = "Забронируй мне место 🅿️"
TEXT_BUTTON_2 = "Отправь отчёт по брони за 2 недели 📝"
TEXT_BUTTON_3 = "Отмени бронь ❌"
TEXT_BUTTON_4 = "Покажи свободные места на текущую дату 🕒"
START_MESSAGE = "Привет!\nМеня зовут Анна.\nПомогу забронировать место на парковке."
HELP_MESSAGE = "/start - и мы начнём диалог сначала 👀\n/help - выводит данную подсказку 💁🏻‍♀️"
ALL_SPOT_ARE_BUSY_MESSAGE = "к сожалению, все места заняты 😢"
DATE_REQUEST_MESSAGE = 'Сейчас посмотрим, что я могу Вам предложить'
ACCESS_IS_NOT_ALLOWED_MESSAGE = "Нет 🙅🏻‍♀️"
UNKNOWN_USER_MESSAGE_1 = "Эммм ... Мы с Вами знакомы? 👀"
UNKNOWN_USER_MESSAGE_2 = "💅🏻"
BEFORE_SEND_REPORT_MESSAGE = "Конечно! Вот Ваш отчёт:\n\n"
UNKNOWN_TEXT_MESSAGE = "Эммм ... 👀"
UNKNOWN_ERROR_MESSAGE = "Произошла какая-то ошибка. Мне так жаль 😢"
NO_RESERVATIONS_MESSAGE = "Кажется, пока никто ничего не забронировал 😒"
CANCEL_SUCCESS_MESSAGE = "Хорошо, удалила. 🫴🏻"
TEXT_ADD_USER_BUTTON = "Добавить пользователя 👤"
TEXT_DELETE_USER_BUTTON = "Удалить пользователя 🪣"
INPUT_USERNAME_MESSAGE = "Введите username пользователя.\nЕсли его нет, введите 0"
INPUT_FIRST_NAME_MESSAGE = "Введите имя (first name) пользователя. \nЕсли его нет, введите 0"
INPUT_LAST_NAME_MESSAGE = "Введите фамилию (last name) пользователя\nЕсли его нет, введите 0"
CHOOSE_ROLE_MESSAGE = "Выберите роль пользователя:\n"
USER_ADDED_SUCCESS_MESSAGE = "Записала ✍🏻\nБуду рада познакомиться с новым пользователем 👀"
UNCORRECT_CHOICE_MESSAGE = "Ну нет такого варианта! 🤦🏻‍♀️"
CHOOSE_GUEST_MESSAGE = "Ко мне приходили следующие неизвестные пользователи ... 👁️"
NO_GUESTS_MESSAGE = "Ко мне никто не приходил. Некого добавлять 🤷🏻‍♀️"
SUCCESS_MESSAGE = "Успешно"
TEXT_CHOOSE_USER_FOR_DELETE_MESSAGE = "Хорошо. Мне нужно знать внутренний id кого удаляем:\n*Если нужна отмена, введите -1"
TEXT_UNCORRECT_USER_ID_MESSAGE = "Не совсем поняла Вас 🤨"
TEXT_DELETE_USER_SUCCESS_MESSAGE = "Вычеркнула из списка пользователей. Я буду по нему скучать 😢 ... хотя кого я обманываю 💃🏼."
TEXT_DELETE_USER_CANCEL_MESSAGE = "Хорошо. Сделаем вид, что ничего не было 💅"

ROLE_ADMINISTRATOR = "ADMINISTRATOR"
ROLE_AUDITOR = "AUDITOR"
ROLE_CLIENT = "CLIENT"

# Получаем данные из файла настроек
with open('settings.yml', 'r') as file:
    CONSTANTS = yaml.safe_load(file)

TODAY_DEADLINE_CLOCK_FOR_CLIENTS = CONSTANTS["TODAY_DEADLINE_CLOCK_FOR_CLIENTS"]


class FSMFillForm(StatesGroup):
    # Создаем экземпляры класса State, последовательно
    # перечисляя возможные состояния, в которых будет находиться
    # бот в разные моменты взаимодейтсвия с пользователем
    add_user = State()  # Состояние ожидания добавления нового пользователя в БД
    choose_role = State()  # Состояние ожидания выбора роли нового пользователя
    book_spot = State()  # Состаяние ожидания подтверждение на бронирование места
    choose_user_for_delete = State()  # Состояние выбора пользователя для удаления


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


async def is_user_unauthorized(message: Message):
    authorized_ids = [user.telegram_id for user in User.select()]

    if message.from_user.id not in authorized_ids:
        return True
    return False


async def send_refusal_unauthorized(message: Message):
    await message.answer(UNKNOWN_USER_MESSAGE_1)


def create_start_menu_keyboard(
        is_show_book_button: bool,
        is_show_report_button: bool,
        is_show_cancel_button: bool,
        is_show_adduser_button: bool = False,
        is_show_delete_user_button: bool = False,
        is_show_free_spots_button: bool = False
) -> ReplyKeyboardMarkup:
    """ Создаёт клавиатуру, которая будет выводиться на команду /start """
    book_button: KeyboardButton = KeyboardButton(text=TEXT_BUTTON_1)
    report_button: KeyboardButton = KeyboardButton(text=TEXT_BUTTON_2)
    cancel_reservation_button: KeyboardButton = KeyboardButton(text=TEXT_BUTTON_3)
    add_user_button: KeyboardButton = KeyboardButton(text=TEXT_ADD_USER_BUTTON)
    delete_user_button: KeyboardButton = KeyboardButton(text=TEXT_DELETE_USER_BUTTON)
    show_free_spots: KeyboardButton = KeyboardButton(text=TEXT_BUTTON_4)

    buttons_list = []

    """ 
    Каждый массив - один ряд кнопок.
    Чтобы кнопка была в отдельном ряду, необходимо, 
    чтобы каждая кнопка была в отдельном массиве 
    """
    if is_show_book_button:
        buttons_list.append([book_button])
    if is_show_report_button:
        buttons_list.append([report_button])
    if is_show_cancel_button:
        buttons_list.append([cancel_reservation_button])
    if is_show_adduser_button:
        buttons_list.append([add_user_button])
    if is_show_delete_user_button:
        buttons_list.append([delete_user_button])
    if is_show_free_spots_button:
        buttons_list.append([show_free_spots])

    """ Создаем объект клавиатуры, добавляя в него кнопки """
    keyboard: ReplyKeyboardMarkup = ReplyKeyboardMarkup(
        keyboard=buttons_list,
        resize_keyboard=True
    )

    return keyboard


@dp.message(Command(commands=["start"]))
async def process_start_command(message: Message, state: FSMContext):
    """ Этот хэндлер обрабатывает команду "/start" """

    """ Проверяем зарегистрирован ли пользователь """
    if await is_user_unauthorized(message):

        """ Проверяем, если этот пользователь уже обращался к боту, то заносить его повторно не нужно """
        guest = Guest.select().where(
            (Guest.username == message.from_user.username) &
            (Guest.first_name == message.from_user.first_name) &
            (Guest.last_name == message.from_user.last_name)
        ).first()
        if guest is None:
            """ Добавляем нового гостя в БД """
            new_guest = Guest.create(
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                telegram_id=message.from_user.id
            )
            new_guest.save()

        await send_refusal_unauthorized(message)
        return 0

    """ Переменные, указывающие на то, какие кнопки меню будут доступны в дальнейшем """
    show_book_button = False
    show_report_button = False
    show_cancel_button = False
    show_add_user_button = False
    show_delete_user_button = False
    show_free_spots_now = False

    """ Топорно пропишем полномочия на кнопки меню """
    user_telegram_id = message.from_user.id
    user_role = User.get_user_role(user_telegram_id)

    if user_role == ROLE_ADMINISTRATOR:
        show_book_button = True
        show_report_button = True
        show_add_user_button = True
        show_free_spots_now = True
        show_delete_user_button = True
    elif user_role == ROLE_AUDITOR:
        show_report_button = True
        show_free_spots_now = True
    elif user_role == ROLE_CLIENT:
        show_book_button = True

    user_id = message.from_user.id
    requester = User.get_user_by_id(user_id)

    if requester is None:
        print("Ошибка")
        return 0

    current_date = date.today()
    current_time = datetime.now().time()

    if current_time.hour >= TODAY_DEADLINE_CLOCK_FOR_CLIENTS:
        checking_date = current_date + timedelta(days=1)
    else:
        checking_date = current_date

    """ Проверяем есть ли у пользователя уже брони на текущую дату """
    reserved_spots = Reservation.select().where(
        Reservation.booking_date == checking_date,
        Reservation.user_id == requester.id
    ).count()

    """ Если есть, то показываем кнопку отмены, а кнопку бронирования убираем """
    if reserved_spots > 0:
        show_cancel_button = True
        show_book_button = False

    await state.clear()

    await message.answer(
        START_MESSAGE,
        reply_markup=create_start_menu_keyboard(
            show_book_button,
            show_report_button,
            show_cancel_button,
            show_add_user_button,
            show_delete_user_button,
            show_free_spots_now
        )
    )


@dp.message(Command(commands=['help']))
async def process_help_command(message: Message):
    """ Этот хэндлер будет срабатывать на команду "/help" """
    await message.answer(HELP_MESSAGE)


@dp.message(F.text == TEXT_BUTTON_1)
async def process_answer_book(message: Message):
    """ Этот хэндлер срабатывает на просьбу забронировать место """

    if await is_user_unauthorized(message):
        await send_refusal_unauthorized(message)
        return 0

    user_id = message.from_user.id
    if User.get_user_role(user_id) == ROLE_AUDITOR:
        await message.reply(
            ACCESS_IS_NOT_ALLOWED_MESSAGE
        )
        return 0

    requester_id = message.from_user.id
    requester = User.get_user_by_id(requester_id)

    if requester is None:
        print("Ошибка")
        return 0

    current_date = date.today()
    current_time = datetime.now().time()

    if current_time.hour >= TODAY_DEADLINE_CLOCK_FOR_CLIENTS:
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

    current_date = date.today()
    current_time = datetime.now().time()

    if current_time.hour >= TODAY_DEADLINE_CLOCK_FOR_CLIENTS:
        date_for_book = current_date + timedelta(days=1)
    else:
        date_for_book = current_date

    available_spots = ParkingSpot.get_booking_options(date_for_book)

    if len(available_spots) > 0:
        inline_keyboard = get_inline_keyboard_for_booking(available_spots, date_for_book)

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
    booking_spot_obj = ParkingSpot.get_parking_spot_by_name(booking_spot, all_spots)
    print("booking_spot_obj: ", booking_spot_obj)
    if booking_spot_obj is None:
        print("Ошибка. Парковочное место не найдено.")
        return 0

    requester_id = callback_query.from_user.id
    requester_user = User.get_user_by_id(requester_id)

    if requester_user is None:
        await bot.send_message(
            chat_id=callback_query.message.chat.id,
            text=UNKNOWN_ERROR_MESSAGE)
        return 0

    """ Проверяем, что слот свободен. Если да, то создаём запись в БД """
    if booking_spot_obj.is_spot_free(booking_date):
        Reservation.create_reservation(
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


def run_bot():
    print("Запускаю бота...")
    dp.run_polling(bot)


@dp.message(F.text == TEXT_BUTTON_2)
async def process_answer_send_report(message: Message):
    """ Обработчик запроса на выгрузку отчёта по занятым местам """

    if await is_user_unauthorized(message):
        await send_refusal_unauthorized(message)
        return 0

    user_id = message.from_user.id
    if User.get_user_role(user_id) == ROLE_CLIENT:
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
        try:
            user_name = reservation.user_id.username
        except DoesNotExist:
            user_name = "[ДАННЫЕ УДАЛЕНЫ]"

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


@dp.message(F.text == TEXT_BUTTON_4)
async def process_answer_free_spots(message: Message):
    """ Обработчик запроса на выгрузку отчёта по свободным местам """

    if await is_user_unauthorized(message):
        await send_refusal_unauthorized(message)
        return 0

    user_id = message.from_user.id
    if User.get_user_role(user_id) == ROLE_CLIENT:
        await message.reply(
            ACCESS_IS_NOT_ALLOWED_MESSAGE
        )
        return 0

    current_date = date.today()
    current_time = datetime.now().time()

    if current_time.hour >= TODAY_DEADLINE_CLOCK_FOR_CLIENTS:
        date_for_book = current_date + timedelta(days=1)
    else:
        date_for_book = current_date
    available_spots = ParkingSpot.get_booking_options(date_for_book)

    spots_name = []
    for one_spot in available_spots:
        spots_name.append(one_spot.name)
    report = "\n".join(spots_name)

    await bot.send_message(
        chat_id=message.chat.id,
        text=f"На {date_for_book} доступны следующие парковочные места:\n{report}",
        reply_markup=ReplyKeyboardRemove()
    )


@dp.message(F.text == TEXT_BUTTON_3)
async def process_cancel(message: Message):
    """ Этот хэндлер срабатывает на просьбу отменить бронь """
    if await is_user_unauthorized(message):
        await send_refusal_unauthorized(message)
        return 0

    user_id = message.from_user.id
    if User.get_user_role(user_id) == ROLE_AUDITOR:
        await message.reply(
            ACCESS_IS_NOT_ALLOWED_MESSAGE
        )
        return 0

    requester_id = message.from_user.id
    requester = User.get_user_by_id(requester_id)

    if requester is None:
        print("Ошибка")
        return 0

    current_date = date.today()
    current_time = datetime.now().time()

    if current_time.hour >= TODAY_DEADLINE_CLOCK_FOR_CLIENTS:
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
            text=" ".join(
                ["У Вас есть бронь места:", reservation_by_user.parking_spot_id.name, "на", str(checking_date)]),
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


# Этот хэндлер будет срабатывать на команду добавления нового пользователя в состоянии по умолчанию
@dp.message(F.text == TEXT_ADD_USER_BUTTON, StateFilter(default_state))
async def process_adduser_command(message: Message, state: FSMContext):
    if await is_user_unauthorized(message):
        await send_refusal_unauthorized(message)
        return 0

    user_id = message.from_user.id
    if User.get_user_role(user_id) == ROLE_AUDITOR:
        await message.reply(
            ACCESS_IS_NOT_ALLOWED_MESSAGE
        )
        return 0

    guests = Guest.select()

    """ Если не было гостей, то выводим сообщение """
    if len(guests) == 0:
        await bot.send_message(
            chat_id=message.chat.id,
            text=NO_GUESTS_MESSAGE,
            reply_markup=ReplyKeyboardRemove()
        )
        return 0

    for guest in guests:
        pass

    buttons_list = []

    """ Создаём кнопку для каждого пользователя в таблице guests """
    for guest in guests:
        one_button: InlineKeyboardButton = InlineKeyboardButton(
            text=str(guest),
            callback_data=f'adduser {guest.id}')
        buttons_list.append(one_button)

    """ Создаем объект инлайн-клавиатуры """
    keyboard: InlineKeyboardMarkup = InlineKeyboardMarkup(
        inline_keyboard=[buttons_list])

    await message.answer(
        text="Ко мне обращались следующие пользователи:\n",
        reply_markup=keyboard
    )

    await state.set_state(FSMFillForm.add_user)


@dp.callback_query(lambda c: c.data.startswith('adduser'), StateFilter(FSMFillForm.add_user))
async def process_button_addguest(callback_query: CallbackQuery, state: FSMContext):
    """ Обрабатываем событие добавления нового пользователя """
    button_data = callback_query.data
    query_data = button_data.split()
    guest_id = query_data[1]

    buttons_list = []
    buttons_list.append(
        InlineKeyboardButton(
            text=str(ROLE_ADMINISTRATOR),
            callback_data=f'addrole {guest_id} {ROLE_ADMINISTRATOR}')
    )
    buttons_list.append(
        InlineKeyboardButton(
            text=str(ROLE_AUDITOR),
            callback_data=f'addrole {guest_id} {ROLE_AUDITOR}')
    )
    buttons_list.append(
        InlineKeyboardButton(
            text=str(ROLE_CLIENT),
            callback_data=f'addrole {guest_id} {ROLE_CLIENT}')
    )

    """ Создаем объект инлайн-клавиатуры """
    keyboard: InlineKeyboardMarkup = InlineKeyboardMarkup(
        inline_keyboard=[buttons_list])

    """ Отправляем ответ пользователю """
    await bot.send_message(
        chat_id=callback_query.message.chat.id,
        text=CHOOSE_ROLE_MESSAGE,
        reply_markup=keyboard
    )

    await callback_query.answer(
        text=SUCCESS_MESSAGE,
        reply_markup=ReplyKeyboardRemove()
    )


@dp.callback_query(lambda c: c.data.startswith('addrole'), StateFilter(FSMFillForm.add_user))
async def process_button_choose_role(callback_query: CallbackQuery, state: FSMContext):
    """ Обрабатываем событие добавления нового пользователя """
    button_data = callback_query.data
    query_data = button_data.split()
    guest_id = query_data[1]
    guest_role = query_data[2]

    guest = Guest.get_by_id(guest_id)

    new_user = User.create(
        username=guest.username,
        first_name=guest.first_name,
        last_name=guest.last_name,
        role_id=Role.select().where(Role.name == guest_role),
        telegram_id=guest.telegram_id
    )
    new_user.save()
    guest.delete_guest()

    await callback_query.message.answer(text=USER_ADDED_SUCCESS_MESSAGE)


@dp.message(F.text == TEXT_DELETE_USER_BUTTON)
async def process_delete_user(message: Message, state: FSMContext):
    """ Обработчик команды удаления пользователя """

    if await is_user_unauthorized(message):
        await send_refusal_unauthorized(message)
        return 0

    all_users_str = User.get_all_users()
    all_users = "\n".join(all_users_str)

    await message.reply(text=TEXT_CHOOSE_USER_FOR_DELETE_MESSAGE, reply_markup=ReplyKeyboardRemove())
    await message.answer(text=all_users)
    await state.set_state(FSMFillForm.choose_user_for_delete)


@dp.message(StateFilter(FSMFillForm.choose_user_for_delete))
async def process_delete_specific_user(message: Message, state: FSMContext):
    """ Обработчик команды удаления пользователя """
    try:
        user_input = int(message.text)
    except ValueError:
        await message.reply(text=TEXT_UNCORRECT_USER_ID_MESSAGE)
        return 0

    """ Если пользователь выбирает отмену """
    if user_input == -1:
        await message.reply(text=TEXT_DELETE_USER_CANCEL_MESSAGE)
        await state.clear()
        return 0

    User.delete_user_by_id(user_input)

    await message.reply(text=TEXT_DELETE_USER_SUCCESS_MESSAGE)
    await state.clear()


@dp.message()
async def process_other_messages(message: Message):
    """ Обработчик остальных сообщений. Выводит сообщение и вызывает обработчик /help """
    await message.answer(text=UNKNOWN_TEXT_MESSAGE)
    await process_help_command(message)
