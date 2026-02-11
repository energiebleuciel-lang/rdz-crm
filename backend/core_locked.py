"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   🔒🔒🔒  NOYAU CRITIQUE VERROUILLÉ - INTÉGRATION LEADS  🔒🔒🔒              ║
║                                                                              ║
║   Ce fichier définit les composants CRITIQUES du système d'intégration.      ║
║   Ces fonctions sont la BASE de la structure RDZ et ne doivent JAMAIS        ║
║   être modifiées sans autorisation explicite du propriétaire.                ║
║                                                                              ║
║   POUR DÉVERROUILLER, LE PROPRIÉTAIRE DOIT DIRE:                             ║
║   "Je déverrouille le noyau critique pour modifier [nom_fonction]"           ║
║                                                                              ║
║   DERNIÈRE VALIDATION: Février 2026                                          ║
║   STATUT: 🔒 VERROUILLÉ DÉFINITIVEMENT                                       ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

# ============================================================
#          🔒 FONCTIONS CRITIQUES VERROUILLÉES 🔒
# ============================================================

CORE_FUNCTIONS_LOCKED = {
    
    # ==================== RÉCEPTION LEAD ====================
    "submit_lead": {
        "file": "/backend/routes/public.py",
        "description": "Point d'entrée principal - Réception des leads depuis les formulaires",
        "criticality": "MAXIMALE",
        "locked": True,
        "reason": "Toute modification peut casser l'intégration de TOUS les leads"
    },
    
    # ==================== ROUTAGE CRM ====================
    "has_commande": {
        "file": "/backend/routes/commandes.py",
        "description": "Vérifie si un CRM a une commande pour ce département/produit",
        "criticality": "MAXIMALE",
        "locked": True,
        "reason": "Détermine vers quel CRM le lead est envoyé - Bug = leads perdus"
    },
    
    # ==================== ENVOI CRM ====================
    "send_to_crm_v2": {
        "file": "/backend/services/lead_sender.py",
        "description": "Envoi effectif du lead vers ZR7 ou MDL",
        "criticality": "MAXIMALE",
        "locked": True,
        "reason": "Communication directe avec les CRMs externes"
    },
    
    "add_to_queue": {
        "file": "/backend/services/lead_sender.py",
        "description": "Mise en file d'attente pour retry automatique",
        "criticality": "HAUTE",
        "locked": True,
        "reason": "Garantit qu'aucun lead n'est perdu en cas d'erreur"
    },
    
    # ==================== VALIDATION ====================
    "validate_phone_fr": {
        "file": "/backend/config.py",
        "description": "Validation du format téléphone français",
        "criticality": "HAUTE",
        "locked": True,
        "reason": "Filtre les leads invalides avant envoi CRM"
    },
    
    # ==================== TRACKING ====================
    "create_session": {
        "file": "/backend/routes/public.py",
        "endpoint": "POST /api/public/track/session",
        "description": "Création de session visiteur pour tracking",
        "criticality": "HAUTE",
        "locked": True,
        "reason": "Lie les événements tracking aux leads"
    },
    
    "track_event": {
        "file": "/backend/routes/public.py",
        "endpoint": "POST /api/public/track/event",
        "description": "Enregistrement des événements (lp_visit, form_start, etc.)",
        "criticality": "MOYENNE",
        "locked": True,
        "reason": "Statistiques et analytics"
    },
    
    # ==================== HELPERS CRM ====================
    "get_crm_url": {
        "file": "/backend/routes/public.py",
        "description": "Récupération dynamique de l'URL API du CRM",
        "criticality": "HAUTE",
        "locked": True,
        "reason": "URL incorrecte = leads non envoyés"
    },
    
    "get_crm_id": {
        "file": "/backend/routes/public.py",
        "description": "Récupération de l'ID CRM depuis le slug",
        "criticality": "HAUTE",
        "locked": True,
        "reason": "Identification CRM pour routage"
    },
}


# ============================================================
#          🔒 FICHIERS CRITIQUES VERROUILLÉS 🔒
# ============================================================

CORE_FILES_LOCKED = {
    "/backend/routes/public.py": {
        "description": "API publique - Tracking + Soumission leads",
        "contains": ["submit_lead", "create_session", "track_event", "get_crm_url"],
        "locked": True
    },
    "/backend/routes/commandes.py": {
        "description": "Gestion commandes + Fonction de routage",
        "contains": ["has_commande"],
        "locked": True
    },
    "/backend/services/lead_sender.py": {
        "description": "Service d'envoi vers CRMs externes",
        "contains": ["send_to_crm_v2", "add_to_queue"],
        "locked": True
    },
    "/backend/config.py": {
        "description": "Configuration + Validation",
        "contains": ["validate_phone_fr"],
        "locked": True,
        "note": "Seules les fonctions listées sont verrouillées"
    },
    "/backend/schema_locked.py": {
        "description": "Définition du schema de données",
        "contains": ["LEAD_FIELDS_LOCKED", "FORBIDDEN_FIELDS"],
        "locked": True
    },
}


