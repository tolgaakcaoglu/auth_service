import argparse

from app import crud
from app.db import SessionLocal


def main() -> int:
    parser = argparse.ArgumentParser(description="Create service and API key")
    parser.add_argument("--name", required=True, help="Service name")
    parser.add_argument("--domain", default=None, help="Service domain")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        service = crud.get_service_by_name(db, args.name)
        if not service:
            service = crud.create_service(db, args.name, args.domain)
        api_key, db_key = crud.create_service_api_key(db, service.id)
    finally:
        db.close()

    print("service_id=", service.id)
    print("api_key=", api_key)
    print("api_key_id=", db_key.id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
