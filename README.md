# Clash of Clans Storage (Clan + Joueurs)

Stack Docker:
- `db`: PostgreSQL
- `cron`: fetch API Clash of Clans + stockage DB (horaire)
- `dashboard-api`: API Python (lit la DB, calcule les stats)
- `dashboard`: front **React Native Web** (design liquid) sur `http://localhost:8120`
- `db-backup`: dump PostgreSQL compressé et rotatif dans `./backups`

## Configuration

1. Copier `.env.example` vers `.env` puis renseigner `API_KEY`.
   Port DB local disponible:
   - `POSTGRES_HOST_PORT` (par défaut `5433`, pour libérer `5432`)
   Variables backup disponibles:
   - `DB_BACKUP_INTERVAL_SECONDS` (par défaut `21600`, soit toutes les 6h)
   - `DB_BACKUP_RETENTION_COUNT` (par défaut `28` dumps conservés)
2. Renseigner `config/config.yml`:
   - `clan_id` obligatoire (pas de valeur par défaut)
   - `fetch_cron` (par défaut: `0 * * * *`)
   - `db_url` (par défaut: DB Docker)

Exemple:

```yaml
clan_id: "#2PVYQ00R"
fetch_cron: "0 * * * *"
db_url: "postgresql://coc:coc@db:5432/coc"
api_base_url: "https://api.clashofclans.com/v1"
request_timeout_seconds: 20
```

## Lancement

```bash
docker compose up --build -d
```

## Accès

- Dashboard (React Native Web): `http://localhost:8120`
- PostgreSQL: `localhost:5433`
- API dashboard:
  - `http://localhost:8120/health` (proxy vers API)
  - `http://localhost:8120/api/overview?scale=30d`
  - `http://localhost:8120/api/player/2PRJVLY29?scale=30d`

## Logs utiles

```bash
docker compose logs -f cron
docker compose logs -f dashboard-api
docker compose logs -f dashboard
docker compose logs -f db-backup
```

## Sauvegardes DB

- Les backups PostgreSQL sont écrits automatiquement dans `./backups`.
- Un dump compressé est créé au démarrage du service puis à intervalle régulier.
- La rotation supprime automatiquement les dumps les plus anciens au-delà de la rétention configurée.
- Les backups sont stockés hors du volume Docker PostgreSQL, donc `docker compose down -v` n'efface pas `./backups`.

### Restaurer un backup

Exemple avec le dump le plus récent:

```bash
gunzip -c backups/coc_YYYYMMDDTHHMMSSZ.sql.gz | docker compose exec -T db psql -U coc -d coc
```

## Règles métier importantes

- `missed_attacks` est compté **uniquement quand la guerre est terminée** (`warEnded`).
- En **LDC (CWL)**, la capacité d'attaque est forcée à **1 attaque/joueur**.
- Distinction explicite des guerres:
  - `war_type=regular` => **GDC**
  - `war_type=cwl` => **LDC**
- `Clan Games` est analysé en **delta mensuel** (mois vs mois), pas en cumul brut.
- `Raids Capitale` sont exploités par **weekend** (fenêtre vendredi -> lundi via saisons API).
- Les stats multi-périodes viennent uniquement de la DB (snapshots + historiques), pas d'un calcul direct live API.

## Schéma DB

Documentation lisible du schéma:
- `docs/db-schema.md`

Schéma SQL source:
- `db/init.sql`

## Données stockées pour pilotage chef de clan

- Dons joueurs
- Participation GDC/LDC
- Ligue
- Clan Games (cumulé)
- Capitale (saisons + détail joueur)

Tout est historisé pour analyser plusieurs échelles de temps: `7d`, `30d`, `90d`, `365d`, `all`.
Le tableau "Détail participation joueurs" est triable par colonne (joueur, TH, dons, global, miss GDC/LDC, score).

## Notes migration

Si la base existait déjà et que tu veux repartir proprement:

```bash
docker compose down -v
docker compose up --build -d
```

Les dumps présents dans `./backups` restent disponibles pour restaurer l'historique après recréation de la base.
