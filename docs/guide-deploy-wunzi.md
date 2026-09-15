# Guide de déploiement — WUNZI sur DigitalOcean

## Switch-Aware Mediation Case Intelligence · Next.js + Laravel + FastAPI + PostgreSQL

> **Domaines cibles** :
> - `wunzi.vylantic.com` — espace de travail médiateur (Next.js)
> - `api.wunzi.vylantic.com` — System of Record (Laravel)
> - `ai.wunzi.vylantic.com` — service d'intelligence (FastAPI)
>
> Ce guide installe WUNZI sur un droplet DigitalOcean avec une **infrastructure mutualisable** (reverse proxy Nginx partagé, réseaux Docker isolés). Si le droplet héberge déjà Kynara ou une autre application, WUNZI s'ajoute sans conflit.

---

## Trois différences avec le guide Kynara — à lire avant de commencer

WUNZI n'est pas structuré comme Kynara et ne se déploie pas pareil. Trois points portent des conséquences réelles.

### 1. Le monorepo et les contextes de build

Kynara a `backend/laravel/Dockerfile`, `backend/fastapi/Dockerfile`, `frontend/web/Dockerfile` — chaque Dockerfile à côté de son app.

WUNZI met **les trois Dockerfiles dans `infrastructure/docker/`** et les construit **depuis la racine du dépôt** :

```yaml
build:
  context: .                                       # ← racine, pas le sous-dossier
  dockerfile: infrastructure/docker/api.Dockerfile
```

C'est nécessaire parce que `api` et `intelligence` ont besoin du répertoire `benchmark/`, qui est en dehors de leur app. Copier-coller les blocs `build` de Kynara casserait la construction.

### 2. Le navigateur ne parle jamais à Laravel

Kynara expose `NEXT_PUBLIC_API_URL` : le navigateur appelle l'API directement.

WUNZI fait l'inverse. Toutes les lectures se font dans des Server Components, toutes les écritures via des Server Actions, et `lib/api.ts` porte `server-only` pour que le jeton ne puisse pas partir dans le bundle. Le navigateur ne connaît qu'un chemin relatif, `/api/laravel/*`, réécrit côté serveur Next.

Conséquence concrète : **`LARAVEL_API_URL` reste interne** (`http://wunzi-app:8000`). Il n'y a pas de `NEXT_PUBLIC_API_URL` dans WUNZI, et il ne faut pas en ajouter un — un dossier de médiation contient le récit de deux parties à un litige, ce n'est pas le genre de chose qu'on expose pour économiser un saut réseau.

`api.wunzi.vylantic.com` n'est donc pas nécessaire au fonctionnement du frontend. Il reste utile pour l'accès API direct, les webhooks et le débogage — mais c'est un choix, pas une dépendance.

### 3. `ai.wunzi.vylantic.com` mérite une décision consciente

Le service FastAPI n'est protégé que par un en-tête `X-Internal-Service-Token`. Il n'a ni sessions, ni rate limiting, ni comptes. Il a été conçu pour n'être appelé que par Laravel, sur un réseau Docker privé.

L'exposer publiquement signifie que **quiconque obtient ce jeton peut déclencher des transcriptions** — donc consommer votre quota ASR Sahara, et faire transiter de l'audio arbitraire par votre infrastructure.

Deux options, et la section 8.4 donne la configuration des deux :

| Option | Quand | Coût |
|---|---|---|
| **Ne pas exposer** (recommandé) | Production normale | `ai.` ne résout pas ; tout passe par le réseau Docker |
| **Exposer avec liste blanche IP** | Démo jury, inspection externe | Il faut maintenir la liste |

Si vous exposez pour la soumission du challenge, faites-le sciemment et régénérez le jeton après.

---

## Architecture cible

| Service | Domaine | Technologie | Port interne |
|---|---|---|---|
| Espace médiateur | `wunzi.vylantic.com` | Next.js 15 (App Router) | 3000 |
| System of Record | `api.wunzi.vylantic.com` | Laravel 11 + PHP 8.3 | 8000 |
| Intelligence | `ai.wunzi.vylantic.com` | FastAPI Python 3.12 | 8001 |
| Base de données | (interne) | PostgreSQL 16 | 5432 |
| Cache + queues | (interne) | Redis 7 | 6379 |
| Stockage audio | (interne) | MinIO (bucket **privé**) | 9000/9001 |

> Pas d'Elasticsearch, pas de PostGIS : WUNZI n'en utilise aucun. Le graphe d'issues est petit et relationnel, et il n'y a pas de recherche plein texte.

```text
Internet
   │
   ▼
Cloudflare (DNS + CDN + WAF)
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│  Droplet Ubuntu 24.04 LTS  (4 vCPU / 8 Go RAM / 80 Go SSD)   │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  proxy-network  →  proxy-nginx  (80 / 443, mutualisé)   │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─────────────── WUNZI ────────────────────────────────┐    │
│  │  Réseau : wunzi-network                              │    │
│  │   • wunzi-web       :3000  (Next.js)                 │    │
│  │   • wunzi-app       :8000  (Laravel)                 │    │
│  │   • wunzi-ai        :8001  (FastAPI)                 │    │
│  │   • wunzi-worker           (queue — transcription)   │    │
│  │   • wunzi-scheduler        (cron)                    │    │
│  │   • wunzi-postgres  :5432                            │    │
│  │   • wunzi-redis     :6379                            │    │
│  │   • wunzi-minio     :9000  (audio, bucket privé)     │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────── Autre SaaS (ex. Kynara) ──────────────────┐    │
│  │  Réseau : kynara-network (isolé)                      │    │
│  └───────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

---

# 1. Prérequis droplet

Si le droplet existe déjà (Kynara installée), passer à la section 4.

- **Plan** : 4 vCPU / 8 Go RAM / 80 Go SSD NVMe
- **OS** : Ubuntu 24.04 LTS
- **Région** : Frankfurt (`fra1`) ou Amsterdam (`ams3`)
- **Backups** : activés

> **Disque** : prévoir large si vous comptez faire tourner le benchmark étage 1 sur le droplet. Le dataset AfriSwitch pèse **6,8 Go** et n'est pas dans le dépôt. La section 16 explique comment l'éviter.

---

# 2. Hardening (nouveau droplet uniquement)

```bash
apt update && apt upgrade -y
apt install -y curl wget vim git ufw fail2ban unzip ca-certificates gnupg \
               lsb-release htop btop ncdu jq tree net-tools dnsutils

