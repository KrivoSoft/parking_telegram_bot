from entities import *
import yaml
import bot

# Получаем данные из файла настроек
with open('settings.yml', 'r') as file:
    CONSTANTS = yaml.safe_load(file)

parking_spots = CONSTANTS['PARKING_SPOTS']
roles = list(CONSTANTS["USERS"])
# Договоримся, что первый элемент в списке - пользователи, которые могут выгружать отчёты
auditor_role_name = list(CONSTANTS["USERS"])[0]
auditors_usernames = CONSTANTS["USERS"][auditor_role_name]

# Договоримся, что второй элемент в списке - обычные пользователи
client_role_name = list(CONSTANTS["USERS"])[1]
clients_usernames = CONSTANTS["USERS"][client_role_name]


if is_db_created():
    parking_spots_obj = []
    query = ParkingSpot.select()
    for obj in query:
        parking_spots_obj.append(obj)
else:
    create_tables()

    # Добавляем записи в БД:
    roles_list_obj = add_roles(roles)
    auditors_list_obj = add_users(auditors_usernames, roles_list_obj[0])
    clients_list_obj = add_users(clients_usernames, roles_list_obj[1])
    parking_spots_obj = create_spots(parking_spots)

bot.run_bot(parking_spots_obj)
