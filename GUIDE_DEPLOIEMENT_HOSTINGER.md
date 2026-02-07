# 🚀 GUIDE DÉPLOIEMENT HOSTINGER - ÉTAPE PAR ÉTAPE

## 📋 Prérequis

- **VPS Hostinger** : IP `72.60.189.23`
- **Accès SSH** : root ou utilisateur sudo
- **Domaine** : Configuré pour pointer vers votre VPS

---

## 🔧 ÉTAPE 1 : Connexion au VPS

```bash
# Depuis votre terminal (Mac/Linux) ou PuTTY (Windows)
ssh root@72.60.189.23

# Si vous avez une clé SSH :
ssh -i /chemin/vers/cle root@72.60.189.23
```

---

## 📦 ÉTAPE 2 : Installation des dépendances système

```bash
# Mettre à jour le système
apt update && apt upgrade -y

# Installer les outils de base
apt install -y curl wget git build-essential

# Installer Node.js 20 (LTS)
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

# Vérifier l'installation
node --version  # Doit afficher v20.x.x
npm --version

# Installer Yarn
npm install -g yarn

# Installer Python 3.11+ et pip
apt install -y python3 python3-pip python3-venv

# Vérifier Python
python3 --version  # Doit afficher 3.10+
```

---

## 🍃 ÉTAPE 3 : Installer MongoDB

```bash
# Importer la clé GPG MongoDB
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor

# Ajouter le repository (pour Ubuntu 22.04)
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-7.0.list

# Installer MongoDB
apt update
apt install -y mongodb-org

# Démarrer MongoDB
systemctl start mongod
systemctl enable mongod

# Vérifier que MongoDB fonctionne
systemctl status mongod
mongosh --eval "db.version()"
```

---

## 📁 ÉTAPE 4 : Créer la structure des dossiers

```bash
# Créer les dossiers pour le projet
mkdir -p /var/www/leads-system/backend
mkdir -p /var/www/leads-system/frontend

# Créer un utilisateur dédié (optionnel mais recommandé)
useradd -r -s /bin/false leads-app
```

---

## 🐍 ÉTAPE 5 : Déployer le Backend (FastAPI)

### 5.1 Copier les fichiers backend

```bash
cd /var/www/leads-system/backend

# Créer le fichier server.py
nano server.py
# → Collez le contenu du fichier backend/server.py
```

### 5.2 Créer le fichier .env

```bash
nano .env
```

Contenu du `.env` :
```
MONGO_URL=mongodb://localhost:27017
DB_NAME=leads_production
CORS_ORIGINS=https://votre-domaine.fr,https://admin.votre-domaine.fr
```

### 5.3 Créer le fichier requirements.txt

```bash
nano requirements.txt
```

Contenu :
```
fastapi==0.109.0
uvicorn[standard]==0.27.0
motor==3.3.2
python-dotenv==1.0.0
pydantic==2.5.3
httpx==0.26.0
```

### 5.4 Installer les dépendances Python

```bash
# Créer un environnement virtuel
python3 -m venv venv

# Activer l'environnement
source venv/bin/activate

# Installer les dépendances
pip install --upgrade pip
pip install -r requirements.txt

# Tester que ça marche
python -c "import fastapi; print('FastAPI OK')"
```

### 5.5 Créer le service systemd pour le backend

```bash
nano /etc/systemd/system/leads-backend.service
```

Contenu :
```ini
[Unit]
Description=Leads Backend FastAPI
After=network.target mongod.service

[Service]
Type=simple
User=root
WorkingDirectory=/var/www/leads-system/backend
Environment="PATH=/var/www/leads-system/backend/venv/bin"
ExecStart=/var/www/leads-system/backend/venv/bin/uvicorn server:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 5.6 Démarrer le backend

```bash
# Recharger systemd
systemctl daemon-reload

# Démarrer le service
systemctl start leads-backend
systemctl enable leads-backend

# Vérifier le statut
systemctl status leads-backend

# Voir les logs en cas de problème
journalctl -u leads-backend -f
```

### 5.7 Tester le backend

```bash
curl http://localhost:8001/api/
# Doit retourner : {"message":"Hello World"}
```

---

## ⚛️ ÉTAPE 6 : Déployer le Frontend (React)

### 6.1 Copier les fichiers frontend

```bash
cd /var/www/leads-system/frontend

# Option A : Cloner depuis git (si vous avez un repo)
# git clone https://votre-repo.git .

# Option B : Copier manuellement les fichiers
# Uploadez vos fichiers via SFTP ou créez-les manuellement
```

### 6.2 Créer le fichier .env pour la production

```bash
nano .env
```

Contenu :
```
REACT_APP_BACKEND_URL=https://api.votre-domaine.fr
```

### 6.3 Installer et builder

```bash
# Installer les dépendances
yarn install

# Builder pour la production
yarn build

# Le dossier 'build' contient le site statique prêt à servir
ls -la build/
```

---

## 🌐 ÉTAPE 7 : Configurer Nginx

### 7.1 Installer Nginx

```bash
apt install -y nginx
```

### 7.2 Créer la configuration Nginx

```bash
nano /etc/nginx/sites-available/leads-system
```

Contenu :
```nginx
# Redirection HTTP vers HTTPS
server {
    listen 80;
    server_name votre-domaine.fr api.votre-domaine.fr admin.votre-domaine.fr;
    return 301 https://$server_name$request_uri;
}

