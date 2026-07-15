# Pulse — Cahier des charges

> Outil de veille informationnelle self-hosted pour les équipes IT.

## 1. Vision

Pulse agrège des sources d'information IT (flux RSS/Atom au départ), centralise
les articles dans une base unique, et permet de les lire, filtrer, catégoriser et
recevoir des digests. Objectif : remplacer un empilement d'onglets et de
newsletters par un point d'entrée unique, self-hosted, contrôlé par l'équipe.

### Utilisateurs cibles
- Ingénieurs / ops / sécurité qui suivent l'actu technique.
- Équipes qui veulent une veille partagée (sources et catégories communes).

### Principes
- **Self-hosted** : déployable en Docker, données maîtrisées.
- **Léger** : peu de dépendances, démarrage simple (SQLite par défaut).
- **Ouvert** : import/export OPML, API documentée.

## 2. Périmètre fonctionnel

### 2.1 MVP (v0.1)
- **Authentification** : comptes utilisateurs, inscription/connexion, mots de
  passe hachés (bcrypt/argon2), sessions par cookie. Multi-utilisateur.
- **Modèle d'équipe** : les **sources et catégories sont partagées** entre tous
  les utilisateurs authentifiés (veille commune). L'état **lu/non-lu et favoris
  est propre à chaque utilisateur** (table `ArticleState`).
- **Sources** : CRUD de flux RSS/Atom, validation d'URL, organisation par
  catégories/tags.
- **Collecte** : récupération périodique (scheduler), parsing robuste, gestion
  des erreurs (flux HS, timeout), respect de `ETag`/`Last-Modified`.
- **Articles** : stockage avec déduplication (par GUID/URL), métadonnées
  (titre, auteur, date, source, résumé, contenu).
- **Lecture (web)** : liste paginée, vue article, marquage lu/non-lu, favoris
  (par utilisateur).
- **Filtres & recherche** : par catégorie, source, statut, mots-clés ;
  recherche plein texte.
- **Import/export OPML** : reprendre une liste de flux existante.

### 2.2 v0.2 (livré)
- **Alertes mots-clés** : règles de veille (ex. `CVE`, nom d'une techno) qui
  déclenchent une alerte sur chaque article correspondant. Vue dédiée + badge.
- **Digests** : résumé périodique (quotidien/hebdo) des nouveaux articles et
  alertes, en aperçu web, export Markdown, CLI et email (SMTP optionnel).
- **Catégories thématiques préconfigurées** : Sécurité/CVE, Cloud, DevOps,
  Langages, Réseau, IA/Data, Général (seed au démarrage).

### 2.3 Backlog / plus tard
- Rôles et permissions (admin / lecteur), gestion d'équipe fine.
- Notifications Slack / Teams / webhook.
- Résumés automatiques par LLM (Claude API).
- Sources non-RSS (Reddit, Hacker News, GitHub releases, mailing-lists).
- Recherche full-text avancée (PostgreSQL `tsvector`).

## 3. Exigences non fonctionnelles
- **Perf** : collecte asynchrone (httpx async), non bloquante pour l'UI.
- **Fiabilité** : un flux en erreur n'interrompt pas les autres ; retries.
- **Portabilité** : SQLite par défaut, PostgreSQL en option via variable d'env.
- **Observabilité** : logs structurés, statut de collecte par source.
- **Qualité** : tests unitaires (parsing, dedup, filtres), CI GitHub Actions.

## 4. Architecture technique

| Couche        | Choix                                              |
|---------------|----------------------------------------------------|
| Langage       | Python 3.12+                                        |
| API / Web     | FastAPI                                             |
| Front         | Jinja2 + HTMX (server-rendered, léger)             |
| ORM / DB      | SQLModel (SQLAlchemy) — **PostgreSQL**              |
| Auth          | Sessions cookie + hachage argon2/bcrypt (passlib)  |
| Parsing flux  | feedparser + httpx (async)                          |
| Scheduler     | APScheduler                                         |
| Migrations    | Alembic                                             |
| Tests         | pytest                                              |
| Déploiement   | Docker + docker-compose (app + PostgreSQL)          |
| Gestion deps  | uv / pyproject.toml                                 |

### Modèle de données (initial)
- **User** : id, email, nom, mot de passe haché, actif, créé_le.
- **Category** : id, nom, couleur (partagée).
- **Source** : id, titre, url du flux, url du site, category_id, actif,
  etag/last_modified, dernière collecte, statut d'erreur (partagée).
- **Article** : id, source_id, guid, titre, url, auteur, résumé, contenu,
  publié_le, récupéré_le.
- **ArticleState** : user_id, article_id, lu, favori (état par utilisateur).
- **Rule** (v0.2) : id, nom, mots-clés, action (tag/notify), catégorie cible.

### Structure du dépôt
```
pulse/
├── pulse/                # package applicatif
│   ├── main.py           # app FastAPI
│   ├── models.py         # SQLModel
│   ├── db.py             # session / init
│   ├── feeds.py          # collecte & parsing
│   ├── scheduler.py      # tâches périodiques
│   ├── routes/           # endpoints web + API
│   └── templates/        # Jinja2 + HTMX
├── tests/
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 5. Jalons
1. **Setup** : scaffolding, repo GitHub, CI, docker. 
2. **v0.1 MVP** : sources + collecte + lecture web + OPML.
3. **v0.2** : alertes mots-clés + digests.
4. **Durcissement** : auth, PostgreSQL, notifications.
