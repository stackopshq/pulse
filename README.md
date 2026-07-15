# Pulse

> Outil de veille informationnelle self-hosted pour les équipes IT.

Pulse agrège des flux RSS/Atom, centralise les articles dans une base unique et
offre une interface web pour lire, filtrer, catégoriser et suivre sa veille en
équipe. Les sources et catégories sont partagées ; l'état de lecture (lu/non-lu,
favoris) est propre à chaque utilisateur.

## Fonctionnalités

**v0.1 — MVP**
- Authentification multi-utilisateur (sessions par cookie, mots de passe hachés).
- Gestion des sources RSS/Atom, organisées par catégories partagées.
- Collecte périodique et robuste (collecte conditionnelle `ETag`/`Last-Modified`,
  isolation des flux en erreur).
- Déduplication des articles, lecture avec marquage lu/non-lu et favoris.
- Filtres par statut, catégorie, source et recherche plein texte.
- Import / export OPML.

**v0.2 — Alertes & digests**
- Règles de veille par mots-clés (ex. `CVE`, `kubernetes`) : chaque article
  correspondant déclenche une alerte, visible dans une vue dédiée avec badge.
- Digest périodique (jour / semaine) des nouveaux articles et alertes :
  aperçu web, export Markdown, CLI et envoi par email (SMTP optionnel).

Voir [`CAHIER-DES-CHARGES.md`](CAHIER-DES-CHARGES.md) pour le périmètre complet
et la feuille de route (notifications Slack, résumés LLM, sources non-RSS…).

## Stack

Python 3.12, FastAPI, SQLModel (PostgreSQL), Jinja2 + HTMX, feedparser + httpx,
APScheduler. Déploiement via Docker.

## Démarrage avec Docker (recommandé)

```bash
cp .env.example .env
# Générer une clé secrète :
python -c "import secrets; print('PULSE_SECRET_KEY=' + secrets.token_hex(32))"
# (reporter la valeur dans .env)

docker compose up --build
```

L'application est disponible sur http://localhost:8000. Le premier compte créé
via `/register` est administrateur.

## Développement local

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Base de données : PostgreSQL (ou SQLite pour un essai rapide) via PULSE_DATABASE_URL.
export PULSE_DATABASE_URL="sqlite:///./pulse.db"
export PULSE_SECRET_KEY="dev-secret"

pulse serve --reload
```

### Commandes CLI

```bash
pulse serve [--host --port --reload]   # démarre le serveur web
pulse collect                          # lance une collecte immédiate
pulse digest [--period day|week] [--send]   # génère (ou envoie) le digest
pulse createuser --email … --name … --password … [--admin]
```

## Tests

```bash
pytest -q
```

## Configuration

Toutes les variables sont préfixées par `PULSE_` (voir `.env.example`) :
`PULSE_DATABASE_URL`, `PULSE_SECRET_KEY`, `PULSE_FETCH_INTERVAL_MINUTES`,
`PULSE_REQUEST_TIMEOUT`, `PULSE_MAX_CONCURRENT_FETCHES`, `PULSE_DEBUG`.

## Licence

MIT.
