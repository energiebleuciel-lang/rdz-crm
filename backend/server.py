"""
RDZ CRM - API Backend
Version 4.0 - Architecture Multi-Tenant Clean

CRON JOBS:
- Livraison quotidienne: 09h30 Europe/Paris
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import pytz

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("rdz_crm")

scheduler = None
PARIS_TZ = pytz.timezone("Europe/Paris")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler

    logger.info("RDZ CRM v4.0 - Architecture Multi-Tenant")

    from config import db

    try:
        # Index utilisateurs/sessions (auth)
        await db.users.create_index("email", unique=True, background=True)
        await db.sessions.create_index("token", background=True)
        await db.sessions.create_index("expires_at", background=True)

        # Index leads
        await db.leads.create_index("phone", background=True)
        await db.leads.create_index("nom", background=True)
        await db.leads.create_index("departement", background=True)
        await db.leads.create_index("entity", background=True)
        await db.leads.create_index("produit", background=True)
        await db.leads.create_index("status", background=True)
        await db.leads.create_index("register_date", background=True)

        # Index composite doublon 30 jours (phone + produit + client + date)
        await db.leads.create_index(
            [("phone", 1), ("produit", 1), ("delivered_to_client_id", 1), ("delivered_at", -1)],
            background=True,
            name="idx_duplicate_30_days"
        )

        # Index composite routing (entity + produit + departement + status)
        await db.leads.create_index(
            [("entity", 1), ("produit", 1), ("departement", 1), ("status", 1)],
            background=True,
            name="idx_routing"
        )

        # Index LB (entity + status + is_lb)
        await db.leads.create_index(
            [("entity", 1), ("status", 1), ("is_lb", 1)],
            background=True,
            name="idx_lb"
        )

        # Index anti double-submit (session + phone + created_at)
        await db.leads.create_index(
            [("session_id", 1), ("phone", 1), ("created_at", -1)],
            background=True,
            name="idx_double_submit_detection"
        )

        # Index clients (entity obligatoire)
        await db.clients.create_index("entity", background=True)
        await db.clients.create_index(
            [("entity", 1), ("email", 1)],
            unique=True,
            background=True,
            name="idx_client_entity_email"
        )

        # Index commandes (entity + client + produit + active)
        await db.commandes.create_index("entity", background=True)
        await db.commandes.create_index(
            [("entity", 1), ("client_id", 1), ("produit", 1), ("active", 1)],
            background=True,
            name="idx_commande_routing"
        )

        # Index delivery batches
        await db.delivery_batches.create_index("entity", background=True)
        await db.delivery_batches.create_index("sent_at", background=True)

        # Index delivery reports
        await db.delivery_reports.create_index("run_at", background=True)

        # Index providers
        await db.providers.create_index("slug", unique=True, background=True)
        await db.providers.create_index("api_key", unique=True, background=True)
        await db.providers.create_index("entity", background=True)

        # Index tracking (LP/Form)
        await db.tracking.create_index("lp_code", background=True)
        await db.tracking.create_index("form_code", background=True)
        await db.tracking.create_index("session_id", background=True)

        # Index sessions visiteurs
        await db.visitor_sessions.create_index("id", unique=True, background=True)
        await db.visitor_sessions.create_index("visitor_id", background=True)
        await db.visitor_sessions.create_index("lp_code", background=True)
        await db.visitor_sessions.create_index("status", background=True)


        # Billing indexes
        await db.products.create_index("code", unique=True, background=True)
        await db.client_pricing.create_index("client_id", unique=True, background=True)
        await db.client_product_pricing.create_index(
            [("client_id", 1), ("product_code", 1)], unique=True, background=True
        )
        await db.billing_credits.create_index(
            [("client_id", 1), ("week_key", 1)], background=True
        )
        await db.prepayment_balances.create_index(
            [("client_id", 1), ("product_code", 1)], unique=True, background=True
        )
        await db.billing_ledger.create_index("week_key", background=True)
        await db.billing_ledger.create_index(
            [("week_key", 1), ("client_id", 1), ("product_code", 1)], background=True
        )
        await db.billing_records.create_index(
            [("week_key", 1), ("client_id", 1), ("product_code", 1), ("order_id", 1)], background=True
        )
        await db.billing_records.create_index("status", background=True)

        await db.entity_transfer_pricing.create_index(
            [("from_entity", 1), ("to_entity", 1), ("product_code", 1)], unique=True, background=True
        )
        await db.interfacturation_records.create_index(
            [("week_key", 1), ("from_entity", 1), ("to_entity", 1)], background=True
        )

        logger.info("Index MongoDB OK")
    except Exception as e:
        logger.warning(f"Index MongoDB: {str(e)}")

    # Scheduler
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
        from services.daily_delivery import run_daily_delivery

        scheduler = AsyncIOScheduler(timezone=PARIS_TZ)

        # Livraison quotidienne - 09h30 Europe/Paris
        scheduler.add_job(
            run_daily_delivery,
            CronTrigger(hour=9, minute=30, timezone=PARIS_TZ),
            id="daily_delivery",
            name="Livraison quotidienne 09h30",
            replace_existing=True
        )

        scheduler.start()
        logger.info("Scheduler: Livraison quotidienne 09h30 Europe/Paris")

    except Exception as e:
        logger.warning(f"Scheduler: {str(e)}")

    yield

    if scheduler:
        scheduler.shutdown()
        logger.info("Scheduler arrete")


app = FastAPI(
    title="RDZ CRM",
    description="CRM Multi-Tenant pour gestion et distribution de leads (ZR7 / MDL)",
    version="4.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
from routes import auth, public, clients, commandes, settings, providers, deliveries, leads, event_log, departements, billing

app.include_router(auth.router, prefix="/api")
app.include_router(public.router, prefix="/api")
app.include_router(clients.router, prefix="/api")
app.include_router(commandes.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(providers.router, prefix="/api")
app.include_router(deliveries.router, prefix="/api")
app.include_router(leads.router, prefix="/api")
app.include_router(event_log.router, prefix="/api")
app.include_router(departements.router, prefix="/api")
app.include_router(billing.router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": "RDZ CRM API",
        "version": "4.0.0",
        "status": "running",
        "entities": ["ZR7", "MDL"],
        "features": {
            "daily_delivery": "09:30 Europe/Paris",
            "duplicate_detection": "30 days rule",
            "lb_system": "8 days threshold"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
