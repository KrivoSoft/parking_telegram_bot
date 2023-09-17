from entities import *
import yaml
import bot

""" Получаем данные из файла настроек """
with open('settings.yml', 'r') as file:
    CONSTANTS = yaml.safe_load(file)

parking_spots = CONSTANTS['PARKING_SPOTS']

""" Подгружаем названия ролей """
administrator_role_name = "ADMINISTRATOR"
auditor_role_name = "AUDITOR"
client_role_name = "CLIENT"
all_roles_names = [
    administrator_role_name,
    auditor_role_name,
    client_role_name
]

all_users = CONSTANTS["USERS"]

if is_db_created():
    parking_spots_obj = []
    query = ParkingSpot.select()
    for obj in query:
        parking_spots_obj.append(obj)
else:
    create_tables()

    # Добавляем записи в БД:
    all_roles_obj = load_roles(all_roles_names)
    all_users_obj = load_users(all_users, all_roles_obj)
    parking_spots_obj = load_spots(parking_spots)

bot.run_bot(parking_spots_obj)
