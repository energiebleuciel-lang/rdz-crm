"""
EnerSolar CRM - API Backend
Version 2.0 - Architecture modulaire

Démarre avec:
    uvicorn server:app --host 0.0.0.0 --port 8001 --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("enersolar")

# Créer l'app
app = FastAPI(
    title="EnerSolar CRM",
    description="CRM de gestion de leads solaires",
    version="2.0.0"
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

from routes import auth, accounts, crms, lps, forms, leads, tracking, queue, config

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

# ==================== ROUTE RACINE ====================

@app.get("/")
async def root():
    return {
        "name": "EnerSolar CRM API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs"
    }


# ==================== STARTUP ====================

@app.on_event("startup")
async def startup():
    logger.info("🚀 EnerSolar CRM v2.0 démarré")
    
    # Créer les index MongoDB (ignorer si existent déjà)
    from config import db
    
    try:
        # Index sur les collections (background=True pour ne pas bloquer)
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
        logger.info("✅ Index MongoDB créés/vérifiés")
    except Exception as e:
        logger.warning(f"⚠️ Index MongoDB: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