adduser deploy && usermod -aG sudo deploy
mkdir -p /home/deploy/.ssh
cp /root/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh && chmod 700 /home/deploy/.ssh

sed -i 's/^PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
sed -i 's/^#PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart ssh

timedatectl set-timezone Africa/Casablanca
systemctl enable --now fail2ban
```

---

# 3. Firewall + Docker (nouveau droplet uniquement)

```bash
ufw default deny incoming && ufw default allow outgoing
ufw allow OpenSSH && ufw allow 80/tcp && ufw allow 443/tcp && ufw enable

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list
apt update && apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
usermod -aG docker deploy
```

---

# 4. DNS

```
Type  Nom                          Valeur          Proxy
A     wunzi.vylantic.com           XX.XX.XX.XX     ☁️
A     api.wunzi.vylantic.com       XX.XX.XX.XX     ☁️
A     ai.wunzi.vylantic.com        XX.XX.XX.XX     ☁️   ← voir §8.4 avant
```

```bash
dig +short wunzi.vylantic.com
dig +short api.wunzi.vylantic.com
dig +short ai.wunzi.vylantic.com
```

---

# 5. Structure serveur

```
/var/www/
├── proxy/                        # Nginx mutualisé (existe déjà si Kynara)
│   ├── docker-compose.yml
│   ├── certbot/{conf,www}
│   └── nginx/{nginx.conf,conf.d/,snippets/}
│
└── wunzi/                        # Monorepo WUNZI, cloné tel quel
    ├── docker-compose.prod.yml   # ← créé en §9, à côté du compose de dev
    ├── .env
    ├── apps/
    │   ├── api/                  # Laravel
    │   ├── intelligence/         # FastAPI
    │   └── web/                  # Next.js
    ├── benchmark/                # fixtures, manifestes, annotations
    ├── infrastructure/docker/    # les 3 Dockerfiles
    ├── scripts/
    └── docs/
```

```bash
mkdir -p /var/www/wunzi
chown -R deploy:deploy /var/www/wunzi
```

---

# 6. Réseaux Docker

```bash
docker network create proxy-network 2>/dev/null || true   # existe si Kynara
docker network create wunzi-network
```

---

# 7. Récupération du code

```bash
cd /var/www/wunzi
git clone git@github.com:VOTRE-ORG/wunzi.git .
```

Le monorepo contient `apps/{api,intelligence,web}`, `benchmark/`, `infrastructure/docker/`, `scripts/`.

Vérifier immédiatement la cohérence des frontières HTTP — deux scripts, quelques secondes, et ils attrapent les erreurs qui ne se voient qu'en production :

```bash
python3 scripts/check_routes.py       # Web → Laravel → FastAPI
python3 scripts/check_migrations.py   # pièges de migration propres à PostgreSQL
```

Les deux doivent sortir en code 0 avant d'aller plus loin.

---

# 8. Reverse proxy Nginx

> Si le proxy est déjà installé (Kynara), il suffit d'ajouter les vhosts ci-dessous dans `/var/www/proxy/nginx/conf.d/`.

## 8.1 — Frontend : `/var/www/proxy/nginx/conf.d/wunzi-web.conf`

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name wunzi.vylantic.com;

    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 301 https://$host$request_uri; }
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    http2 on;
    server_name wunzi.vylantic.com;

    ssl_certificate     /etc/letsencrypt/live/wunzi.vylantic.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/wunzi.vylantic.com/privkey.pem;

    include /etc/nginx/snippets/ssl.conf;
    include /etc/nginx/snippets/security.conf;

    access_log /var/log/nginx/wunzi-web-access.log main;
    error_log  /var/log/nginx/wunzi-web-error.log warn;

    # L'audio est téléversé par le navigateur vers Next, qui le relaie à
    # Laravel. La limite doit dépasser wunzi.audio.max_bytes (40 Mo).
    client_max_body_size 48M;

    location /_next/static/ {
        proxy_pass http://wunzi-web:3000;
        include /etc/nginx/snippets/proxy.conf;
        add_header Cache-Control "public, max-age=31536000, immutable";
    }

    location / {
        proxy_pass http://wunzi-web:3000;
        include /etc/nginx/snippets/proxy.conf;
    }
}
```

