from aiogram import Bot, Dispatcher, executor, types
import yaml

# Получаем данные из файла настроек
with open('settings.yml', 'r') as file:
    CONSTANTS = yaml.safe_load(file)
API_TOKEN = CONSTANTS['API_TOKEN']

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)


@dp.message_handler(commands=['start'])  # Явно указываем в декораторе, на какую команду реагируем.
async def send_welcome(message: types.Message):
    await message.reply("Привет!\nЯ бот для бронирования парковки\nОтправь мне любое сообщение.")


@dp.message_handler() #Создаём новое событие, которое запускается в ответ на любой текст, введённый пользователем.
async def echo(message: types.Message): #Создаём функцию с простой задачей — отправить обратно текст.
    await message.answer("Hello")


def run_bot():
    print("Запускаю бота...")
    executor.start_polling(dp, skip_updates=True)