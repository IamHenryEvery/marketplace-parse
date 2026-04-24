import argparse
import asyncio

from sqlalchemy import select

from marketplace_parse.core.security import hash_password
from marketplace_parse.db.enums import UserRole
from marketplace_parse.db.models import User
from marketplace_parse.db.session import async_session_maker


async def bootstrap_admin(email: str, password: str) -> None:
    async with async_session_maker() as session:
        existing = await session.scalar(select(User).where(User.email == email))
        if existing is not None:
            print(f"user with email {email!r} already exists (user_id={existing.user_id}, role={existing.role.value})")
            return

        user = User(
            email=email,
            password_hash=hash_password(password),
            role=UserRole.admin,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        print(f"created admin user_id={user.user_id} email={user.email}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the first admin user.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    asyncio.run(bootstrap_admin(args.email, args.password))


if __name__ == "__main__":
    main()
