from peewee import *
import os
import yaml

# Получаем данные из файла настроек
with open('settings.yml', 'r') as file:
    CONSTANTS = yaml.safe_load(file)

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
