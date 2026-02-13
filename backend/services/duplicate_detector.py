"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  SERVICE DE PROTECTION ANTI DOUBLE-SUBMIT                                    ║
║                                                                              ║
║  Unique règle active:                                                        ║
║  - Anti double-clic: même session + même phone en < 5 secondes               ║
║                                                                              ║
║  La détection doublons 30 jours (doublon_recent, non_livre) est SUPPRIMÉE.   ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from config import db

logger = logging.getLogger("duplicate_detector")

DOUBLE_SUBMIT_SECONDS = 5


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
        self.duplicate_type = duplicate_type
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
    Vérifie uniquement le double-submit (anti double-clic).
    La règle des 30 jours est supprimée.
    """
    if not phone:
        return DuplicateResult(is_duplicate=False)

    now = datetime.now(timezone.utc)

    # Anti double-submit : même session + même phone en < 5 secondes
    if session_id:
        cutoff = (now - timedelta(seconds=DOUBLE_SUBMIT_SECONDS)).isoformat()
        double_submit = await db.leads.find_one({
            "session_id": session_id,
            "phone": phone,
            "created_at": {"$gte": cutoff}
        }, {"_id": 0, "id": 1})

        if double_submit:
            logger.info(f"Double-submit détecté pour session {session_id[:8]}...")
            return DuplicateResult(
                is_duplicate=True,
                duplicate_type="double_submit",
                original_lead_id=double_submit.get("id"),
                message="Double soumission détectée - lead déjà créé"
            )

    return DuplicateResult(is_duplicate=False)
