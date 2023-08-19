from entities import *
import yaml
import bot

# Получаем данные из файла настроек
with open('settings.yml', 'r') as file:
    CONSTANTS = yaml.safe_load(file)

parking_spots = CONSTANTS['PARKING_SPOTS']


if is_db_created():
    print("База данных уже есть.")

    parking_spots_obj = []
    query = ParkingSpot.select()
    for obj in query:
        parking_spots_obj.append(obj)
else:
    print("Базы данных нет. Создаю...")
    create_tables()
    parking_spots_obj = create_spots(parking_spots)
    print("Записал в базу парковочные места.")

bot.run_bot()
