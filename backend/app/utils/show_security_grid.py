import json
import sys

from app.models.user import User
from app.db.session import SessionLocal


def show_security_grid(identifier: str) -> None:
    db = SessionLocal()
    try:
        user = (
            db.query(User)
            .filter((User.email == identifier.strip().lower()) | (User.name == identifier.strip()))
            .first()
        )
        if not user:
            raise SystemExit(f"User not found: {identifier}")
        grid = json.loads(user.security_grid)
        print(f"Security grid for {user.email}:")
        for key in sorted(grid.keys(), key=lambda value: int(value[1:])):
            print(f"{key}: {grid[key]}")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python -m app.utils.show_security_grid <email-or-name>")
    show_security_grid(sys.argv[1])
