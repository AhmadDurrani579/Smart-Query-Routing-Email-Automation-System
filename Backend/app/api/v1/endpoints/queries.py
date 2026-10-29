
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)

from sqlalchemy.orm import Session
from app.repositories.query_repository import get_department_queries
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.query import (
    QueryCreate,
    QueryResponse
)
from app.services.query_service import submit_student_query
from app.services.query_service import get_query_details
from app.schemas.query_message import (
    QueryReplyCreate,
    QueryMessageResponse
)
from app.repositories.query_repository import get_student_queries
from app.services.query_service import (
    reply_to_query,
    get_query_conversation
)
from app.schemas.query import QueryStatusUpdate
from app.services.query_service import update_query_status
from app.repositories.query_escalation_repository import (
    get_escalated_queries,
    get_query_escalation_history,
)

from app.schemas.query_escalation import (
    EscalatedQueryResponse,
    EscalationHistoryResponse,
)
from sqlalchemy import select
from app.models.department import Department

router = APIRouter(
    prefix="/queries",
    tags=["Student Queries"]
)


@router.post(
    "",
    response_model=QueryResponse,
    status_code=status.HTTP_201_CREATED
)
def submit_query(
    data: QueryCreate,
    current_user: Annotated[
        User, Depends(get_current_user)
    ],
    db: Annotated[Session, Depends(get_db)]
):

    if current_user.role != "STUDENT":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can submit queries"
        )

    return submit_student_query(
        db=db,
        student_id=current_user.id,
        message=data.message
    )


@router.post(
    "/{query_id}/reply",
    response_model=QueryMessageResponse,
    status_code=status.HTTP_201_CREATED
)
def submit_query_reply(
    query_id: int,
    data: QueryReplyCreate,
    current_user: Annotated[
        User, Depends(get_current_user)
    ],
    db: Annotated[Session, Depends(get_db)]
):
    return reply_to_query(
        db=db,
        query_id=query_id,
        current_user=current_user,
        message=data.message
    )


@router.get(
    "/{query_id}/messages",
    response_model=list[QueryMessageResponse]
)
def list_query_messages(
    query_id: int,
    current_user: Annotated[
        User, Depends(get_current_user)
    ],
    db: Annotated[Session, Depends(get_db)]
):
    return get_query_conversation(
        db=db,
        query_id=query_id,
        current_user=current_user
    )



# 1. Student query history

@router.get(
    "/my",
    response_model=list[QueryResponse]
)
def list_my_queries(
    current_user: Annotated[
        User, Depends(get_current_user)
    ],
    db: Annotated[Session, Depends(get_db)]
):
    if current_user.role != "STUDENT":
        raise HTTPException(
            status_code=403,
            detail="Only students can view their query history"
        )

    # 1. Get only the logged-in student's queries
    queries = get_student_queries(
        db=db,
        student_id=current_user.id
    )

    # 2. Collect department IDs
    department_ids = {
        query.department_id
        for query in queries
        if query.department_id is not None
    }

    # 3. Look up department names
    department_names = {}

    if department_ids:
        departments = db.scalars(
            select(Department).where(
                Department.id.in_(department_ids)
            )
        ).all()

        department_names = {
            department.id: department.name
            for department in departments
        }

    # 4. Return queries with department names
    return [
        {
            **QueryResponse.model_validate(query).model_dump(),
            "department_name": department_names.get(
                query.department_id
            )
        }
        for query in queries
    ]


# 2. Department query listing
@router.get(
    "/department",
    response_model=list[QueryResponse]
)
def list_department_queries(
    current_user: Annotated[
        User, Depends(get_current_user)
    ],
    db: Annotated[Session, Depends(get_db)]
):
    if current_user.role not in {"EXAM_STAFF", "IT_STAFF", "FINANCE_STAFF", "HOD"}:
        raise HTTPException(
            status_code=403,
            detail="Only department staff can view department queries"
        )

    if current_user.department_id is None:
        raise HTTPException(
            status_code=403,
            detail="No department assigned to your account"
        )

    return get_department_queries(
        db=db,
        department_id=current_user.department_id
    )



@router.patch(
    "/{query_id}/status",
    response_model=QueryResponse
)
def change_query_status(
    query_id: int,
    data: QueryStatusUpdate,
    current_user: Annotated[
        User, Depends(get_current_user)
    ],
    db: Annotated[Session, Depends(get_db)]
):
    return update_query_status(
        db=db,
        query_id=query_id,
        current_user=current_user,
        new_status=data.status
    )


@router.get(
    "/escalated",
    response_model=list[EscalatedQueryResponse]
)
def list_escalated_queries(
    current_user: Annotated[
        User, Depends(get_current_user)
    ],
    db: Annotated[Session, Depends(get_db)],
    include_resolved: bool = False,
):
    if current_user.role not in {"HOD", "ADMIN"}:
        raise HTTPException(
            status_code=403,
            detail="Only HOD or Admin can view escalations"
        )

    return get_escalated_queries(
        db=db,
        hod_id=(
            current_user.id
            if current_user.role == "HOD"
            else None
        ),
        include_resolved=include_resolved,
    )

# 3. Individual query details — after static paths
@router.get(
    "/{query_id}",
    response_model=QueryResponse
)
def get_single_query(
    query_id: int,
    current_user: Annotated[
        User, Depends(get_current_user)
    ],
    db: Annotated[Session, Depends(get_db)]
):
    return get_query_details(
        db=db,
        query_id=query_id,
        current_user=current_user
    )


@router.get(
    "/{query_id}/escalations",
    response_model=list[EscalationHistoryResponse]
)
def list_query_escalations(
    query_id: int,
    current_user: Annotated[
        User, Depends(get_current_user)
    ],
    db: Annotated[Session, Depends(get_db)]
):
    # Reuse existing access control.
    get_query_details(
        db=db,
        query_id=query_id,
        current_user=current_user
    )

    return get_query_escalation_history(
        db=db,
        query_id=query_id
    )
