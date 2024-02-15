from typing import Optional

from peewee import *
import yaml
from datetime import timedelta, date, datetime
from aiogram.types import Message

# Получаем данные из файла настроек
with open('settings.yml', 'r') as file:
    CONSTANTS = yaml.safe_load(file)

reservation_period_days = CONSTANTS['RESERVATION_PERIOD_DAYS']
db_name = CONSTANTS['DB_NAME']
db = SqliteDatabase(db_name)

TODAY_DEADLINE_CLOCK_FOR_CLIENTS = CONSTANTS["TODAY_DEADLINE_CLOCK_FOR_CLIENTS"]
TODAY_DEADLINE_CLOCK_FOR_AUDITORS = CONSTANTS["TODAY_DEADLINE_CLOCK_FOR_AUDITORS"]

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

    @staticmethod
    def load_spots(spots_list: list) -> list:
        """ Функция загрузки парковочных мест из конфига"""
        spots_obj_array = []

        for one in spots_list:
            spot_obj = ParkingSpot(name=one)
            spots_obj_array.append(spot_obj)
            spot_obj.save()

        return spots_obj_array


class Role(BaseModel):
    name = CharField()

    class Meta:
        table_name = 'roles'

    def __repr__(self):
        return self.name

    @staticmethod
    def load_roles(roles_list: list) -> list:
        """ Запись в БД информации по ролям """
        roles_obj_array = []

        for one in roles_list:
            role_obj = Role(name=one)
            roles_obj_array.append(role_obj)
            role_obj.save()

        return roles_obj_array


class User(BaseModel):
    username = CharField(null=True)
    first_name = CharField(null=True)
    last_name = CharField(null=True)
    role_id = ForeignKeyField(Role, backref="role_id")


    class Meta:
        table_name = 'users'

    def __repr__(self):
        return f"User: {self.username} {self.last_name} {self.first_name}"

    @staticmethod
    def load_users(users: list[dict]) -> list:
        """ Функция загрузки пользователей из конфига """
        users_list_obj = []
        roles = Role.select()

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

    @staticmethod
    def add_user(username: str, first_name: str, last_name: str, role_id: int):
        if username is not None:
            User.create(
                username=username,
                first_name=first_name,
                last_name=last_name,
                role_id=Role.select().where(Role.id == role_id)
            )


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


class Guest(BaseModel):
    username = CharField(null=True)
    first_name = CharField(null=True)
    last_name = CharField(null=True)

    class Meta:
        table_name = 'guests'

    def __repr__(self):
        return " ".join([str(self.username), str(self.first_name), str(self.last_name)])

    def __str__(self):
        return " ".join([str(self.username), str(self.first_name), str(self.last_name)])


def create_tables() -> None:
    """ Создание таблиц при создании новой БД """
    db.connect()
    db.create_tables([ParkingSpot, Reservation, User, Role, Guest])


def create_reservation(spot_id: int, date: str, user: User) -> None:
    """ Создание новой записи в БД о бронировании парковочного места """
    new_reservation = Reservation.create(parking_spot_id=spot_id, booking_date=date, user_id=user.id)
    new_reservation.save()


def get_user_by_username(username: str) -> Optional[User]:
    """ Функция, возвращающая нужного пользователя по username из БД> """
    if username == "":
        return None
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


def get_parking_spot_by_name(spot_name: str, all_spots: list[ParkingSpot]) -> Optional[ParkingSpot]:
    check_query = ParkingSpot.select().where(
        ParkingSpot.name == spot_name
    )
    if len(check_query) == 0:
        return None
    else:
        for one_spot in all_spots:
            if one_spot.name == spot_name:
                return one_spot


def get_booking_options(date_for_book: date) -> list[ParkingSpot]:
    """ Функция, получающая доступные для бронирования варианты """

    available_spots_for_book = []
    all_spots = ParkingSpot.select()

    for one_spot in all_spots:
        if is_spot_free(one_spot, date_for_book):
            available_spots_for_book.append(one_spot)

    return available_spots_for_book


def get_user_role(message: Message) -> Optional[str]:
    name_user = message.from_user.username
    if (name_user is None) or (name_user == ""):
        first_name = message.from_user.first_name
        last_name = message.from_user.last_name
        user = get_user_by_name(first_name, last_name)
    else:
        user = get_user_by_username(name_user)
    if user is None:
        return None
    return user.role_id.name
