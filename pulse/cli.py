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

    digest = sub.add_parser("digest", help="Génère le digest (Markdown sur stdout)")
    digest.add_argument("--period", choices=["day", "week"], default="day")
    digest.add_argument("--send", action="store_true", help="Envoie le digest par email")

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

    if args.command == "digest":
        from datetime import datetime, timezone

        from sqlmodel import Session

        from .db import engine, init_db
        from .digest import build_digest, period_delta, render_markdown, send_digest_email

        init_db()
        since = datetime.now(timezone.utc) - period_delta(args.period)
        with Session(engine) as session:
            data = build_digest(session, since)
            markdown = render_markdown(data)
        if args.send:
            subject = f"Digest Pulse — {data['total_new']} article(s)"
            ok = send_digest_email(subject, markdown)
            print("Digest envoyé." if ok else "Envoi impossible (SMTP non configuré ?).")
        else:
            print(markdown)
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
