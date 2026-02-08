# 🚀 Guide de Déploiement EnerSolar CRM sur Hostinger VPS

## Prérequis
- Un VPS Hostinger (Ubuntu 22.04 recommandé)
- Un nom de domaine configuré (ex: crm.votredomaine.com)
- Accès SSH au serveur

---

## 1. Configuration du Serveur

### 1.1 Connexion SSH
```bash
ssh root@VOTRE_IP_VPS
```

### 1.2 Mise à jour du système
```bash
apt update && apt upgrade -y
```

### 1.3 Installation des dépendances
```bash
# Python 3.11+
apt install -y python3.11 python3.11-venv python3-pip

# Node.js 18+
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt install -y nodejs

# Yarn
npm install -g yarn

# Nginx (reverse proxy)
apt install -y nginx

# MongoDB
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg
echo "deb [ signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] http://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-7.0.list
apt update
apt install -y mongodb-org
systemctl start mongod
systemctl enable mongod

# Supervisor (gestion des processus)
apt install -y supervisor
```

---

## 2. Déploiement de l'Application

### 2.1 Créer la structure
```bash
mkdir -p /var/www/enersolar-crm
cd /var/www/enersolar-crm
```

### 2.2 Cloner ou copier les fichiers
```bash
# Option 1: Git
git clone VOTRE_REPO .

# Option 2: SCP depuis votre machine
# scp -r /app/* root@VOTRE_IP_VPS:/var/www/enersolar-crm/
```

### 2.3 Configuration Backend
```bash
cd /var/www/enersolar-crm/backend

# Créer environnement virtuel
python3.11 -m venv venv
source venv/bin/activate

# Installer dépendances
pip install -r requirements.txt

# Créer fichier .env
cat > .env << 'EOF'
MONGO_URL="mongodb://localhost:27017"
DB_NAME="enersolar_crm"
CORS_ORIGINS="*"
EOF
```

### 2.4 Configuration Frontend
```bash
cd /var/www/enersolar-crm/frontend

# Installer dépendances
yarn install

# Créer fichier .env (remplacer par votre domaine)
cat > .env << 'EOF'
REACT_APP_BACKEND_URL=https://crm.votredomaine.com
EOF

# Build pour production
yarn build
```

---

## 3. Configuration Supervisor

### 3.1 Backend (FastAPI)
```bash
cat > /etc/supervisor/conf.d/enersolar-backend.conf << 'EOF'
[program:enersolar-backend]
command=/var/www/enersolar-crm/backend/venv/bin/uvicorn server:app --host 127.0.0.1 --port 8001 --workers 2
directory=/var/www/enersolar-crm/backend
user=www-data
autostart=true
autorestart=true
stdout_logfile=/var/log/enersolar/backend.log
stderr_logfile=/var/log/enersolar/backend-error.log
environment=PATH="/var/www/enersolar-crm/backend/venv/bin"
EOF
```

### 3.2 Créer dossier logs
```bash
mkdir -p /var/log/enersolar
chown -R www-data:www-data /var/log/enersolar
chown -R www-data:www-data /var/www/enersolar-crm
```

### 3.3 Démarrer Supervisor
```bash
supervisorctl reread
supervisorctl update
supervisorctl start enersolar-backend
```

---

## 4. Configuration Nginx

### 4.1 Créer la configuration
```bash
cat > /etc/nginx/sites-available/enersolar-crm << 'EOF'
server {
    listen 80;
    server_name crm.votredomaine.com;  # REMPLACER PAR VOTRE DOMAINE

    # Frontend (fichiers statiques)
    root /var/www/enersolar-crm/frontend/build;
    index index.html;

    # Toutes les routes API vers le backend
    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Frontend SPA (React Router)
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
}
EOF
```

### 4.2 Activer le site
```bash
ln -s /etc/nginx/sites-available/enersolar-crm /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default  # Supprimer config par défaut
nginx -t  # Vérifier la config
systemctl reload nginx
```

---

## 5. SSL avec Let's Encrypt

```bash
# Installer Certbot
apt install -y certbot python3-certbot-nginx

# Obtenir certificat SSL
certbot --nginx -d crm.votredomaine.com

# Renouvellement automatique (déjà configuré par Certbot)
```

---

## 6. Sécurisation MongoDB (Production)

### 6.1 Créer un utilisateur admin
```bash
mongosh

use admin
db.createUser({
  user: "enersolar_admin",
  pwd: "MOT_DE_PASSE_FORT",  # CHANGER !
  roles: [{ role: "userAdminAnyDatabase", db: "admin" }]
})

use enersolar_crm
db.createUser({
  user: "enersolar_user",
  pwd: "AUTRE_MOT_DE_PASSE",  # CHANGER !
  roles: [{ role: "readWrite", db: "enersolar_crm" }]
})

exit
```

### 6.2 Activer l'authentification
```bash
# Éditer /etc/mongod.conf
nano /etc/mongod.conf

# Ajouter sous "security:"
security:
  authorization: enabled

# Redémarrer MongoDB
systemctl restart mongod
```

### 6.3 Mettre à jour .env backend
```bash
# /var/www/enersolar-crm/backend/.env
MONGO_URL="mongodb://enersolar_user:AUTRE_MOT_DE_PASSE@localhost:27017/enersolar_crm"
DB_NAME="enersolar_crm"
```

---

## 7. Commandes Utiles

```bash
# Voir les logs backend
tail -f /var/log/enersolar/backend.log

# Redémarrer le backend
supervisorctl restart enersolar-backend

# Redémarrer Nginx
systemctl reload nginx

# Vérifier MongoDB
mongosh --eval "db.stats()"

# Voir l'état des services
supervisorctl status
systemctl status nginx
systemctl status mongod
```

---

## 8. Checklist de Vérification

- [ ] MongoDB fonctionne : `mongosh --eval "db.stats()"`
- [ ] Backend fonctionne : `curl http://localhost:8001/api/health`
- [ ] Nginx fonctionne : `curl http://localhost`
- [ ] SSL actif : `curl https://crm.votredomaine.com`
- [ ] API accessible : `curl https://crm.votredomaine.com/api/health`

---

## 9. Migration des Données (Optionnel)

Si vous avez des données existantes :

```bash
# Export depuis le serveur source
mongodump --uri="mongodb://localhost:27017" --db=test_database --out=/tmp/backup

# Copier vers Hostinger
scp -r /tmp/backup root@VOTRE_IP_VPS:/tmp/

# Import sur Hostinger
mongorestore --uri="mongodb://localhost:27017" --db=enersolar_crm /tmp/backup/test_database
```

---

## Support

En cas de problème :
1. Vérifier les logs : `/var/log/enersolar/`
2. Vérifier Nginx : `/var/log/nginx/error.log`
3. Vérifier MongoDB : `/var/log/mongodb/mongod.log`
