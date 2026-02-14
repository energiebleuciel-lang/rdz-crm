"""
Configuration et utilitaires partagés
"""

import os
import hashlib
import secrets
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

# Charger .env
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')  # Default to test_database

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

print(f"[CONFIG] Using database: {DB_NAME}")

# Backend URL (pour les scripts de tracking)
BACKEND_URL = os.environ.get('BACKEND_URL')
if not BACKEND_URL:
    raise ValueError("BACKEND_URL environment variable is required")


# ==================== HELPERS ====================

def hash_password(password: str) -> str:
    """Hash un mot de passe avec SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_token() -> str:
    """Génère un token de session sécurisé"""
    return secrets.token_urlsafe(32)

def generate_api_key() -> str:
    """Génère une clé API"""
    return f"crm_{secrets.token_urlsafe(32)}"

def now_iso() -> str:
    """Retourne la date/heure actuelle en ISO"""
    return datetime.now(timezone.utc).isoformat()

def timestamp() -> int:
    """Retourne le timestamp actuel"""
    return int(datetime.now(timezone.utc).timestamp())

def validate_phone_fr(phone: str) -> tuple[bool, str]:
    """
    LEGACY wrapper — calls normalize_phone_fr internally.
    Returns: (is_valid, cleaned_phone_or_error)
    """
    status, normalized, quality = normalize_phone_fr(phone)
    if status == "invalid":
        return False, normalized  # normalized contains the error message
    return True, normalized


def normalize_phone_fr(phone: str) -> tuple[str, str, str]:
    """
    Normalise et valide un numéro de téléphone français.
    FORMAT UNIQUE EN BASE: 0XXXXXXXXX (10 chiffres, commence par 0)

    Pipeline:
      1. Supprimer tous les caractères non numériques
      2. Gestion indicatif France (+33, 0033, 33)
      3. Validation stricte (longueur=10, commence par 0)
      4. Blocage faux numéros évidents
      5. Détection patterns suspects

    Returns: (status, normalized_or_error, quality)
      status:  "valid" | "invalid"
      normalized_or_error: "0612345678" si valid, message d'erreur si invalid
      quality: "valid" | "suspicious" | "invalid"
    """
    if not phone or not phone.strip():
        return "invalid", "Numéro vide", "invalid"

    # ═══════ ÉTAPE 1: Nettoyer (garder uniquement les chiffres) ═══════
    digits = ''.join(filter(str.isdigit, phone))

    if not digits:
        return "invalid", "Aucun chiffre détecté", "invalid"

    # ═══════ ÉTAPE 2: Gestion indicatif France ═══════
    # 0033XXXXXXXXX → 0XXXXXXXXX
    if digits.startswith("0033") and len(digits) >= 13:
        digits = "0" + digits[4:]

    # 33XXXXXXXXX (11 chiffres commençant par 33) → 0XXXXXXXXX
    if digits.startswith("33") and len(digits) == 11:
        digits = "0" + digits[2:]

    # 6XXXXXXXX ou 7XXXXXXXX (9 chiffres mobile sans le 0) → 0XXXXXXXXX
    if len(digits) == 9 and digits[0] in ("6", "7"):
        digits = "0" + digits

    # ═══════ ÉTAPE 3: Validation stricte ═══════
    if len(digits) != 10:
        return "invalid", f"Format invalide: {len(digits)} chiffres (10 requis)", "invalid"

    if not digits.startswith("0"):
        return "invalid", "Le numéro doit commencer par 0", "invalid"

    # ═══════ ÉTAPE 4: Blocage faux numéros évidents ═══════
    BLOCKED_NUMBERS = {
        "0612345678",  # Numéro test ultra commun
    }

    # 10 chiffres identiques (0000000000, 1111111111, etc.)
    if len(set(digits)) == 1:
        return "invalid", f"Numéro bloqué: {digits} (chiffres identiques)", "invalid"

    # Séquences ascendantes/descendantes complètes
    BLOCKED_SEQUENCES = {
        "0123456789",
        "1234567890",
        "0987654321",
        "9876543210",
    }
    if digits in BLOCKED_SEQUENCES:
        return "invalid", f"Numéro bloqué: séquence interdite", "invalid"

    if digits in BLOCKED_NUMBERS:
        return "invalid", f"Numéro bloqué: numéro test", "invalid"

    # ═══════ ÉTAPE 5: Détection patterns suspects ═══════
    quality = "valid"

    # Alternance simple répétée (ex: 0606060606, 0611111111)
    after_prefix = digits[2:]  # Les 8 derniers chiffres (après 0X)

    # Pattern: même chiffre 7+ fois dans les 8 derniers (ex: 0611111111)
    from collections import Counter
    counts = Counter(after_prefix)
    if counts.most_common(1)[0][1] >= 7:
        quality = "suspicious"

    # Alternance AB AB AB AB (ex: 0606060606, 0678787878)
    if len(after_prefix) == 8:
        pair = after_prefix[:2]
        if pair * 4 == after_prefix:
            quality = "suspicious"

    return "valid", digits, quality
