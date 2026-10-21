
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.department import Department
from sqlalchemy import func


def get_all_departments(db: Session):
    statement = (
        select(Department)
        .where(Department.is_active.is_(True))
        .order_by(Department.name)
    )

    return db.scalars(statement).all()


def get_department_by_id(
    db: Session,
    department_id: int
):
    statement = (
        select(Department)
        .where(
            Department.id == department_id,
            Department.is_active.is_(True)
        )
    )

    return db.scalar(statement)


def get_department_by_code(db: Session, code: str):
    statement = select(Department).where(
        func.lower(Department.code) == code.lower()
    )
    return db.scalar(statement)


def create_department(db: Session, data):
    department = Department(
        name=data.name,
        code=data.code.upper(),
        description=data.description,
        keywords=data.keywords,
        is_active=True
    )

    db.add(department)
    db.commit()
    db.refresh(department)

    return department


def get_department_for_update(
    db: Session,
    department_id: int
):
    return db.get(Department, department_id)


def save_department(db: Session, department: Department):
    db.add(department)
    db.commit()
    db.refresh(department)
    return department