## 8.2 — API : `/var/www/proxy/nginx/conf.d/wunzi-api.conf`

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name api.wunzi.vylantic.com;

    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 301 https://$host$request_uri; }
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    http2 on;
    server_name api.wunzi.vylantic.com;

    ssl_certificate     /etc/letsencrypt/live/api.wunzi.vylantic.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.wunzi.vylantic.com/privkey.pem;

    include /etc/nginx/snippets/ssl.conf;
    include /etc/nginx/snippets/security.conf;

    access_log /var/log/nginx/wunzi-api-access.log main;
    error_log  /var/log/nginx/wunzi-api-error.log warn;

    client_max_body_size 48M;

    # Budget de timeouts (docs/service-contract.md) :
    #   appel ASR        120s
    #   FastAPI (1 retry) ≤240s
    #   client Laravel    300s
    #   job de queue      420s
    # Le proxy doit rester au-dessus du client Laravel, sinon il coupe une
    # requête dont la transcription a déjà été payée.
    proxy_read_timeout 330s;
    proxy_send_timeout 330s;

    location / {
        proxy_pass http://wunzi-app:8000;
        include /etc/nginx/snippets/proxy.conf;
    }
}
```

## 8.3 — Interdire les routes de benchmark en public

Un run de benchmark consomme du quota ASR sur quatre fournisseurs. L'endpoint est derrière Sanctum, mais une couche de moins au niveau du proxy coûte une ligne :

```nginx
    # À ajouter dans le bloc 443 de wunzi-api.conf, AVANT location /
    location /api/benchmark-runs {
        # Décommenter et renseigner pour autoriser une IP d'inspection.
        # allow XX.XX.XX.XX;
        deny all;
    }
```

Retirer ce bloc si vous pilotez le benchmark depuis l'extérieur.

## 8.4 — Intelligence : `/var/www/proxy/nginx/conf.d/wunzi-ai.conf`

> **Lire §« Trois différences », point 3, avant d'activer ce vhost.** FastAPI n'a qu'un jeton partagé pour toute défense.

**Option A — ne pas exposer (recommandé en production).** Ne pas créer ce fichier, ne pas créer l'enregistrement DNS `ai.`. Laravel joint FastAPI par `http://wunzi-ai:8001` sur le réseau Docker. Rien n'est perdu : aucun client externe n'a besoin de ce service.

**Option B — exposer avec liste blanche IP** (démo jury, audit externe) :

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name ai.wunzi.vylantic.com;

    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 301 https://$host$request_uri; }
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    http2 on;
    server_name ai.wunzi.vylantic.com;

    ssl_certificate     /etc/letsencrypt/live/ai.wunzi.vylantic.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ai.wunzi.vylantic.com/privkey.pem;

    include /etc/nginx/snippets/ssl.conf;
    include /etc/nginx/snippets/security.conf;

    access_log /var/log/nginx/wunzi-ai-access.log main;
    error_log  /var/log/nginx/wunzi-ai-error.log warn;

    proxy_read_timeout 330s;
    proxy_send_timeout 330s;
    client_max_body_size 48M;

    # /health est ouvert : il ne révèle que le mode, les versions de pipeline
    # et les frontières de sécurité déclarées. Rien de sensible, et c'est
    # exactement ce qu'un juge veut pouvoir vérifier lui-même.
    location = /health {
        proxy_pass http://wunzi-ai:8001;
        include /etc/nginx/snippets/proxy.conf;
    }

    # Tout le reste : liste blanche. Ces routes dépensent du quota ASR.
    location / {
        # allow XX.XX.XX.XX;    # poste d'inspection
        deny all;

        proxy_pass http://wunzi-ai:8001;
        include /etc/nginx/snippets/proxy.conf;
    }
}
```

Après la période d'inspection :

```bash
mv /var/www/proxy/nginx/conf.d/wunzi-ai.conf{,.disabled}
docker exec proxy-nginx nginx -s reload
cd /var/www/wunzi && sed -i "s|^INTERNAL_AI_SERVICE_SECRET=.*|INTERNAL_AI_SERVICE_SECRET=$(openssl rand -base64 32)|" .env
docker compose -f docker-compose.prod.yml restart app worker fastapi
```

---

# 9. Variables d'environnement

## `/var/www/wunzi/.env`

Partir du `.env.example` du dépôt — il documente chaque variable, y compris le budget de timeouts.

```bash
cd /var/www/wunzi
cp .env.example .env
chmod 600 .env
```

Puis appliquer les valeurs de production :

```bash
# ─── Global ─────────────────────────────────────────
COMPOSE_PROJECT_NAME=wunzi
WUNZI_MODE=fixture               # fixture = rejoue des sorties provider réelles
                                 # live    = appelle les vraies API ASR
DATASET_VERSION=dataset-v1
PIPELINE_VERSION=pipeline-v1

# ─── PostgreSQL ─────────────────────────────────────
DB_CONNECTION=pgsql
DB_HOST=wunzi-postgres
DB_PORT=5432
DB_DATABASE=wunzi
DB_USERNAME=wunzi
DB_PASSWORD=                     # openssl rand -base64 32

# ─── Redis ──────────────────────────────────────────
REDIS_HOST=wunzi-redis
REDIS_PORT=6379
REDIS_PASSWORD=                  # openssl rand -base64 32
CACHE_STORE=redis
QUEUE_CONNECTION=redis
SESSION_DRIVER=redis

# ─── Laravel ────────────────────────────────────────
APP_NAME=WUNZI
APP_ENV=production
APP_DEBUG=false
APP_KEY=                         # §11
APP_URL=https://api.wunzi.vylantic.com
APP_TIMEZONE=UTC
FRONTEND_URL=https://wunzi.vylantic.com
SANCTUM_STATEFUL_DOMAINS=wunzi.vylantic.com
SESSION_DOMAIN=.wunzi.vylantic.com

# ─── MinIO — audio de médiation, bucket PRIVÉ ───────
FILESYSTEM_DISK=s3
AWS_ACCESS_KEY_ID=wunzi_minio
AWS_SECRET_ACCESS_KEY=           # openssl rand -base64 32
AWS_DEFAULT_REGION=us-east-1
AWS_BUCKET=wunzi-audio
AWS_ENDPOINT=http://wunzi-minio:9000
AWS_URL=                         # vide : l'accès passe par URL signée (10 min)
AWS_USE_PATH_STYLE_ENDPOINT=true

