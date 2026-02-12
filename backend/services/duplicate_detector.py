"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  SERVICE DE DÉTECTION DES DOUBLONS INTERNES RDZ                              ║
║                                                                              ║
║  Règles de détection:                                                        ║
║  - Critères: même téléphone + même département                               ║
║  - Fenêtre: 30 jours                                                         ║
║  - Protection anti double-submit (5 secondes)                                ║
║                                                                              ║
║  Comportements:                                                              ║
║  - Si déjà livré (sent_to_crm=True) dans les 30 jours → doublon_recent       ║
║  - Si existe mais non livré → non_livre (redistribuable)                     ║
║  - Si double-submit rapide (< 5s) → double_submit                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict, Any
from config import db

logger = logging.getLogger("duplicate_detector")

# Configuration
DUPLICATE_WINDOW_DAYS = 30  # Fenêtre de détection doublons
DOUBLE_SUBMIT_SECONDS = 5   # Protection anti double-clic


class DuplicateResult:
    """Résultat de la détection de doublon"""
    
    def __init__(
        self,
        is_duplicate: bool,
        duplicate_type: Optional[str] = None,
        original_lead_id: Optional[str] = None,
        original_status: Optional[str] = None,
        original_sent_to_crm: bool = False,
        message: str = ""
    ):
        self.is_duplicate = is_duplicate
        self.duplicate_type = duplicate_type  # "doublon_recent", "non_livre", "double_submit"
        self.original_lead_id = original_lead_id
        self.original_status = original_status
        self.original_sent_to_crm = original_sent_to_crm
        self.message = message
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_duplicate": self.is_duplicate,
            "duplicate_type": self.duplicate_type,
            "original_lead_id": self.original_lead_id,
            "original_status": self.original_status,
            "original_sent_to_crm": self.original_sent_to_crm,
            "message": self.message
        }


async def check_duplicate(
    phone: str,
    departement: str,
    session_id: Optional[str] = None
) -> DuplicateResult:
    """
    Vérifie si un lead est un doublon interne RDZ.
    
    Critères de détection:
    1. Double-submit: Même session_id dans les 5 dernières secondes
    2. Doublon récent: Même phone + dept, déjà livré dans les 30 jours
    3. Non livré: Même phone + dept, existe mais non livré dans les 30 jours
    
    Args:
        phone: Numéro de téléphone (déjà normalisé)
        departement: Code département
        session_id: ID de session (pour anti double-clic)
    
    Returns:
        DuplicateResult avec les détails
    """
    
    # Ignorer si données insuffisantes
    if not phone or not departement:
        return DuplicateResult(is_duplicate=False)
    
    now = datetime.now(timezone.utc)
    
    # === CHECK 1: Anti double-submit (même session, < 5 secondes) ===
    if session_id:
        double_submit_cutoff = (now - timedelta(seconds=DOUBLE_SUBMIT_SECONDS)).isoformat()
        
        double_submit = await db.leads.find_one({
            "session_id": session_id,
            "phone": phone,
            "created_at": {"$gte": double_submit_cutoff}
        }, {"_id": 0, "id": 1})
        
        if double_submit:
            logger.info(f"Double-submit détecté pour session {session_id[:8]}...")
            return DuplicateResult(
                is_duplicate=True,
                duplicate_type="double_submit",
                original_lead_id=double_submit.get("id"),
                message="Double soumission détectée - lead déjà créé"
            )
    
    # === CHECK 2 & 3: Doublon phone + dept dans les 30 jours ===
    duplicate_cutoff = (now - timedelta(days=DUPLICATE_WINDOW_DAYS)).isoformat()
    
    # Chercher un lead existant avec même phone + dept dans les 30 jours
    existing_lead = await db.leads.find_one(
        {
            "phone": phone,
            "departement": departement,
            "created_at": {"$gte": duplicate_cutoff},
            # Exclure les leads en erreur (orphan, invalid_phone, etc.)
            "api_status": {"$nin": ["orphan", "invalid_phone", "missing_required"]}
        },
        {"_id": 0, "id": 1, "api_status": 1, "sent_to_crm": 1, "created_at": 1, "target_crm": 1}
    )
    
    if existing_lead:
        original_id = existing_lead.get("id")
        original_status = existing_lead.get("api_status")
        sent_to_crm = existing_lead.get("sent_to_crm", False)
        
        if sent_to_crm:
            # Doublon récent - déjà livré → NON LIVRABLE
            logger.info(f"Doublon récent détecté: {phone} / {departement} - original: {original_id[:8]}...")
            return DuplicateResult(
                is_duplicate=True,
                duplicate_type="doublon_recent",
                original_lead_id=original_id,
                original_status=original_status,
                original_sent_to_crm=True,
                message=f"Doublon: lead déjà livré le {existing_lead.get('created_at', '')[:10]} vers {existing_lead.get('target_crm', 'CRM')}"
            )
        else:
            # Non livré - existe mais pas encore envoyé → REDISTRIBUABLE
            logger.info(f"Non livré détecté: {phone} / {departement} - original: {original_id[:8]}...")
            return DuplicateResult(
                is_duplicate=True,
                duplicate_type="non_livre",
                original_lead_id=original_id,
                original_status=original_status,
                original_sent_to_crm=False,
                message=f"Lead existant non livré (status: {original_status}) - redistribuable"
            )
    
    # Pas de doublon trouvé
    return DuplicateResult(is_duplicate=False)


async def get_duplicate_stats() -> Dict[str, int]:
    """
    Retourne les statistiques des doublons détectés.
    """
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=DUPLICATE_WINDOW_DAYS)).isoformat()
    
    # Compter les différents types
    doublon_recent = await db.leads.count_documents({
        "api_status": "doublon_recent",
        "created_at": {"$gte": cutoff}
    })
    
    non_livre = await db.leads.count_documents({
        "api_status": "non_livre",
        "created_at": {"$gte": cutoff}
    })
    
    double_submit = await db.leads.count_documents({
        "api_status": "double_submit",
        "created_at": {"$gte": cutoff}
    })
    
    return {
        "doublon_recent": doublon_recent,
        "non_livre": non_livre,
        "double_submit": double_submit,
        "total_duplicates": doublon_recent + non_livre + double_submit,
        "window_days": DUPLICATE_WINDOW_DAYS
    }
