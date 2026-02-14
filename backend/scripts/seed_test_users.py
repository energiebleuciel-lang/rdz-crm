"""
RDZ CRM - Seed Test Users (dev/staging only)
Creates 7 test accounts with predictable credentials.
Run: python scripts/seed_test_users.py
Reset: python scripts/seed_test_users.py --reset
"""

import asyncio
import sys
from motor.motor_asyncio import AsyncIOMotorClient
import hashlib
import uuid

MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"

# Same password for all test accounts
TEST_PASSWORD = "RdzTest2026!"

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# Permission presets (mirror of services/permissions.py)
ALL_KEYS = [
    "dashboard.view", "leads.view", "leads.edit_status", "leads.add_note", "leads.delete",
    "clients.view", "clients.create", "clients.edit", "clients.delete",
    "commandes.view", "commandes.create", "commandes.edit_quota", "commandes.edit_lb_target",
    "commandes.activate_pause", "commandes.delete",
    "deliveries.view", "deliveries.resend",
    "billing.view", "billing.manage",
    "departements.view", "activity.view",
    "settings.access", "providers.access", "users.manage", "monitoring.lb.view",
]

PRESETS = {
    "super_admin": {k: True for k in ALL_KEYS},
    "admin": {
        **{k: True for k in ALL_KEYS},
        "users.manage": False,
        "monitoring.lb.view": False,
    },
    "ops": {
        "dashboard.view": True,
        "leads.view": True, "leads.edit_status": True, "leads.add_note": True, "leads.delete": False,
        "clients.view": True, "clients.create": False, "clients.edit": False, "clients.delete": False,
        "commandes.view": True, "commandes.create": False, "commandes.edit_quota": True,
        "commandes.edit_lb_target": True, "commandes.activate_pause": True, "commandes.delete": False,
        "deliveries.view": True, "deliveries.resend": True,
        "billing.view": False, "billing.manage": False,
        "departements.view": True, "activity.view": False,
        "settings.access": False, "providers.access": False, "users.manage": False, "monitoring.lb.view": False,
    },
    "viewer": {
        "dashboard.view": True,
        "leads.view": True, "leads.edit_status": False, "leads.add_note": False, "leads.delete": False,
        "clients.view": True, "clients.create": False, "clients.edit": False, "clients.delete": False,
        "commandes.view": True, "commandes.create": False, "commandes.edit_quota": False,
        "commandes.edit_lb_target": False, "commandes.activate_pause": False, "commandes.delete": False,
        "deliveries.view": True, "deliveries.resend": False,
        "billing.view": False, "billing.manage": False,
        "departements.view": True, "activity.view": False,
        "settings.access": False, "providers.access": False, "users.manage": False, "monitoring.lb.view": False,
    },
}

TEST_USERS = [
    {"email": "superadmin@test.local",  "nom": "Super Admin Test", "entity": "ZR7", "role": "super_admin"},
    {"email": "admin_zr7@test.local",   "nom": "Admin ZR7",       "entity": "ZR7", "role": "admin"},
    {"email": "ops_zr7@test.local",     "nom": "OPS ZR7",         "entity": "ZR7", "role": "ops"},
    {"email": "viewer_zr7@test.local",  "nom": "Viewer ZR7",      "entity": "ZR7", "role": "viewer"},
    {"email": "admin_mdl@test.local",   "nom": "Admin MDL",       "entity": "MDL", "role": "admin"},
    {"email": "ops_mdl@test.local",     "nom": "OPS MDL",         "entity": "MDL", "role": "ops"},
    {"email": "viewer_mdl@test.local",  "nom": "Viewer MDL",      "entity": "MDL", "role": "viewer"},
]


async def reset(db):
    """Delete all test.local users"""
    result = await db.users.delete_many({"email": {"$regex": "@test\\.local$"}})
    await db.sessions.delete_many({"user_id": {"$in": []}})
    print(f"Deleted {result.deleted_count} test users")


async def seed(db):
    """Create/update test users"""
    for u in TEST_USERS:
        existing = await db.users.find_one({"email": u["email"]})
        perms = PRESETS[u["role"]]
        doc = {
            "email": u["email"],
            "password": hash_password(TEST_PASSWORD),
            "nom": u["nom"],
            "entity": u["entity"],
            "role": u["role"],
            "permissions": perms,
            "is_active": True,
        }
        if existing:
            await db.users.update_one({"email": u["email"]}, {"$set": doc})
            print(f"  Updated: {u['email']} ({u['role']}/{u['entity']})")
        else:
            doc["id"] = str(uuid.uuid4())
            doc["created_at"] = "2026-02-14T00:00:00+00:00"
            await db.users.insert_one(doc)
            print(f"  Created: {u['email']} ({u['role']}/{u['entity']})")


async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    if "--reset" in sys.argv:
        await reset(db)
        print("Reset complete. Run without --reset to re-seed.")
    else:
        await reset(db)
        await seed(db)
        print(f"\n7 test users seeded. Password for all: {TEST_PASSWORD}")
        print("Reset: python scripts/seed_test_users.py --reset")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
