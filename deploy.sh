#!/bin/bash
# Script de déploiement automatique EnerSolar CRM pour Hostinger VPS
# Usage: ./deploy.sh <IP_VPS> <DOMAINE>

set -e

IP_VPS=$1
DOMAINE=$2

if [ -z "$IP_VPS" ] || [ -z "$DOMAINE" ]; then
    echo "Usage: ./deploy.sh <IP_VPS> <DOMAINE>"
    echo "Exemple: ./deploy.sh 192.168.1.100 crm.mondomaine.com"
    exit 1
fi

echo "🚀 Déploiement EnerSolar CRM sur $IP_VPS ($DOMAINE)"

# 1. Copier les fichiers
echo "📦 Copie des fichiers..."
ssh root@$IP_VPS "mkdir -p /var/www/enersolar-crm"
rsync -avz --exclude 'node_modules' --exclude 'venv' --exclude '__pycache__' --exclude '.git' \
    /app/backend /app/frontend root@$IP_VPS:/var/www/enersolar-crm/

# 2. Configuration sur le serveur
echo "⚙️ Configuration du serveur..."
ssh root@$IP_VPS << REMOTE_SCRIPT
set -e

# Mettre à jour .env frontend avec le bon domaine
echo "REACT_APP_BACKEND_URL=https://$DOMAINE" > /var/www/enersolar-crm/frontend/.env

# Mettre à jour .env backend
cat > /var/www/enersolar-crm/backend/.env << 'ENVFILE'
MONGO_URL="mongodb://localhost:27017"
DB_NAME="enersolar_crm"
CORS_ORIGINS="*"
ENVFILE

# Installer dépendances backend
cd /var/www/enersolar-crm/backend
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Installer dépendances frontend et build
cd /var/www/enersolar-crm/frontend
yarn install
yarn build

# Configurer Nginx
cat > /etc/nginx/sites-available/enersolar-crm << NGINX
server {
    listen 80;
    server_name $DOMAINE;
    
    root /var/www/enersolar-crm/frontend/build;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \\\$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \\\$host;
        proxy_set_header X-Real-IP \\\$remote_addr;
        proxy_set_header X-Forwarded-For \\\$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \\\$scheme;
    }

    location / {
        try_files \\\$uri \\\$uri/ /index.html;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/enersolar-crm /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# Configurer Supervisor
cat > /etc/supervisor/conf.d/enersolar-backend.conf << SUPERVISOR
[program:enersolar-backend]
command=/var/www/enersolar-crm/backend/venv/bin/uvicorn server:app --host 127.0.0.1 --port 8001 --workers 2
directory=/var/www/enersolar-crm/backend
user=root
autostart=true
autorestart=true
stdout_logfile=/var/log/enersolar-backend.log
stderr_logfile=/var/log/enersolar-backend-error.log
SUPERVISOR

supervisorctl reread
supervisorctl update
supervisorctl restart enersolar-backend

echo "✅ Déploiement terminé!"
REMOTE_SCRIPT

echo ""
echo "🎉 Déploiement terminé!"
echo ""
echo "📋 Prochaines étapes:"
echo "1. Configurer le DNS: $DOMAINE -> $IP_VPS"
echo "2. Installer SSL: ssh root@$IP_VPS 'certbot --nginx -d $DOMAINE'"
echo "3. Tester: curl http://$IP_VPS/api/health"
echo ""
