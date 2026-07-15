"""Interface en ligne de commande de Pulse."""

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pulse", description="Outil de veille IT Pulse")
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="Démarre le serveur web")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")

    sub.add_parser("collect", help="Lance une collecte immédiate des flux")

    createuser = sub.add_parser("createuser", help="Crée un utilisateur")
    createuser.add_argument("--email", required=True)
    createuser.add_argument("--name", required=True)
    createuser.add_argument("--password", required=True)
    createuser.add_argument("--admin", action="store_true")

    args = parser.parse_args(argv)

    if args.command == "serve":
        import uvicorn

        uvicorn.run("pulse.main:app", host=args.host, port=args.port, reload=args.reload)
        return 0

    if args.command == "collect":
        from .db import init_db
        from .feeds import collect_all

        init_db()
        result = collect_all()
        print(f"{result['new_articles']} nouveaux articles sur {result['sources']} sources.")
        return 0

    if args.command == "createuser":
        from sqlmodel import Session, select

        from .db import engine, init_db
        from .models import User
        from .security import hash_password

        init_db()
        email = args.email.strip().lower()
        with Session(engine) as session:
            if session.exec(select(User).where(User.email == email)).first() is not None:
                print(f"L'utilisateur {email} existe déjà.", file=sys.stderr)
                return 1
            session.add(
                User(
                    email=email,
                    name=args.name,
                    password_hash=hash_password(args.password),
                    is_admin=args.admin,
                )
            )
            session.commit()
        print(f"Utilisateur {email} créé.")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
