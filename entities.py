from peewee import *
import os
import yaml
from datetime import datetime, timedelta, date

# Получаем данные из файла настроек
with open('settings.yml', 'r') as file:
    CONSTANTS = yaml.safe_load(file)

reservation_period_days = CONSTANTS['RESERVATION_PERIOD_DAYS']
db_name = CONSTANTS['DB_NAME']
db = SqliteDatabase(db_name)

""" Сущности, описывающие хранимые в БД записи """


class BaseModel(Model):
    class Meta:
        database = db


class ParkingSpot(BaseModel):
    name = CharField()

    class Meta:
        table_name = 'parking_spots'

    def __repr__(self):
        return self.name

    def get_name(self):
        return self.name


class Reservation(BaseModel):
    booking_date = DateField()
    username = CharField()
    parking_spot_id = ForeignKeyField(ParkingSpot, backref='parking_spot_id')

    class Meta:
        table_name = 'reservations'

    def __repr__(self):
        return self.booking_date

    def get_date(self):
        return self.booking_date


def create_tables():
    """ Создание таблиц при создании новой БД """
    db.connect()
    db.create_tables([ParkingSpot, Reservation])


def create_spots(spots_list):
    """ Запись в БД информации из конфига по доступным парковочным местам"""
    spots_obj_array = []

    for one in spots_list:
        spot_obj = ParkingSpot(name=one)
        spots_obj_array.append(spot_obj)
        spot_obj.save()

    return spots_obj_array


def create_reservation(spot, date, username):
    """ Создание новой записи в БД о бронировании парковочного места """
    new_reservation = Reservation.create(parking_spot_id=spot, booking_date=date, username=username)
    new_reservation.save()


def is_db_created():
    """ Проверка есть ли база данных sqlite в текущем каталоге """
    if os.path.isfile(db_name):
        return True
    else:
        return False


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