#!/usr/bin/env python3
"""
SANS PMS — Add User Script
Run inside the backend container to create a new system user
and link them to Telegram for bot access.

Usage:
    docker compose exec backend python scripts/add_user.py \\
        --email engineer@sans-intl.com \\
        --name "Ahmed Ali" \\
        --name-ar "أحمد علي" \\
        --password "TempPass123!" \\
        --role site_engineer \\
        --telegram-id 123456789
"""
import argparse
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from core.security import hash_password
from core.config import settings
from models.user import User, Role


def main():
    parser = argparse.ArgumentParser(description="Add a new SANS PMS user")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True, help="Full name (English)")
    parser.add_argument("--name-ar", help="Full name (Arabic)")
    parser.add_argument("--password", required=True)
    parser.add_argument("--role", required=True,
                         help="Role name: super_admin, project_director, planning_manager, "
                              "commercial_manager, project_manager, site_engineer, "
                              "quantity_surveyor, store_keeper, employee, managing_director")
    parser.add_argument("--telegram-id", type=int, help="Telegram user ID (optional, links bot access)")
    parser.add_argument("--phone")
    args = parser.parse_args()

    engine = create_engine(settings.DATABASE_SYNC_URL)
    with Session(engine) as session:
        role = session.execute(
            select(Role).where(Role.name == args.role)
        ).scalar_one_or_none()

        if not role:
            print(f"❌ Role '{args.role}' not found. Available roles:")
            all_roles = session.execute(select(Role.name)).scalars().all()
            for r in all_roles:
                print(f"   - {r}")
            sys.exit(1)

        existing = session.execute(
            select(User).where(User.email == args.email)
        ).scalar_one_or_none()
        if existing:
            print(f"❌ User with email {args.email} already exists.")
            sys.exit(1)

        user = User(
            company_id=role.company_id,
            role_id=role.id,
            email=args.email,
            password_hash=hash_password(args.password),
            full_name=args.name,
            full_name_ar=args.name_ar,
            phone=args.phone,
            telegram_id=args.telegram_id,
            status="active",
            must_change_password=True,
        )
        session.add(user)
        session.commit()

        print(f"✅ User created successfully:")
        print(f"   Email: {user.email}")
        print(f"   Role:  {role.name} ({role.name_ar})")
        print(f"   Telegram linked: {'Yes (' + str(args.telegram_id) + ')' if args.telegram_id else 'No'}")
        print(f"\n⚠️  User must change password on first login.")


if __name__ == "__main__":
    main()
