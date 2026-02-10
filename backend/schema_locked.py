"""
🔒 SCHEMA VERROUILLÉ - NE PAS MODIFIER 🔒

Ce fichier définit les noms canoniques IMMUABLES du système RDZ CRM.
Toute modification de ces noms est INTERDITE sans autorisation explicite.

Si une modification est nécessaire, l'utilisateur doit explicitement déverrouiller
en disant: "Je déverrouille le schema pour modifier [nom_du_champ]"

DERNIÈRE VALIDATION: Février 2026
STATUT: 🔒 VERROUILLÉ
"""

# ============================================================
#                    🔒 CHAMPS LEAD 🔒
# ============================================================
# Ces noms sont utilisés dans: API, DB, Frontend, Scripts tracking
# NE JAMAIS CHANGER sans déverrouillage explicite

LEAD_FIELDS_LOCKED = {
    # ===== IDENTITÉ =====
    "phone": {
        "type": "string",
        "required": True,
        "description": "Numéro de téléphone (10 chiffres)",
        "locked": True
    },
    "nom": {
        "type": "string",
        "required": False,
        "description": "Nom de famille",
        "locked": True
    },
    "prenom": {
        "type": "string",
        "required": False,
        "description": "Prénom",
        "locked": True
    },
    "civilite": {
        "type": "string",
        "required": False,
        "description": "Civilité (M., Mme, Mlle)",
        "locked": True
    },
    "email": {
        "type": "string",
        "required": False,
        "description": "Adresse email",
        "locked": True
    },
    
    # ===== LOCALISATION =====
    "departement": {
        "type": "string",
        "required": False,
        "description": "Code département (01-95)",
        "locked": True,
        "ATTENTION": "REMPLACE code_postal - NE JAMAIS UTILISER code_postal"
    },
    "ville": {
        "type": "string",
        "required": False,
        "description": "Nom de la ville",
        "locked": True
    },
    "adresse": {
        "type": "string",
        "required": False,
        "description": "Adresse postale",
        "locked": True
    },
    
    # ===== LOGEMENT =====
    "type_logement": {
        "type": "string",
        "required": False,
        "description": "Type (Maison, Appartement)",
        "locked": True
    },
    "statut_occupant": {
        "type": "string",
        "required": False,
        "description": "Statut (Propriétaire, Locataire)",
        "locked": True
    },
    "surface_habitable": {
        "type": "string",
        "required": False,
        "description": "Surface en m²",
        "locked": True
    },
    "annee_construction": {
        "type": "string",
        "required": False,
        "description": "Année de construction",
        "locked": True
    },
    "type_chauffage": {
        "type": "string",
        "required": False,
        "description": "Type chauffage actuel",
        "locked": True
    },
    
    # ===== ÉNERGIE =====
    "facture_electricite": {
        "type": "string",
        "required": False,
        "description": "Tranche facture électricité",
        "locked": True
    },
    "facture_chauffage": {
        "type": "string",
        "required": False,
        "description": "Tranche facture chauffage",
        "locked": True
    },
    
    # ===== PROJET =====
    "type_projet": {
        "type": "string",
        "required": False,
        "description": "Type projet (Installation, Remplacement)",
        "locked": True
    },
    "delai_projet": {
        "type": "string",
        "required": False,
        "description": "Délai projet",
        "locked": True
    },
    "budget": {
        "type": "string",
        "required": False,
        "description": "Budget prévu",
        "locked": True
    },
    
    # ===== TRACKING =====
    "form_code": {
        "type": "string",
        "required": True,
        "description": "Code formulaire (PV-001, PAC-002...)",
        "locked": True
    },
    "lp_code": {
        "type": "string",
        "required": False,
        "description": "Code Landing Page (LP-001...)",
        "locked": True
    },
    "liaison_code": {
        "type": "string",
        "required": False,
        "description": "Code liaison LP_Form",
        "locked": True
    },
    "session_id": {
        "type": "string",
        "required": True,
        "description": "ID session visiteur",
        "locked": True
    },
    "utm_source": {
        "type": "string",
        "required": False,
        "description": "UTM Source",
        "locked": True
    },
    "utm_medium": {
        "type": "string",
        "required": False,
        "description": "UTM Medium",
        "locked": True
    },
    "utm_campaign": {
        "type": "string",
        "required": False,
        "description": "UTM Campaign",
        "locked": True
    },
    
    # ===== CRM & ROUTING =====
    "origin_crm": {
        "type": "string",
        "required": False,
        "description": "CRM d'origine (slug: zr7, mdl)",
        "locked": True
    },
    "target_crm": {
        "type": "string",
        "required": False,
        "description": "CRM de destination (slug: zr7, mdl, none)",
        "locked": True
    },
    "is_transferred": {
        "type": "boolean",
        "required": False,
        "description": "Lead transféré vers autre CRM",
        "locked": True
    },
    "routing_reason": {
        "type": "string",
        "required": False,
        "description": "Raison du routage",
        "locked": True
    },
    "allow_cross_crm": {
        "type": "boolean",
        "required": False,
        "description": "Cross-CRM autorisé",
        "locked": True
    },
    "api_status": {
        "type": "string",
        "required": False,
        "description": "Statut API (pending, success, failed, duplicate, queued, no_crm)",
        "locked": True
    },
    "sent_to_crm": {
        "type": "boolean",
        "required": False,
        "description": "Envoyé avec succès au CRM",
        "locked": True
    },
    
    # ===== CONSENTEMENT =====
    "rgpd_consent": {
        "type": "boolean",
        "required": False,
        "description": "Consentement RGPD",
        "locked": True
    },
    "newsletter": {
        "type": "boolean",
        "required": False,
        "description": "Inscription newsletter",
        "locked": True
    },
    
    # ===== METADATA =====
    "id": {
        "type": "string",
        "required": True,
        "description": "UUID unique du lead",
        "locked": True
    },
    "created_at": {
        "type": "string",
        "required": True,
        "description": "Date création ISO",
        "locked": True
    },
    "register_date": {
        "type": "integer",
        "required": False,
        "description": "Timestamp Unix",
        "locked": True
    },
    "ip": {
        "type": "string",
        "required": False,
        "description": "Adresse IP",
        "locked": True
    }
}


