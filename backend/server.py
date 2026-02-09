"""
EnerSolar CRM - API Backend
Version 2.0 - Architecture modulaire

Démarre avec:
    uvicorn server:app --host 0.0.0.0 --port 8001 --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import asyncio

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("enersolar")

# Variable pour le scheduler
scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application"""
    global scheduler
    
    logger.info("🚀 EnerSolar CRM v2.0 démarré")
    
    # Créer les index MongoDB
    from config import db
    
    try:
        await db.users.create_index("email", unique=True, background=True)
        await db.sessions.create_index("token", background=True)
        await db.sessions.create_index("expires_at", background=True)
        await db.accounts.create_index("name", background=True)
        await db.lps.create_index("code", background=True)
        await db.forms.create_index("code", background=True)
        await db.leads.create_index("phone", background=True)
        await db.leads.create_index("form_code", background=True)
        await db.leads.create_index("created_at", background=True)
        await db.tracking.create_index("lp_code", background=True)
        await db.tracking.create_index("form_code", background=True)
        await db.lead_queue.create_index("status", background=True)
        await db.lead_queue.create_index("next_retry_at", background=True)
        await db.verification_reports.create_index("run_at", background=True)
        logger.info("✅ Index MongoDB créés/vérifiés")
    except Exception as e:
        logger.warning(f"⚠️ Index MongoDB: {str(e)}")
    
    # Démarrer le scheduler pour la vérification nocturne
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
        from services.nightly_verification import verify_and_retry_leads
        
        scheduler = AsyncIOScheduler()
        
        # Vérification nocturne à 3h du matin (UTC)
        scheduler.add_job(
            verify_and_retry_leads,
            CronTrigger(hour=3, minute=0),
            id="nightly_verification",
            name="Vérification nocturne des leads",
            replace_existing=True
        )
        
        # Traitement de la queue toutes les 5 minutes
        from services.lead_sender import process_queue
        scheduler.add_job(
            process_queue,
            'interval',
            minutes=5,
            id="queue_processor",
            name="Traitement file d'attente",
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("✅ Scheduler démarré (vérification nocturne à 3h UTC)")
        
    except Exception as e:
        logger.warning(f"⚠️ Scheduler: {str(e)}")
    
    yield  # L'application tourne
    
    # Arrêt propre
    if scheduler:
        scheduler.shutdown()
        logger.info("🛑 Scheduler arrêté")


# Créer l'app avec lifespan
app = FastAPI(
    title="EnerSolar CRM",
    description="CRM de gestion de leads solaires",
    version="2.0.0",
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

from routes import auth, accounts, crms, lps, forms, leads, tracking, queue, config, commandes, stats, billing, verification

# Routes avec préfixe /api
app.include_router(auth.router, prefix="/api")
app.include_router(accounts.router, prefix="/api")
app.include_router(crms.router, prefix="/api")
app.include_router(lps.router, prefix="/api")
app.include_router(forms.router, prefix="/api")
app.include_router(leads.router, prefix="/api")
app.include_router(tracking.router, prefix="/api")
app.include_router(queue.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(commandes.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
app.include_router(verification.router, prefix="/api")

# ==================== ROUTE RACINE ====================

@app.get("/")
async def root():
    return {
        "name": "EnerSolar CRM API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "features": {
            "nightly_verification": "03:00 UTC",
            "queue_processing": "every 5 minutes"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
