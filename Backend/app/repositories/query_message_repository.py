
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.query_message import QueryMessage


def create_reply(
    db: Session,
    query_id: int,
    sender_id: int,
    message: str
) -> QueryMessage:

    reply = QueryMessage(
        query_id=query_id,
        sender_id=sender_id,
        message=message
    )

    db.add(reply)
    db.flush()

    return reply


def get_query_messages(
    db: Session,
    query_id: int
) -> list[QueryMessage]:

    statement = (
        select(QueryMessage)
        .where(QueryMessage.query_id == query_id)
        .order_by(
            QueryMessage.created_at.asc(),
            QueryMessage.id.asc()
        )
    )

    return list(db.scalars(statement).all())