# ============================================================
#          🔒 FLUX CRITIQUE VERROUILLÉ 🔒
# ============================================================

CRITICAL_FLOW = """
┌─────────────────────────────────────────────────────────────────┐
│                    FLUX D'INTÉGRATION LEAD                      │
│                      🔒 VERROUILLÉ 🔒                            │
└─────────────────────────────────────────────────────────────────┘

  1. FORMULAIRE (externe)
         │
         ▼
  ┌──────────────────┐
  │  create_session  │ ← Création session tracking
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │   track_event    │ ← Events: lp_visit, form_start, etc.
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │   submit_lead    │ ← POINT D'ENTRÉE PRINCIPAL
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │validate_phone_fr │ ← Validation téléphone
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │  has_commande    │ ← Routage: quel CRM ?
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │  get_crm_url     │ ← URL du CRM cible
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │ send_to_crm_v2   │ ← ENVOI VERS ZR7 ou MDL
  └────────┬─────────┘
           │
       ┌───┴───┐
       │Erreur?│
       └───┬───┘
           │ Oui
           ▼
  ┌──────────────────┐
  │  add_to_queue    │ ← Retry automatique
  └──────────────────┘
"""


# ============================================================
#          🚫 MODIFICATIONS INTERDITES 🚫
# ============================================================

FORBIDDEN_MODIFICATIONS = [
    "Changer la signature des fonctions critiques",
    "Modifier les noms de paramètres",
    "Changer l'ordre des validations",
    "Modifier la structure du payload lead",
    "Changer les endpoints API publics",
    "Modifier la logique de routage has_commande",
    "Changer le format d'envoi vers les CRMs",
    "Modifier la validation téléphone",
    "Changer les noms des champs (voir schema_locked.py)",
]


# ============================================================
#          ✅ MODIFICATIONS AUTORISÉES ✅
# ============================================================

ALLOWED_MODIFICATIONS = [
    "Ajouter des logs/debug (sans changer la logique)",
    "Corriger un bug CRITIQUE (avec déverrouillage)",
    "Ajouter un nouveau CRM (sans toucher aux existants)",
    "Améliorer les messages d'erreur",
    "Ajouter des champs OPTIONNELS au schema (pas obligatoires)",
]


# ============================================================
#          MESSAGE D'AVERTISSEMENT
# ============================================================

LOCK_WARNING = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   ⛔ ATTENTION: VOUS TENTEZ DE MODIFIER LE NOYAU CRITIQUE ⛔                 ║
║                                                                              ║
║   Le système d'intégration des leads est VERROUILLÉ.                         ║
║   Ces fonctions sont la BASE de RDZ et ne peuvent pas être modifiées.        ║
║                                                                              ║
║   Si vous avez VRAIMENT besoin de modifier ce code, dites:                   ║
║   "Je déverrouille le noyau critique pour modifier [nom_fonction]"           ║
║                                                                              ║
║   ⚠️  Toute modification non autorisée peut:                                 ║
║       - Casser l'intégration de TOUS les leads                               ║
║       - Perdre des leads définitivement                                      ║
║       - Bloquer les envois vers ZR7/MDL                                      ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""


def is_core_function(function_name: str) -> bool:
    """Vérifie si une fonction fait partie du noyau critique"""
    return function_name in CORE_FUNCTIONS_LOCKED


def is_core_file(file_path: str) -> bool:
    """Vérifie si un fichier fait partie du noyau critique"""
    for locked_file in CORE_FILES_LOCKED.keys():
        if locked_file in file_path:
            return True
    return False


def get_lock_status() -> dict:
    """Retourne le statut de verrouillage"""
    return {
        "status": "LOCKED",
        "functions_locked": len(CORE_FUNCTIONS_LOCKED),
        "files_locked": len(CORE_FILES_LOCKED),
        "forbidden_modifications": len(FORBIDDEN_MODIFICATIONS)
    }


if __name__ == "__main__":
    print(LOCK_WARNING)
    print(CRITICAL_FLOW)
    print(f"\n🔒 Fonctions verrouillées: {len(CORE_FUNCTIONS_LOCKED)}")
    print(f"📁 Fichiers verrouillés: {len(CORE_FILES_LOCKED)}")
    print(f"🚫 Modifications interdites: {len(FORBIDDEN_MODIFICATIONS)}")
