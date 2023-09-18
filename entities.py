from typing import Optional

from peewee import *
import os
import yaml
from datetime import timedelta, date

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


class Role(BaseModel):
    name = CharField()

    class Meta:
        table_name = 'roles'

    def __repr__(self):
        return self.name


class User(BaseModel):
    username = CharField(null=True)
    first_name = CharField(null=True)
    last_name = CharField(null=True)
    role_id = ForeignKeyField(Role, backref="role_id")

    class Meta:
        table_name = 'users'

    def __repr__(self):
        return self.username


class Reservation(BaseModel):
    booking_date = DateField()
    user_id = ForeignKeyField(User, backref="username_id")
    parking_spot_id = ForeignKeyField(ParkingSpot, backref='parking_spot_id')

    class Meta:
        table_name = 'reservations'

    def __repr__(self):
        return self.booking_date

    def get_date(self):
        return self.booking_date


def create_tables() -> None:
    """ Создание таблиц при создании новой БД """
    db.connect()
    db.create_tables([ParkingSpot, Reservation, User, Role])


def load_spots(spots_list: list) -> list:
    """ Запись в БД информации из конфига по доступным парковочным местам"""
    spots_obj_array = []

    for one in spots_list:
        spot_obj = ParkingSpot(name=one)
        spots_obj_array.append(spot_obj)
        spot_obj.save()

    return spots_obj_array


def create_reservation(spot_id: int, date: str, user: User) -> None:
    """ Создание новой записи в БД о бронировании парковочного места """
    new_reservation = Reservation.create(parking_spot_id=spot_id, booking_date=date, user_id=user.id)
    new_reservation.save()


def get_user_by_username(username: str) -> Optional[User]:
    """ Функция, возвращающая нужного пользователя по username из БД> """
    query = User.select()

    for user in query:
        if user.username == username:
            return user
    return None


def get_user_by_name(first_name: str, last_name: str) -> Optional[User]:
    """ Функция, возвращающая нужного пользователя по имени и фамилии из БД """
    query = User.select()

    for user in query:
        if user.first_name == first_name:
            if user.last_name == last_name:
                return user
    return None


def is_spot_free(checking_spot: ParkingSpot, checking_date) -> bool:
    """ Проверка свободно ли парковочное место на определённую дату """
    check_query = Reservation.select().where(
        Reservation.booking_date == checking_date,
        Reservation.parking_spot_id == checking_spot.id
    )
    if len(check_query) == 0:
        return True
    else:
        return False


def get_parking_spot_by_name(spot_name: str, all_spots: list) -> ParkingSpot or None:
    check_query = ParkingSpot.select().where(
        ParkingSpot.name == spot_name
    )
    if len(check_query) == 0:
        return None
    else:
        for one_spot in all_spots:
            if one_spot.name == spot_name:
                return one_spot


def get_booking_options() -> dict:
    """ Получаем доступные для бронирования варианты """
    current_date = date.today()

    # Получаем даты, начиная с завтрашнего дня, на которые можно бронировать парковочные места
    parking_reservation_date_range = []
    for i in range(1, reservation_period_days + 1):
        one_date = current_date + timedelta(days=i)
        parking_reservation_date_range.append(one_date)

    available_dates_for_book = {}
    all_spots = ParkingSpot.select()

    for one_date in parking_reservation_date_range:
        available_dates_for_book[one_date] = []
        for one_spot in all_spots:
            if is_spot_free(one_spot, one_date):
                available_dates_for_book[one_date].append(one_spot.name)

    # Удаляем из словаря все даты, для которых нет свободных мест
    available_dates_for_book = {key: value for key, value in available_dates_for_book.items() if value}

    return available_dates_for_book


def load_roles(roles_list: list) -> list:
    """ Запись в БД информации по аудиторам"""
    auditors_obj_array = []

    for one in roles_list:
        role_obj = Role(name=one)
        auditors_obj_array.append(role_obj)
        role_obj.save()

    return auditors_obj_array


def load_users(users: list[dict], roles: list[Role]) -> list:
    users_list_obj = []

    for user_data in users:
        for role in roles:
            if user_data["role"] == role.name:
                user_obj = User.create(
                    username=user_data["username"],
                    first_name=user_data["first_name"],
                    last_name=user_data["last_name"],
                    role_id=role.id)
                users_list_obj.append(user_obj)
                user_obj.save()

    return users_list_obj