# ─── Laravel → FastAPI ──────────────────────────────
INTELLIGENCE_BASE_URL=http://wunzi-ai:8001
INTERNAL_AI_SERVICE_SECRET=      # openssl rand -base64 32 — partagé entre app et fastapi

# ─── Budget de timeouts — ces valeurs doivent s'emboîter ───
# appel ASR 120s < FastAPI ≤240s < client Laravel 300s < job 420s
INTELLIGENCE_TIMEOUT=300
INTELLIGENCE_CONNECT_TIMEOUT=5
ASR_TIMEOUT_SECONDS=120
ASR_MAX_RETRIES=1
BENCHMARK_MAX_WAIT_SECONDS=3300

# ─── Fournisseurs ASR — requis seulement si WUNZI_MODE=live ───
DEFAULT_ASR_PROVIDER=sahara
SAHARA_API_KEY=
SAHARA_BASE_URL=https://infer.voice.intron.io
SAHARA_MODEL=sahara
WHISPER_API_KEY=
MODEL_B_API_KEY=
MODEL_C_API_KEY=

# ─── LLM — deterministic ne demande aucun réseau ────
LLM_PROVIDER=deterministic

# ─── Critical Speech Guard ──────────────────────────
GUARD_AMOUNT_CONFIDENCE_THRESHOLD=0.90
GUARD_DATE_CONFIDENCE_THRESHOLD=0.85
GUARD_DEFAULT_CONFIDENCE_THRESHOLD=0.80

# ─── Chemins benchmark (dans les containers) ────────
FIXTURE_ROOT=/benchmark/fixtures
BENCHMARK_ROOT=/benchmark

# ─── Next.js — server-side uniquement ───────────────
LARAVEL_API_URL=http://wunzi-app:8000   # interne : jamais exposé au navigateur
WUNZI_API_TOKEN=                        # §11 : php artisan wunzi:token
```

> **`AWS_URL` reste vide.** Les enregistrements audio sont des récits de parties à un litige : le bucket est privé et chaque accès passe par une URL signée valable 10 minutes. Renseigner `AWS_URL` ferait générer des liens publics directs.

---

# 10. Docker Compose production

## `/var/www/wunzi/docker-compose.prod.yml`

> Adaptation du `docker-compose.yml` du dépôt : aucun port publié sauf via `proxy-network`, mots de passe depuis `.env`, healthchecks, pas de bind-mount du code (l'image contient le code), et **les mêmes Dockerfiles, inchangés**.

```yaml
services:

  # ─── PostgreSQL ───────────────────────────────────────────────
  postgres:
    image: postgres:16-alpine
    container_name: wunzi-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB:       ${DB_DATABASE}
      POSTGRES_USER:     ${DB_USERNAME}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - ./postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USERNAME}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks: [wunzi-network]

  # ─── Redis ────────────────────────────────────────────────────
  redis:
    image: redis:7-alpine
    container_name: wunzi-redis
    restart: unless-stopped
    command: redis-server --requirepass ${REDIS_PASSWORD} --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - ./redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "--pass", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      retries: 5
    networks: [wunzi-network]

  # ─── MinIO — audio de médiation ───────────────────────────────
  minio:
    # quay.io, pas Docker Hub : MinIO y a retiré minio/minio et minio/mc en
    # septembre 2026 — les dépôts renvoient 404, pas seulement les tags.
    # Versions épinglées : une stack de production ne change pas de binaire
    # au prochain `up --build` sans qu'on l'ait demandé.
    image: quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z
    container_name: wunzi-minio
    restart: unless-stopped
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER:     ${AWS_ACCESS_KEY_ID}
      MINIO_ROOT_PASSWORD: ${AWS_SECRET_ACCESS_KEY}
    volumes:
      - ./minio-data:/data
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 10s
      retries: 5
    networks: [wunzi-network]

  # ─── Création du bucket, en privé ─────────────────────────────
  createbuckets:
    image: quay.io/minio/mc:RELEASE.2025-08-13T08-35-41Z
    container_name: wunzi-createbuckets
    depends_on: [minio]
    entrypoint: >
      /bin/sh -c "
      until (mc alias set wunzi http://wunzi-minio:9000 ${AWS_ACCESS_KEY_ID} ${AWS_SECRET_ACCESS_KEY}) do sleep 2; done;
      mc mb --ignore-existing wunzi/${AWS_BUCKET};
      mc anonymous set none wunzi/${AWS_BUCKET};
      exit 0;"
    networks: [wunzi-network]

  # ─── Laravel — System of Record ───────────────────────────────
  app:
    build:
      context: .                                       # racine du monorepo
      dockerfile: infrastructure/docker/api.Dockerfile
    container_name: wunzi-app
    restart: unless-stopped
    depends_on:
      postgres: {condition: service_healthy}
      redis:    {condition: service_healthy}
    env_file: .env
    environment:
      APP_ENV: production
      APP_DEBUG: "false"
      DB_HOST: wunzi-postgres
      REDIS_HOST: wunzi-redis
      INTELLIGENCE_BASE_URL: http://wunzi-ai:8001
      AWS_ENDPOINT: http://wunzi-minio:9000
    volumes:
      # Le benchmark n'est PAS dans l'image : il change indépendamment du code
      # et n'a pas à déclencher un rebuild.
      - ./benchmark:/benchmark
      - laravel-storage:/var/www/html/storage
    networks: [wunzi-network, proxy-network]

  # ─── Queue worker — transcription + extraction ────────────────
  worker:
    build:
      context: .
      dockerfile: infrastructure/docker/api.Dockerfile
    container_name: wunzi-worker
    restart: unless-stopped
    # --timeout doit dépasser ProcessRecording::$timeout (420s), sinon le
    # worker tue un job dont l'appel ASR a déjà été facturé.
    command: php artisan queue:work redis --sleep=3 --tries=3 --timeout=450 --max-time=3600
    depends_on:
      app:   {condition: service_started}
      redis: {condition: service_healthy}
    env_file: .env
    environment:
      DB_HOST: wunzi-postgres
      REDIS_HOST: wunzi-redis
      INTELLIGENCE_BASE_URL: http://wunzi-ai:8001
      AWS_ENDPOINT: http://wunzi-minio:9000
    volumes:
      - ./benchmark:/benchmark
      - laravel-storage:/var/www/html/storage
    networks: [wunzi-network]

  # ─── Scheduler ────────────────────────────────────────────────
  scheduler:
    build:
      context: .
      dockerfile: infrastructure/docker/api.Dockerfile
    container_name: wunzi-scheduler
    restart: unless-stopped
    command: sh -c "while true; do php artisan schedule:run --no-interaction; sleep 60; done"
    depends_on: [app]
    env_file: .env
    environment:
      DB_HOST: wunzi-postgres
      REDIS_HOST: wunzi-redis
    volumes:
      - laravel-storage:/var/www/html/storage
    networks: [wunzi-network]

  # ─── FastAPI — intelligence ───────────────────────────────────
  fastapi:
    build:
      context: .
      dockerfile: infrastructure/docker/intelligence.Dockerfile
    container_name: wunzi-ai
    restart: unless-stopped
    env_file: .env
    environment:
      WUNZI_MODE: ${WUNZI_MODE}
      INTELLIGENCE_LOG_LEVEL: info
      FIXTURE_ROOT: /benchmark/fixtures
      BENCHMARK_ROOT: /benchmark
      S3_ENDPOINT: http://wunzi-minio:9000
      S3_ACCESS_KEY: ${AWS_ACCESS_KEY_ID}
      S3_SECRET_KEY: ${AWS_SECRET_ACCESS_KEY}
    volumes:
      - ./benchmark:/benchmark
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:8001/health"]
      interval: 30s
      retries: 3
    # proxy-network seulement si vous avez choisi l'option B en §8.4.
    networks: [wunzi-network, proxy-network]

  # ─── Next.js — espace médiateur ───────────────────────────────
  web:
    build:
      context: .
      dockerfile: infrastructure/docker/web.Dockerfile
    container_name: wunzi-web
    restart: unless-stopped
    environment:
      NODE_ENV: production
      # Interne. Pas de NEXT_PUBLIC_API_URL dans WUNZI : le navigateur ne
      # connaît que /api/laravel/*, réécrit par le serveur Next.
      LARAVEL_API_URL: http://wunzi-app:8000
      WUNZI_API_TOKEN: ${WUNZI_API_TOKEN}
      NEXT_PUBLIC_APP_NAME: WUNZI
      NEXT_PUBLIC_DEMO_MODE: ${WUNZI_MODE}
    depends_on: [app]
    networks: [wunzi-network, proxy-network]

volumes:
  laravel-storage:

networks:
  wunzi-network:
    external: true
  proxy-network:
    external: true
```

> **Les trois Dockerfiles du dépôt sont utilisés tels quels.** Aucune modification n'est nécessaire. Le contexte de build est la racine, pas les sous-dossiers — voir §« Trois différences », point 1.

---

# 11. Certificats Let's Encrypt

## 11.1 — Bootstrap HTTP

```bash
cat > /var/www/proxy/nginx/conf.d/_wunzi-bootstrap.conf << 'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name wunzi.vylantic.com api.wunzi.vylantic.com ai.wunzi.vylantic.com;

    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 200 "WUNZI Bootstrap OK"; add_header Content-Type text/plain; }
}
EOF

