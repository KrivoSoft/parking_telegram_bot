from typing import Any
import yaml
from aiogram import Bot, Dispatcher, F
from aiogram.dispatcher import router
from aiogram.filters import Command
from aiogram.handlers import InlineQueryHandler
from aiogram.types import ReplyKeyboardRemove, \
    ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton, InlineQueryResult, InlineQueryResultsButton, InlineQueryResultArticle, \
    InputTextMessageContent
from aiogram.types import Message, InlineQuery
from entities import get_booking_options

TEXT_BUTTON_1 = "Забронировать место на парковке"
TEXT_BUTTON_2 = "Вывести список брони"
START_MESSAGE = "Привет!\nМеня зовут Анна.\nПомогу забронировать место на парковке."
HELP_MESSAGE = "Напиши мне что-нибудь"

# Получаем данные из файла настроек
with open('settings.yml', 'r') as file:
    CONSTANTS = yaml.safe_load(file)
API_TOKEN = CONSTANTS['API_TOKEN']

bot: Bot = Bot(token=API_TOKEN)
dp: Dispatcher = Dispatcher()

button_1: KeyboardButton = KeyboardButton(text=TEXT_BUTTON_1)
button_2: KeyboardButton = KeyboardButton(text=TEXT_BUTTON_2)

# Создаем объект клавиатуры, добавляя в него кнопки
keyboard: ReplyKeyboardMarkup = ReplyKeyboardMarkup(
    keyboard=[[button_1, button_2]],
    resize_keyboard=True
)


# Этот хэндлер будет срабатывать на команду "/start"
@dp.message(Command(commands=["start"]))
async def process_start_command(message: Message):
    await message.answer(
        START_MESSAGE,
        reply_markup=keyboard
    )


# Этот хэндлер будет срабатывать на команду "/help"
@dp.message(Command(commands=['help']))
async def process_help_command(message: Message):
    await message.answer(HELP_MESSAGE)


# Этот хэндлер будет срабатывать на просьбу забронировать место и удалять клавиатуру
@dp.message(F.text == TEXT_BUTTON_1)
async def process_dog_answer(message: Message):
    available_options = get_booking_options()
    if len(available_options) > 0:
        for one_day in available_options:
            day_str = one_day.strftime("%d/%m/%Y")
            print(f"{day_str}")
            # Добавить inline-кнопку с датой

        await message.reply(
            text='Сейчас посмотрим, что я могу Вам предложить...',
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await message.reply(
            text='К сожалению, все места заняты 😢',
            reply_markup=ReplyKeyboardRemove()
        )


if __name__ == '__main__':
    dp.run_polling(bot)


def run_bot():
    print("Запускаю бота...")
    dp.run_polling(bot)