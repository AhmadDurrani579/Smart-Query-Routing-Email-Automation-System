
from enum import Enum


class UserRole(str, Enum):
    STUDENT = "STUDENT"
    INSTRUCTOR = "INSTRUCTOR"
    HOD = "HOD"
    ADMIN = "ADMIN"
