from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import or_, select

from marketplace_parse.api.deps import CurrentUser
from marketplace_parse.api.schemas import UpdateUserRoleRequest, UserAdminOut
from marketplace_parse.db.enums import UserRole
from marketplace_parse.db.models import RoleChangeAudit, User
from marketplace_parse.db.session import async_session_maker


router = APIRouter()


def _ensure_admin(user: User) -> None:
    if user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для администраторов",
        )


@router.get("/admin/users", response_model=list[UserAdminOut])
async def list_users(user: User = CurrentUser) -> list[UserAdminOut]:
    _ensure_admin(user)
    async with async_session_maker() as session:
        result = await session.execute(select(User).order_by(User.user_id))
        return [UserAdminOut.model_validate(u) for u in result.scalars()]


@router.patch("/admin/users/{user_id}/role", response_model=UserAdminOut)
async def update_user_role(
    user_id: int,
    body: UpdateUserRoleRequest,
    user: User = CurrentUser,
) -> UserAdminOut:
    _ensure_admin(user)
    if user_id == user.user_id:
        raise HTTPException(status_code=400, detail="Нельзя менять роль самому себе")

    async with async_session_maker() as session:
        target = await session.get(User, user_id)
        if target is None:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        if target.role == body.role:
            return UserAdminOut.model_validate(target)

        old_role = target.role
        target.role = body.role
        session.add(
            RoleChangeAudit(
                target_user_id=target.user_id,
                changed_by_id=user.user_id,
                old_role=old_role,
                new_role=body.role,
            )
        )
        await session.commit()
        await session.refresh(target)
        return UserAdminOut.model_validate(target)


@router.delete("/admin/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, user: User = CurrentUser) -> Response:
    _ensure_admin(user)
    if user_id == user.user_id:
        raise HTTPException(status_code=400, detail="Нельзя удалить самого себя")

    async with async_session_maker() as session:
        target = await session.get(User, user_id)
        if target is None:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        audit_q = await session.execute(
            select(RoleChangeAudit).where(
                or_(
                    RoleChangeAudit.target_user_id == user_id,
                    RoleChangeAudit.changed_by_id == user_id,
                )
            )
        )
        for row in audit_q.scalars():
            await session.delete(row)

        await session.delete(target)
        await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
