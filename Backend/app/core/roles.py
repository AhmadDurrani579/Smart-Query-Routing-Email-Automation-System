from enum import Enum


class UserRole(str, Enum):
    STUDENT = "STUDENT"
    HOD = "HOD"
    EXAM_STAFF = "EXAM_STAFF"
    FINANCE_STAFF = "FINANCE_STAFF"
    IT_STAFF = "IT_STAFF"
    ADMIN = "ADMIN"


PUBLIC_SIGNUP_ROLES = {
    UserRole.STUDENT,
    UserRole.HOD,
    UserRole.EXAM_STAFF,
    UserRole.FINANCE_STAFF,
    UserRole.IT_STAFF,
}

DEPARTMENT_STAFF_ROLES = {
    UserRole.EXAM_STAFF,
    UserRole.FINANCE_STAFF,
    UserRole.IT_STAFF,
}

STAFF_ROLES = DEPARTMENT_STAFF_ROLES | {UserRole.HOD}

REPLY_ROLES = STAFF_ROLES | {UserRole.ADMIN}