cd /var/www/proxy/nginx/conf.d
for f in wunzi-web.conf wunzi-api.conf wunzi-ai.conf; do
  [ -f "$f" ] && mv "$f" "${f}.disabled"
done
docker exec proxy-nginx nginx -s reload
```

## 11.2 — Émettre

Retirer `-d ai.wunzi.vylantic.com` si vous avez choisi l'option A en §8.4.

```bash
cd /var/www/proxy
docker compose run --rm --entrypoint certbot certbot certonly \
  --webroot -w /var/www/certbot \
  --email fdjikoloum@gmail.com --agree-tos --no-eff-email \
  -d wunzi.vylantic.com \
  -d api.wunzi.vylantic.com \
  -d ai.wunzi.vylantic.com
```

## 11.3 — Réactiver

```bash
cd /var/www/proxy/nginx/conf.d
for f in wunzi-web.conf wunzi-api.conf wunzi-ai.conf; do
  [ -f "${f}.disabled" ] && mv "${f}.disabled" "$f"
done
rm -f _wunzi-bootstrap.conf
docker exec proxy-nginx nginx -s reload
```

---

# 12. Premier déploiement

```bash
cd /var/www/wunzi

docker compose -f docker-compose.prod.yml config          # valider
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml logs -f
```

## 12.1 — Clé applicative

```bash
docker compose -f docker-compose.prod.yml exec app php artisan key:generate --show
# → coller dans .env (APP_KEY=base64:...)
docker compose -f docker-compose.prod.yml restart app worker scheduler
```

## 12.2 — Migrations

```bash
docker compose -f docker-compose.prod.yml exec app php artisan migrate --force
docker compose -f docker-compose.prod.yml exec app php artisan db:seed --force
```

> Si `migrate` échoue sur `claims_superseded_by_foreign` (SQLSTATE 42830), la migration corrigée n'est pas déployée. Faire `git pull` : la clé auto-référencée doit être ajoutée dans un `Schema::table()` séparé. Détail dans `docs/limitations.md` et `scripts/check_migrations.py`.

## 12.3 — Jeton API pour le frontend

Sans ça, **toutes** les pages affichent une erreur : presque toutes les routes `/api` sont derrière `auth:sanctum`.

```bash
docker compose -f docker-compose.prod.yml exec app php artisan wunzi:token
```

Coller la valeur dans `WUNZI_API_TOKEN` du `.env`, puis :

```bash
docker compose -f docker-compose.prod.yml up -d --build web
```

> Le rebuild est nécessaire : Next lit `WUNZI_API_TOKEN` côté serveur au démarrage. Sanctum ne stocke qu'un hash, donc le texte clair n'apparaît qu'une fois — `--revoke` pour le remplacer.

## 12.4 — Caches production

```bash
docker compose -f docker-compose.prod.yml exec app php artisan config:cache
docker compose -f docker-compose.prod.yml exec app php artisan route:cache
docker compose -f docker-compose.prod.yml exec app php artisan view:cache
docker compose -f docker-compose.prod.yml exec app php artisan storage:link
```

## 12.5 — Dossier de démonstration

```bash
docker compose -f docker-compose.prod.yml exec app php artisan wunzi:demo-case
```

Construit `WZ_DEMO_001` (litige de dépôt locatif : 150 000 contre 100 000 RWF, promesse de remboursement niée, facture de réparation mentionnée mais non fournie) à partir des fixtures. Ne nécessite aucune clé ASR.

---

# 13. Vérifications

```bash
docker ps | grep wunzi

