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
    Valide un numéro de téléphone français.
    Règles:
    - 10 chiffres
    - Commence par 0
    - Pas de suite (0123456789)
    - Pas de répétition (0666666666)
    
    Returns: (is_valid, cleaned_phone_or_error)
    """
    # Nettoyer
    digits = ''.join(filter(str.isdigit, phone))
    
    # Ajouter 0 si 9 chiffres
    if len(digits) == 9 and not digits.startswith('0'):
        digits = '0' + digits
    
    # Règle 1: 10 chiffres
    if len(digits) != 10:
        return False, "Le téléphone doit contenir 10 chiffres"
    
    # Règle 2: Commence par 0
    if not digits.startswith('0'):
        return False, "Le téléphone doit commencer par 0"
    
    # Règle 3: Pas de suite
    if digits in "0123456789" or digits in "9876543210":
        return False, "Numéro invalide (suite)"
    
    # Vérifier suite par paires (01 02 03 04 05)
    is_pair_sequence = True
    for i in range(0, 8, 2):
        curr = int(digits[i:i+2])
        next_val = int(digits[i+2:i+4])
        if abs(next_val - curr) != 1:
            is_pair_sequence = False
            break
    if is_pair_sequence:
        return False, "Numéro invalide (suite)"
    
    # Règle 4: Pas de répétition (8+ chiffres identiques après le 0)
    first_digit = digits[1]
    same_count = sum(1 for d in digits[1:] if d == first_digit)
    if same_count >= 8:
        return False, "Numéro invalide (répétition)"
    
    return True, digits
