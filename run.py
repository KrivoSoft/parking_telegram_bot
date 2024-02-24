from entities import *
import yaml
import bot
import os

""" Получаем данные из файла настроек """
with open('settings.yml', 'r') as file:
    CONSTANTS = yaml.safe_load(file)

parking_spots = CONSTANTS['PARKING_SPOTS']
db_name = CONSTANTS['DB_NAME']


def create_tables() -> None:
    """ Создание таблиц при создании новой БД """
    db.connect()
    db.create_tables([ParkingSpot, Reservation, User, Role, Guest])


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

if not os.path.isfile(db_name):
    create_tables()
    all_roles_obj = Role.load_roles(all_roles_names)
    all_users_obj = User.load_users(all_users)
    all_spots_obj = ParkingSpot.load_spots(parking_spots)
    data = {
        "all_roles_obj": all_roles_obj,
        "all_users_obj": all_users_obj,
        "all_spots_obj": all_spots_obj
    }
bot.run_bot()
