from entities import *
from datetime import datetime, timedelta, date
import yaml

# Получаем данные из файла настроек
with open('settings.yml', 'r') as file:
    CONSTANTS = yaml.safe_load(file)

parking_spots = CONSTANTS['PARKING_SPOTS']
reservation_period_days = CONSTANTS['RESERVATION_PERIOD_DAYS']


def is_spot_free(checking_spot, checking_date):
    """ Проверка свободно ли парковочное место на определённую дату """
    check_query = Reservation.select().where(
        Reservation.booking_date == checking_date,
        Reservation.parking_spot_id == checking_spot.id
    )
    if len(check_query) == 0:
        return True
    else:
        return False


def get_booking_options():
    """ Получаем доступные для бронирования варианты """
    current_date = date.today()

    # Получаем даты, начиная с завтрашнего дня, на которые можно бронировать парковочные места
    parking_reservation_date_range = []
    for i in range(1, reservation_period_days + 1):
        one_date = current_date + timedelta(days=i)
        parking_reservation_date_range.append(one_date)

    available_for_book_dates = {}

    all_spots = ParkingSpot.select()

    for one_date in parking_reservation_date_range:
        available_for_book_dates[one_date] = []
        for one_spot in all_spots:
            if is_spot_free(one_spot, one_date):
                available_for_book_dates[one_date].append(one_spot.name)

    return available_for_book_dates


if is_db_created():
    print("База данных уже есть.")

    parking_spots_obj = []
    query = ParkingSpot.select()
    for obj in query:
        parking_spots_obj.append(obj)
else:
    print("Базы данных нет. Создаю...")
    create_tables()
    print("Создал.")

    parking_spots_obj = create_spots(parking_spots)
    print(f"Записал в базу парковочные места.")

print(get_booking_options())