# ============================================================
#                    🔒 CHAMPS INTERDITS 🔒
# ============================================================
# Ces noms ne doivent JAMAIS être utilisés - ils sont obsolètes

FORBIDDEN_FIELDS = [
    "code_postal",      # → Utiliser "departement"
    "target_crm_id",    # → Utiliser "target_crm" (slug)
    "target_crm_slug",  # → Utiliser "target_crm"
    "source",           # → Utiliser "utm_source"
    "cp",               # → Utiliser "departement"
    "postal_code",      # → Utiliser "departement"
    "zipcode",          # → Utiliser "departement"
]


# ============================================================
#                    🔒 SLUGS CRM 🔒
# ============================================================

CRM_SLUGS_LOCKED = {
    "zr7": {
        "name": "ZR7 Digital",
        "locked": True
    },
    "mdl": {
        "name": "Maison du Lead",
        "locked": True
    }
}


# ============================================================
#                    🔒 EVENTS TRACKING 🔒
# ============================================================

TRACKING_EVENTS_LOCKED = {
    "lp_visit": {
        "description": "Visite Landing Page",
        "locked": True
    },
    "cta_click": {
        "description": "Clic sur CTA",
        "locked": True
    },
    "form_start": {
        "description": "Début formulaire",
        "locked": True
    },
    "form_submit": {
        "description": "Soumission formulaire (implicite via lead)",
        "locked": True
    }
}


# ============================================================
#                    🔒 API STATUS 🔒
# ============================================================

API_STATUS_LOCKED = [
    "pending",      # En attente
    "success",      # Envoyé avec succès
    "failed",       # Échec d'envoi
    "duplicate",    # Doublon détecté
    "queued",       # En file d'attente
    "no_crm",       # Pas de CRM disponible
]


# ============================================================
#                    🔒 PRODUCT TYPES 🔒
# ============================================================

PRODUCT_TYPES_LOCKED = [
    "PV",   # Panneaux solaires
    "PAC",  # Pompe à chaleur
    "ITE",  # Isolation thermique
]


# ============================================================
#              FONCTION DE VALIDATION
# ============================================================

def validate_field_name(field_name: str) -> dict:
    """
    Valide qu'un nom de champ est autorisé.
    Retourne un dict avec le statut et un message.
    """
    # Vérifier si c'est un champ interdit
    if field_name in FORBIDDEN_FIELDS:
        return {
            "valid": False,
            "locked": True,
            "error": f"🔒 CHAMP INTERDIT: '{field_name}' ne doit JAMAIS être utilisé. Utilisez le champ canonique à la place."
        }
    
    # Vérifier si c'est un champ verrouillé
    if field_name in LEAD_FIELDS_LOCKED:
        return {
            "valid": True,
            "locked": True,
            "message": f"🔒 Champ '{field_name}' est verrouillé et ne peut pas être renommé."
        }
    
    # Champ inconnu
    return {
        "valid": True,
        "locked": False,
        "message": f"Champ '{field_name}' n'est pas dans le schema verrouillé."
    }


def get_locked_fields_list() -> list:
    """Retourne la liste de tous les champs verrouillés"""
    return list(LEAD_FIELDS_LOCKED.keys())


def is_field_locked(field_name: str) -> bool:
    """Vérifie si un champ est verrouillé"""
    return field_name in LEAD_FIELDS_LOCKED


def is_field_forbidden(field_name: str) -> bool:
    """Vérifie si un champ est interdit"""
    return field_name in FORBIDDEN_FIELDS


# ============================================================
#              MESSAGE D'AVERTISSEMENT
# ============================================================

LOCK_WARNING = """
╔══════════════════════════════════════════════════════════════╗
║  🔒 ATTENTION: SCHEMA VERROUILLÉ                             ║
║                                                              ║
║  Les noms de champs dans ce fichier sont IMMUABLES.          ║
║  Toute modification nécessite un déverrouillage explicite.   ║
║                                                              ║
║  Pour déverrouiller, l'utilisateur doit dire:                ║
║  "Je déverrouille le schema pour modifier [nom_du_champ]"    ║
║                                                              ║
║  Sans cette autorisation, aucun renommage n'est permis.      ║
╚══════════════════════════════════════════════════════════════╝
"""

if __name__ == "__main__":
    print(LOCK_WARNING)
    print(f"\n📋 Champs verrouillés: {len(LEAD_FIELDS_LOCKED)}")
    print(f"🚫 Champs interdits: {len(FORBIDDEN_FIELDS)}")
    print(f"🏷️  CRM Slugs: {list(CRM_SLUGS_LOCKED.keys())}")
    print(f"📊 Events: {list(TRACKING_EVENTS_LOCKED.keys())}")
    print(f"📦 Produits: {PRODUCT_TYPES_LOCKED}")