curl -I https://wunzi.vylantic.com
curl -I https://api.wunzi.vylantic.com/api/health

# Si option B en §8.4 :
curl -s https://ai.wunzi.vylantic.com/health | jq
```

`/health` de FastAPI doit renvoyer les frontières déclarées — c'est vérifiable par un tiers :

```json
{
  "status": "ok",
  "mode": "fixture",
  "boundaries": {
    "decides_truth": false,
    "scores_credibility": false,
    "recommends_liability": false,
    "gives_legal_advice": false,
    "resolves_autonomously": false
  }
}
```

Parcours complet dans le navigateur : ouvrir `https://wunzi.vylantic.com/cases`, le dossier de démo doit apparaître avec son graphe d'issues.

---

# 14. Sauvegardes

L'audio de médiation est la donnée la plus sensible du système. La sauvegarde est **chiffrée**, contrairement à celle de Kynara.

## `/usr/local/bin/backup-wunzi.sh`

```bash
#!/bin/bash
set -euo pipefail

BACKUP_ROOT=/var/backups/wunzi
TS=$(date +%Y%m%d-%H%M%S)
DEST="$BACKUP_ROOT/$TS"
mkdir -p "$DEST"

cd /var/www/wunzi
set -a; source .env; set +a

# PostgreSQL — dossiers, claims, vérifications, journal d'audit
docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U "$DB_USERNAME" "$DB_DATABASE" | gzip > "$DEST/postgres.sql.gz"

# Audio — récits de parties à un litige : chiffré au repos.
# Clé publique GPG importée au préalable ; la clé privée ne vit PAS sur le droplet.
tar -czf - minio-data 2>/dev/null \
  | gpg --encrypt --recipient backup@vylantic.com --trust-model always \
  > "$DEST/minio-data.tar.gz.gpg"

# Storage Laravel
docker run --rm -v wunzi_laravel-storage:/data -v "$DEST":/backup alpine \
  tar -czf /backup/laravel-storage.tar.gz -C /data . 2>/dev/null || true

# Le benchmark n'est pas sauvegardé : les fixtures sont dans git, et le dataset
# AfriSwitch se retélécharge. Sauvegarder 6,8 Go tous les jours n'a pas de sens.

find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -mtime +7 -exec rm -rf {} \;
echo "Backup WUNZI : $DEST"
```

```bash
chmod +x /usr/local/bin/backup-wunzi.sh
crontab -e
# 0 3 * * * /usr/local/bin/backup-wunzi.sh >> /var/log/backup-wunzi.log 2>&1
```

> **Le retrait de consentement doit atteindre les sauvegardes.** Un participant peut retirer son consentement, ce qui supprime le clip et tout ce qui en dérive. Une sauvegarde conservée 7 jours signifie que la suppression complète prend 7 jours — c'est acceptable si c'est écrit, ça ne l'est pas si on l'a oublié. Documenté dans `docs/responsible-ai.md`.

---

# 15. Déploiement continu

## `/usr/local/bin/deploy-wunzi.sh`

```bash
#!/bin/bash
set -euo pipefail

cd /var/www/wunzi
git pull origin main

# Les frontières HTTP d'abord : un chemin renommé casse en silence.
python3 scripts/check_routes.py
python3 scripts/check_migrations.py

docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

docker compose -f docker-compose.prod.yml exec -T app php artisan migrate --force
docker compose -f docker-compose.prod.yml exec -T app php artisan config:cache
docker compose -f docker-compose.prod.yml exec -T app php artisan route:cache
docker compose -f docker-compose.prod.yml exec -T app php artisan view:cache

# Le worker porte l'ancien code jusqu'au redémarrage.
docker compose -f docker-compose.prod.yml restart worker scheduler

echo "WUNZI déployé."
```

```bash
chmod +x /usr/local/bin/deploy-wunzi.sh
```

---

# 16. Faire tourner le benchmark en production

Deux étages, deux besoins différents.

## Étage 2 — scénarios de médiation (aucune dépendance externe)

```bash
cd /var/www/wunzi
docker compose -f docker-compose.prod.yml exec fastapi \
  python -m app.benchmark.cli run --split holdout \
  --providers sahara,whisper,model_b,model_c --out /benchmark/reports
```

