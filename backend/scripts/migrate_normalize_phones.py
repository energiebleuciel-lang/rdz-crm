"""
RDZ CRM — Migration: Normalize all phone numbers in leads collection.
Run: cd /app/backend && python3 scripts/migrate_normalize_phones.py
"""

import asyncio
import sys
sys.path.insert(0, "/app/backend")

from motor.motor_asyncio import AsyncIOMotorClient
from config import normalize_phone_fr


async def migrate():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["test_database"]

    total = await db.leads.count_documents({})
    print(f"Total leads in DB: {total}")

    modified = 0
    invalid_count = 0
    suspicious_count = 0
    already_ok = 0
    errors = []

    cursor = db.leads.find({}, {"_id": 0, "id": 1, "phone": 1, "phone_quality": 1})

    async for lead in cursor:
        lead_id = lead.get("id")
        raw_phone = lead.get("phone", "")

        if not raw_phone:
            # No phone — mark as invalid quality if not already set
            if lead.get("phone_quality") != "invalid":
                await db.leads.update_one(
                    {"id": lead_id},
                    {"$set": {"phone_quality": "invalid"}}
                )
                invalid_count += 1
            continue

        status, normalized, quality = normalize_phone_fr(raw_phone)

        if status == "invalid":
            if lead.get("phone_quality") != "invalid":
                await db.leads.update_one(
                    {"id": lead_id},
                    {"$set": {"phone_quality": "invalid"}}
                )
            invalid_count += 1
            errors.append({"id": lead_id[:8], "phone": raw_phone, "reason": normalized})
            continue

        update = {}

        # Normalize the phone if it differs
        if raw_phone != normalized:
            update["phone"] = normalized
            modified += 1

        # Set quality if missing or different
        if lead.get("phone_quality") != quality:
            update["phone_quality"] = quality

        if quality == "suspicious":
            suspicious_count += 1
        else:
            already_ok += 1

        if update:
            await db.leads.update_one({"id": lead_id}, {"$set": update})

    client.close()

    print("\n════════════════════════════════════")
    print("  MIGRATION REPORT")
    print("════════════════════════════════════")
    print(f"  Total leads:      {total}")
    print(f"  Phones modified:  {modified}")
    print(f"  Already OK:       {already_ok}")
    print(f"  Suspicious:       {suspicious_count}")
    print(f"  Invalid:          {invalid_count}")
    print("════════════════════════════════════")

    if errors and len(errors) <= 20:
        print("\nInvalid phones (sample):")
        for e in errors[:20]:
            print(f"  lead={e['id']}... phone={e['phone']} reason={e['reason']}")

    return {
        "total": total,
        "modified": modified,
        "already_ok": already_ok,
        "suspicious": suspicious_count,
        "invalid": invalid_count,
    }


if __name__ == "__main__":
    asyncio.run(migrate())
