"""
RDZ CRM - API Backend
Version 3.0 - Architecture Multi-Tenant

Démarre avec:
    uvicorn server:app --host 0.0.0.0 --port 8001 --reload

CRON JOBS:
- Livraison quotidienne: 09h30 Europe/Paris
- Vérification nocturne: 03h00 UTC
- Queue processing: toutes les 5 minutes
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import asyncio
import pytz

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("rdz_crm")

# Variable pour le scheduler
scheduler = None

# Timezone Paris pour le cron
PARIS_TZ = pytz.timezone("Europe/Paris")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application"""
    global scheduler
    
    logger.info("🚀 RDZ CRM v3.0 démarré - Architecture Multi-Tenant")
    
    # Créer les index MongoDB
    from config import db
    
    try:
        # Index utilisateurs/sessions
        await db.users.create_index("email", unique=True, background=True)
        await db.sessions.create_index("token", background=True)
        await db.sessions.create_index("expires_at", background=True)
        
        # Index accounts/lps/forms
        await db.accounts.create_index("name", background=True)
        await db.lps.create_index("code", background=True)
        await db.forms.create_index("code", background=True)
        
        # Index leads optimisés
        await db.leads.create_index("phone", background=True)
        await db.leads.create_index("form_code", background=True)
        await db.leads.create_index("created_at", background=True)
        await db.leads.create_index("entity", background=True)
        await db.leads.create_index("status", background=True)
        
        # Index composite pour doublon 30 jours (phone + product + client + date)
        await db.leads.create_index(
            [("phone", 1), ("product_type", 1), ("delivered_to_client_id", 1), ("delivered_at", -1)],
            background=True,
            name="idx_duplicate_30_days"
        )
        
        # Index composite pour routing (entity + product + dept + status)
        await db.leads.create_index(
            [("entity", 1), ("product_type", 1), ("departement", 1), ("status", 1)],
            background=True,
            name="idx_routing"
        )
        
        # Index pour LB (entity + status + is_lb)
        await db.leads.create_index(
            [("entity", 1), ("status", 1), ("is_lb", 1)],
            background=True,
            name="idx_lb"
        )
        
        # Index pour double-submit (session + phone + created_at)
        await db.leads.create_index(
            [("session_id", 1), ("phone", 1), ("created_at", -1)],
            background=True,
            name="idx_double_submit_detection"
        )
        
        # Index tracking
        await db.tracking.create_index("lp_code", background=True)
        await db.tracking.create_index("form_code", background=True)
        await db.tracking.create_index("session_id", background=True)
        
        # Index sessions visiteurs
        await db.visitor_sessions.create_index("id", unique=True, background=True)
        await db.visitor_sessions.create_index("visitor_id", background=True)
        await db.visitor_sessions.create_index("lp_code", background=True)
        await db.visitor_sessions.create_index("form_code", background=True)
        await db.visitor_sessions.create_index("status", background=True)
        
        # Index clients (entity obligatoire)
        await db.clients.create_index("entity", background=True)
        await db.clients.create_index(
            [("entity", 1), ("email", 1)],
            unique=True,
            background=True,
            name="idx_client_entity_email"
        )
        
        # Index commandes (entity + client + product)
        await db.commandes.create_index("entity", background=True)
        await db.commandes.create_index(
            [("entity", 1), ("client_id", 1), ("product_type", 1), ("active", 1)],
            background=True,
            name="idx_commande_routing"
        )
        
        # Index delivery batches
        await db.delivery_batches.create_index("entity", background=True)
        await db.delivery_batches.create_index("sent_at", background=True)
        
        # Index queue
        await db.lead_queue.create_index("status", background=True)
        await db.lead_queue.create_index("next_retry_at", background=True)
        
        # Index reports
        await db.verification_reports.create_index("run_at", background=True)
        await db.delivery_reports.create_index("run_at", background=True)
        
        logger.info("✅ Index MongoDB créés/vérifiés")
    except Exception as e:
        logger.warning(f"⚠️ Index MongoDB: {str(e)}")
    
    # Démarrer le scheduler
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
        from services.nightly_verification import verify_and_retry_leads
        from services.lead_sender import process_queue
        from services.daily_delivery import run_daily_delivery
        
        scheduler = AsyncIOScheduler(timezone=PARIS_TZ)
        
        # 🚀 LIVRAISON QUOTIDIENNE - 09h30 Europe/Paris
        scheduler.add_job(
            run_daily_delivery,
            CronTrigger(hour=9, minute=30, timezone=PARIS_TZ),
            id="daily_delivery",
            name="Livraison quotidienne 09h30",
            replace_existing=True
        )
        
        # Vérification nocturne à 3h du matin (UTC)
        scheduler.add_job(
            verify_and_retry_leads,
            CronTrigger(hour=3, minute=0),
            id="nightly_verification",
            name="Vérification nocturne des leads",
            replace_existing=True
        )
        
        # Traitement de la queue toutes les 5 minutes
        scheduler.add_job(
            process_queue,
            'interval',
            minutes=5,
            id="queue_processor",
            name="Traitement file d'attente",
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("✅ Scheduler démarré:")
        logger.info("   - Livraison quotidienne: 09h30 Europe/Paris")
        logger.info("   - Vérification nocturne: 03h00 UTC")
        logger.info("   - Queue processing: toutes les 5 min")
        
    except Exception as e:
        logger.warning(f"⚠️ Scheduler: {str(e)}")
    
    yield  # L'application tourne
    
    # Arrêt propre
    if scheduler:
        scheduler.shutdown()
        logger.info("🛑 Scheduler arrêté")


# Créer l'app avec lifespan
app = FastAPI(
    title="RDZ CRM",
    description="CRM Multi-Tenant pour gestion et distribution de leads (ZR7 / MDL)",
    version="3.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== IMPORT DES ROUTES ====================

from routes import auth, accounts, crms, lps, forms, leads, queue, config, stats, billing, verification, public, media, quality_mappings, monitoring
from routes import clients
from routes import commandes_v2 as commandes

# Routes avec préfixe /api
app.include_router(auth.router, prefix="/api")
app.include_router(accounts.router, prefix="/api")
app.include_router(crms.router, prefix="/api")
app.include_router(lps.router, prefix="/api")
app.include_router(forms.router, prefix="/api")
app.include_router(leads.router, prefix="/api")
app.include_router(queue.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
app.include_router(verification.router, prefix="/api")
app.include_router(public.router, prefix="/api")
app.include_router(media.router, prefix="/api")
app.include_router(quality_mappings.router, prefix="/api")
app.include_router(monitoring.router, prefix="/api")
# Nouvelles routes RDZ v3
app.include_router(clients.router, prefix="/api")
app.include_router(commandes.router, prefix="/api")

# ==================== ROUTE RACINE ====================

@app.get("/")
async def root():
    return {
        "name": "RDZ CRM API",
        "version": "3.0.0",
        "status": "running",
        "docs": "/docs",
        "entities": ["ZR7", "MDL"],
        "features": {
            "daily_delivery": "09:30 Europe/Paris",
            "nightly_verification": "03:00 UTC",
            "queue_processing": "every 5 minutes",
            "duplicate_detection": "30 days rule",
            "lb_system": "8 days threshold"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