En `WUNZI_MODE=fixture` cela rejoue des sorties provider stockées. Le rapport porte alors la bannière **NOT PUBLISHABLE** tant que les fixtures sont des placeholders — c'est voulu, et aucun chiffre qui en sort ne décrit un modèle réel.

## Étage 1 — AfriSwitch (6,8 Go, dataset restreint)

```bash
docker compose -f docker-compose.prod.yml exec fastapi \
  pip install --no-cache-dir datasets huggingface_hub
docker compose -f docker-compose.prod.yml exec fastapi huggingface-cli login
# puis accepter les conditions sur
# https://huggingface.co/datasets/intronhealth/AfriSwitch

docker compose -f docker-compose.prod.yml exec fastapi \
  python -m app.benchmark.afriswitch_cli run \
  --config kinyarwanda --limit 200 \
  --providers sahara,whisper,model_b,model_c --out /benchmark/reports
```

> **Le faire plutôt sur une machine de travail que sur le droplet.** 6,8 Go de dataset plus les appels ASR live n'ont rien à faire sur le serveur qui sert l'espace médiateur, et les rapports générés sont de simples fichiers à committer dans `benchmark/reports/`. Le droplet n'a besoin de rien de tout ça pour fonctionner.

Pour des chiffres réels il faut `WUNZI_MODE=live` et les quatre clés ASR renseignées. Chaque run consomme du quota chez les quatre fournisseurs.

---

# 17. Logs & monitoring

```bash
cd /var/www/wunzi
docker compose -f docker-compose.prod.yml logs -f app       # Laravel
docker compose -f docker-compose.prod.yml logs -f worker    # transcription
docker compose -f docker-compose.prod.yml logs -f fastapi   # intelligence
docker compose -f docker-compose.prod.yml logs -f web       # Next.js

docker exec proxy-nginx tail -f /var/log/nginx/wunzi-api-access.log
docker stats | grep wunzi
```

Les deux services émettent du JSON structuré. Quelques événements à surveiller :

| Événement | Signification |
|---|---|
| `asr_failed` | un fournisseur a échoué — jamais remplacé en silence |
| `guard_evaluated` | nombre de valeurs critiques renvoyées au locuteur |
| `issue_graph_built` | nombre d'issues en `DISPUTED` / `UNVERIFIED` |
| `neutrality_violation` | prose adjudicative bloquée avant le médiateur |
| `recording.processing_failed` | transcription abandonnée après tous les essais |

```bash
docker compose -f docker-compose.prod.yml logs fastapi | jq -R 'fromjson? | select(.event == "asr_failed")'
```

Une file de queue qui s'allonge indique en général un problème ASR, pas un problème Laravel :

```bash
docker compose -f docker-compose.prod.yml exec app php artisan queue:monitor redis:default --max=50
docker compose -f docker-compose.prod.yml exec app php artisan queue:failed
```

---

# 18. Optimisations production

## Swap

```bash
fallocate -l 4G /swapfile && chmod 600 /swapfile
mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

## Image Next.js plus légère (optionnel)

Le `web.Dockerfile` actuel copie tout `node_modules` — environ 440 Mo dans l'image finale. Le mode `standalone` de Next réduit ça à quelques dizaines de mégaoctets, mais demande **deux** changements cohérents, à faire ensemble ou pas du tout :

```javascript
// apps/web/next.config.mjs
const nextConfig = {
  output: 'standalone',   // ← à ajouter
  reactStrictMode: true,
  async rewrites() { /* inchangé */ },
};
```

```dockerfile
# infrastructure/docker/web.Dockerfile — remplacer l'étage runner
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
CMD ["node", "server.js"]
```

Ne pas faire l'un sans l'autre : `standalone` sans le Dockerfile adapté produit une image qui démarre puis renvoie du 404.

## Cloudflare

Proxy activé (nuage orange), mode SSL **Full (strict)**.

> Cloudflare coupe à 100 secondes sur les offres gratuites. Aucun parcours utilisateur de WUNZI ne dure aussi longtemps — la transcription est asynchrone, le navigateur interroge un statut. Mais **ne pas piloter un benchmark à travers Cloudflare** : un run dépasse largement cette limite. Utiliser `docker compose exec`.

---

# 19. Checklist sécurité

**Infrastructure**

- [ ] UFW actif (22/80/443 uniquement)
- [ ] Connexion root SSH par mot de passe désactivée
- [ ] fail2ban actif
- [ ] Cloudflare devant le droplet, SSL Full (strict)
- [ ] `.env` en `chmod 600`

**Secrets**

- [ ] Mots de passe Postgres / Redis / MinIO générés par `openssl rand -base64 32`
- [ ] `INTERNAL_AI_SERVICE_SECRET` régénéré, jamais laissé à `change-me`
- [ ] `APP_KEY` généré, `APP_DEBUG=false`, `APP_ENV=production`
- [ ] Jeton Sanctum créé par `wunzi:token`, et régénéré après toute démo

**Propre à WUNZI**

- [ ] Bucket MinIO en `anonymous set none`, `AWS_URL` vide
- [ ] `ai.wunzi.vylantic.com` : décision prise consciemment (§8.4), liste blanche si exposé
- [ ] `/api/benchmark-runs` refusé au public (§8.3)
- [ ] Sauvegardes audio chiffrées, clé privée hors du droplet
- [ ] Rétention de sauvegarde documentée dans la note d'éthique — un retrait de consentement met 7 jours à atteindre les sauvegardes

---

# 20. Dépannage

## Toutes les pages affichent une erreur API

Presque toujours l'une de deux causes, et l'écran indique laquelle :

```bash
# « The API is not reachable » → LARAVEL_API_URL faux, ou app arrêtée
docker compose -f docker-compose.prod.yml exec web wget -qO- http://wunzi-app:8000/api/health

