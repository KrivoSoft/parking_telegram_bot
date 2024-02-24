from __future__ import annotations
from typing import Optional
import peewee
import yaml
from datetime import date
from peewee import *

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

    def is_spot_free(self, checking_date) -> bool:
        """ Проверка свободно ли парковочное место на определённую дату """

        check_query = Reservation.select().where(
            Reservation.booking_date == checking_date,
            Reservation.parking_spot_id == self.id
        )

        if len(check_query) == 0:
            return True
        else:
            return False

    @staticmethod
    def get_booking_options(date_for_book: date) -> list[ParkingSpot]:
        """ Функция, получающая доступные для бронирования варианты """

        available_spots_for_book = []
        all_spots = ParkingSpot.select()

        for one_spot in all_spots:
            if one_spot.is_spot_free(date_for_book):
                available_spots_for_book.append(one_spot)

        return available_spots_for_book

    @staticmethod
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
    telegram_id = IntegerField(null=False)

    class Meta:
        table_name = 'users'

    def __repr__(self):
        return f"User: {self.username} {self.last_name} {self.first_name}"

    def __str__(self):
        return f"User: {self.id} {self.username} {self.last_name} {self.first_name}"

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
                        role_id=role.id,
                        telegram_id=user_data["telegram_id"]
                    )
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

    @staticmethod
    def get_all_users() -> Optional[list[str]]:
        users_obj: peewee.ModelSelect = User.select()
        users_str = []
        for user in users_obj:
            users_str.append(str(user))
        return users_str

    @staticmethod
    def delete_user_by_id(user_id: int) -> bool:
        is_success = True

        try:
            user = User.get(User.id == user_id)
            user.delete_instance()
        except Exception:
            is_success = False

        return is_success

    @staticmethod
    def get_user_by_id(the_user_id_i_want: int) -> Optional[User]:
        """ Функция, возвращающая нужного пользователя по его telegram id из БД """
        query: peewee.ModelSelect = User.select().where(User.telegram_id == the_user_id_i_want)

        if len(query) == 0:
            return None
        else:
            return query[0]

    @staticmethod
    def get_user_role(user_telegram_id) -> Optional[str]:
        user = User.get_user_by_id(user_telegram_id)
        if user is None:
            return None
        return user.role_id.name


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

    def create_reservation(spot_id: int, date: str, user: User) -> None:
        """ Создание новой записи в БД о бронировании парковочного места """
        new_reservation = Reservation.create(parking_spot_id=spot_id, booking_date=date, user_id=user.id)
        new_reservation.save()


class Guest(BaseModel):
    username = CharField(null=True)
    first_name = CharField(null=True)
    last_name = CharField(null=True)
    telegram_id = IntegerField(null=False)

    class Meta:
        table_name = 'guests'

    def __repr__(self):
        return " ".join([str(self.username), str(self.first_name), str(self.last_name)])

    def __str__(self):
        return " ".join([str(self.username), str(self.first_name), str(self.last_name)])

    def delete_guest(self) -> bool:
        is_success = True

        try:
            guest = Guest.get(Guest.id == self.id)
            guest.delete_instance()
        except Exception:
            is_success = False

        return is_success
