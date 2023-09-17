from entities import *
import yaml
import bot

""" Получаем данные из файла настроек """
with open('settings.yml', 'r') as file:
    CONSTANTS = yaml.safe_load(file)

parking_spots = CONSTANTS['PARKING_SPOTS']
db_name = CONSTANTS['DB_NAME']

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

if os.path.isfile(db_name):
    data = {}

    query = Role.select()
    for obj in query:
        data["all_roles_obj"] = obj

    query = User.select()
    for obj in query:
        data["all_users_obj"] = obj

    query = ParkingSpot.select()
    for obj in query:
        data["all_spots_obj"] = obj
else:
    create_tables()

    # Добавляем записи в БД:
    all_roles_obj = load_roles(all_roles_names)
    all_users_obj = load_users(all_users, all_roles_obj)
    all_spots_obj = load_spots(parking_spots)
    data = {
        "all_roles_obj": all_roles_obj,
        "all_users_obj": all_users_obj,
        "all_spots_obj": all_spots_obj
    }

bot.run_bot(data)