# « The API refused this request » → jeton absent ou révoqué
docker compose -f docker-compose.prod.yml exec app php artisan wunzi:token --revoke
```

Après un nouveau jeton : rebuild du service `web`, pas un simple restart.

## 502 Bad Gateway

```bash
docker exec proxy-nginx nginx -t
docker network inspect proxy-network | grep wunzi
# wunzi-web et wunzi-app doivent y figurer (et wunzi-ai si option B)
```

## Migration : SQLSTATE 42830 sur `claims`

Version obsolète du code. La clé auto-référencée `superseded_by` doit être ajoutée dans un `Schema::table()` séparé après le `Schema::create` — Laravel place la clé primaire en dernier, donc PostgreSQL voit la clé étrangère avant la contrainte unique qu'elle vise.

```bash
git pull && python3 scripts/check_migrations.py
```

## La transcription reste en « Transcribing »

```bash
docker compose -f docker-compose.prod.yml logs worker | tail -50
docker compose -f docker-compose.prod.yml exec app php artisan queue:failed
```

En `WUNZI_MODE=live` sans clé ASR valide, le job échoue trois fois puis marque l'enregistrement `FAILED`. C'est le comportement voulu : WUNZI ne substitue jamais un autre modèle de parole — ça changerait ce sur quoi le dossier est bâti sans le dire.

Reprendre en `fixture` pour vérifier que le reste de la chaîne fonctionne :

```bash
sed -i 's/^WUNZI_MODE=.*/WUNZI_MODE=fixture/' .env
docker compose -f docker-compose.prod.yml restart app worker fastapi
```

## Un dossier refuse de passer en READY

Ce n'est pas un bug. Une valeur critique attend encore la confirmation de son locuteur, et la machine à états le bloque volontairement :

```bash
docker compose -f docker-compose.prod.yml exec app php artisan tinker
>>> App\Models\CriticalField::where('status','NEEDS_CONFIRMATION')->count();
```

Passer par `/cases/{id}/verify` dans l'interface. Seul le locuteur peut confirmer ou corriger ses propres mots.

## Timeout sur les appels à l'intelligence

Vérifier que le budget s'emboîte encore — un `INTELLIGENCE_TIMEOUT` sous le pire cas FastAPI fait jeter un travail déjà payé :

```bash
docker compose -f docker-compose.prod.yml exec app php -r \
  'echo config("wunzi.intelligence.timeout"), PHP_EOL;'   # doit être ≥ 300
grep -c "^INTELLIGENCE_TIMEOUT=" .env                      # doit être 1, pas 2
```

phpdotenv garde la **première** définition : un doublon avec une ancienne valeur gagne silencieusement.

## `pull access denied for minio/mc` au premier `up --build`

Ce n'est pas un problème d'authentification, malgré le message. **MinIO a retiré
`minio/minio` et `minio/mc` du Docker Hub en septembre 2026** — les dépôts
eux-mêmes renvoient 404, pas seulement les tags épinglés :

```bash
curl -s https://hub.docker.com/v2/repositories/minio/mc/
# {"message":"object not found","errinfo":{}}
```

Le message Docker couvre à la fois « dépôt inexistant » et « non authentifié »,
ce qui envoie chercher des identifiants pour rien. Et comme une seule image en
échec interrompt les cinq autres tirages, toute la stack s'arrête.

quay.io est le registre officiel de MinIO et sert les mêmes releases sous les
mêmes tags. Le `docker-compose.prod.yml` de ce guide y pointe déjà. Si vous
partez d'une ancienne copie :

```yaml
  minio:
    image: quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z
  createbuckets:
    image: quay.io/minio/mc:RELEASE.2025-08-13T08-35-41Z
```

Vérifier avant de relancer la stack entière :

```bash
docker pull quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z
docker pull quay.io/minio/mc:RELEASE.2025-08-13T08-35-41Z
```

Les deux se tirent anonymement, sans `docker login`.

> **À surveiller.** MinIO a archivé son édition communautaire et retire
> progressivement sa distribution publique. quay.io fonctionne aujourd'hui ;
> rien ne garantit que ce soit permanent. Si ça bouge encore, WUNZI n'utilise
> MinIO que comme stockage S3 privé pour l'audio — n'importe quel serveur
> compatible S3 convient, et seule la variable `AWS_ENDPOINT` change.

## Disque saturé

```bash
docker system prune -af
du -sh /var/www/wunzi/*
ncdu /var
```

Coupables habituels : `minio-data` (audio), et le cache Hugging Face si le benchmark étage 1 a tourné sur le droplet.

---

# 21. Architecture finale

```
                   Internet
                       │
                  Cloudflare DNS
                       │
                   Port 80/443
                       ▼
            ┌────────────────────┐
            │   proxy-nginx      │  (proxy-network)
            └────────────────────┘
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
     wunzi-web                 wunzi-app
     (Next.js)                 (Laravel)
     wunzi.vylantic.com        api.wunzi.vylantic.com
          │                         │
          └──── server-side ────────┤
                                    ▼
                               wunzi-ai
                               (FastAPI, interne par défaut)
                                    │
          ┌─────────────────────────┤
          ▼                         ▼
   wunzi-postgres            wunzi-minio
   wunzi-redis               (audio, privé)
   wunzi-worker
   wunzi-scheduler
        (wunzi-network)
```

Le navigateur ne joint que `wunzi-web`. Tout le reste est atteint côté serveur.

WUNZI est en production sur `wunzi.vylantic.com`.

---

*Fin du guide WUNZI.*