# Frontend - Formulaire principal
server {
    listen 443 ssl http2;
    server_name votre-domaine.fr;

    # SSL (sera configuré par Certbot)
    ssl_certificate /etc/letsencrypt/live/votre-domaine.fr/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/votre-domaine.fr/privkey.pem;

    root /var/www/leads-system/frontend/build;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache pour les assets statiques
    location /static/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}

# Backend API
server {
    listen 443 ssl http2;
    server_name api.votre-domaine.fr;

    ssl_certificate /etc/letsencrypt/live/votre-domaine.fr/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/votre-domaine.fr/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
    }
}

# Dashboard Admin (même build, route différente)
server {
    listen 443 ssl http2;
    server_name admin.votre-domaine.fr;

    ssl_certificate /etc/letsencrypt/live/votre-domaine.fr/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/votre-domaine.fr/privkey.pem;

    root /var/www/leads-system/frontend/build;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

### 7.3 Activer la configuration

```bash
# Créer le lien symbolique
ln -s /etc/nginx/sites-available/leads-system /etc/nginx/sites-enabled/

# Supprimer la config par défaut
rm /etc/nginx/sites-enabled/default

# Tester la configuration
nginx -t

# Si OK, redémarrer Nginx
systemctl restart nginx
systemctl enable nginx
```

---

## 🔒 ÉTAPE 8 : Configurer SSL avec Certbot

```bash
# Installer Certbot
apt install -y certbot python3-certbot-nginx

# Obtenir les certificats SSL
certbot --nginx -d votre-domaine.fr -d api.votre-domaine.fr -d admin.votre-domaine.fr

# Suivre les instructions (entrer votre email, accepter les conditions)

# Vérifier le renouvellement automatique
certbot renew --dry-run
```

---

## 🔥 ÉTAPE 9 : Configurer le Firewall

```bash
# Installer UFW si pas déjà fait
apt install -y ufw

# Configurer les règles
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp

# Activer le firewall
ufw enable

# Vérifier le statut
ufw status
```

---

## ✅ ÉTAPE 10 : Vérification finale

### 10.1 Vérifier tous les services

```bash
# MongoDB
systemctl status mongod

# Backend
systemctl status leads-backend

# Nginx
systemctl status nginx

# Tous les services doivent être "active (running)"
```

### 10.2 Tester les URLs

```bash
# Tester le backend
curl https://api.votre-domaine.fr/api/
# Doit retourner : {"message":"Hello World"}

# Tester le frontend
curl -I https://votre-domaine.fr
# Doit retourner : HTTP/2 200

# Tester le dashboard admin
curl -I https://admin.votre-domaine.fr
# Doit retourner : HTTP/2 200
```

### 10.3 Tester un envoi de lead

```bash
curl -X POST "https://api.votre-domaine.fr/api/submit-lead" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "0612345678",
    "nom": "Test Deploiement",
    "email": "test@test.com",
    "departement": "75",
    "form_id": "test-deploy",
    "form_name": "Test Deploiement"
  }'
```

---

## 🔧 Commandes utiles

### Logs

```bash
# Logs du backend
journalctl -u leads-backend -f

# Logs Nginx
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# Logs MongoDB
tail -f /var/log/mongodb/mongod.log
```

### Redémarrage

```bash
# Redémarrer le backend
systemctl restart leads-backend

# Redémarrer Nginx
systemctl restart nginx

# Redémarrer MongoDB
systemctl restart mongod
```

### Mise à jour du code

```bash
# Backend
cd /var/www/leads-system/backend
# Modifier les fichiers...
systemctl restart leads-backend

# Frontend
cd /var/www/leads-system/frontend
# Modifier les fichiers...
yarn build
# Pas besoin de redémarrer Nginx, les fichiers statiques sont servis directement
```

---

## 📊 Accès final

| Service | URL |
|---------|-----|
| **Formulaire** | https://votre-domaine.fr |
| **Dashboard Admin** | https://admin.votre-domaine.fr/admin |
| **API Backend** | https://api.votre-domaine.fr/api |

---

## ⚠️ Notes importantes

1. **Remplacez `votre-domaine.fr`** par votre vrai domaine partout dans ce guide
2. **Sauvegardez régulièrement** la base MongoDB :
   ```bash
   mongodump --out /backup/mongodb/$(date +%Y%m%d)
   ```
3. **Configurez les DNS** dans Hostinger :
   - `votre-domaine.fr` → `72.60.189.23`
   - `api.votre-domaine.fr` → `72.60.189.23`
   - `admin.votre-domaine.fr` → `72.60.189.23`

---

## 🆘 En cas de problème

1. **Backend ne démarre pas** :
   ```bash
   journalctl -u leads-backend -n 50
   # Vérifier les erreurs Python
   ```

2. **Erreur 502 Bad Gateway** :
   ```bash
   # Le backend n'est pas accessible
   systemctl status leads-backend
   curl http://localhost:8001/api/
   ```

3. **Erreur SSL** :
   ```bash
   # Regénérer le certificat
   certbot certonly --nginx -d votre-domaine.fr
   ```

4. **MongoDB ne démarre pas** :
   ```bash
   journalctl -u mongod -n 50
   # Vérifier l'espace disque
   df -h
   ```
