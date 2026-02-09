from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import httpx
import hashlib
import secrets
import traceback

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configuration du logging pour les alertes
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("crm_system")

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI(title="CRM Leads System")
api_router = APIRouter(prefix="/api")
security = HTTPBearer(auto_error=False)

# ==================== CLÉ API GLOBALE ====================
# Système d'authentification style Landbot:
# - 1 clé API globale par compte CRM
# - Chaque formulaire a un form_id unique
# - Header: Authorization: Token VOTRE_CLE_GLOBALE

async def get_or_create_global_api_key():
    """Récupère ou crée la clé API globale du CRM."""
    config = await db.system_config.find_one({"type": "global_api_key"})
    if not config:
        # Créer une nouvelle clé globale
        api_key = f"crm_{secrets.token_urlsafe(32)}"
        await db.system_config.insert_one({
            "type": "global_api_key",
            "api_key": api_key,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        return api_key
    return config.get("api_key")

async def verify_global_api_key(authorization: str) -> bool:
    """Vérifie la clé API globale dans le header Authorization."""
    if not authorization:
        return False
    
    # Format: "Token abc123..." ou "Bearer abc123..."
    parts = authorization.split(" ")
    if len(parts) != 2:
        return False
    
    token_type, token = parts
    if token_type.lower() not in ["token", "bearer"]:
        return False
    
    config = await db.system_config.find_one({"type": "global_api_key"})
    if not config:
        return False
    
    return config.get("api_key") == token

# ==================== MODELS ====================

class UserCreate(BaseModel):
    email: str
    password: str
    nom: str
    role: str = "viewer"  # admin, editor, viewer
    allowed_accounts: List[str] = []  # Liste des IDs de comptes autorisés (vide = tous)

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    nom: str
    role: str
    allowed_accounts: List[str] = []

class UserUpdate(BaseModel):
    role: Optional[str] = None
    allowed_accounts: Optional[List[str]] = None

class CRMCreate(BaseModel):
    name: str  # "Maison du Lead", "ZR7"
    slug: str  # "mdl", "zr7"
    api_url: str
    description: Optional[str] = ""
    # Commandes par produit : départements où ce CRM a des commandes
    # Format: {"PAC": ["75", "92", "93"], "PV": ["13", "31"], "ITE": ["59", "62"]}
    commandes: Optional[Dict[str, List[str]]] = {}
    # Prix par lead par produit en euros (pour facturation inter-CRM)
    # Format: {"PAC": 25.0, "PV": 20.0, "ITE": 30.0}
    lead_prices: Optional[Dict[str, float]] = {}
    # Limites de leads inter-CRM par produit par mois (0 = illimité)
    # Format: {"PAC": 100, "PV": 200, "ITE": 50}
    routing_limits: Optional[Dict[str, int]] = {}

class CRMUpdate(BaseModel):
    name: Optional[str] = None
    api_url: Optional[str] = None
    description: Optional[str] = None
    commandes: Optional[Dict[str, List[str]]] = None
    lead_prices: Optional[Dict[str, float]] = None
    routing_limits: Optional[Dict[str, int]] = None

# Diffusion source types (Native, Google Ads, etc.)
class DiffusionSourceCreate(BaseModel):
    name: str  # "Taboola", "Outbrain", "Google Ads"
    category: str  # "native", "google", "facebook", "tiktok", "other"
    is_active: bool = True

# Product type with instructions
class ProductTypeCreate(BaseModel):
    name: str  # "Panneaux solaires", "Pompe à chaleur"
    slug: str  # "solaire", "pac", "isolation"
    aide_montant: str  # "10 000€"
    aides_liste: List[str]  # ["MaPrimeRenov", "CEE", "TVA réduite"]
    description: Optional[str] = ""
    is_active: bool = True

# Asset library for images/logos
class AssetCreate(BaseModel):
    label: str  # "Logo principal bleu"
    url: str  # URL of the image
    asset_type: str = "image"  # image, logo, favicon, background
    sub_account_id: Optional[str] = None  # None = global asset, otherwise specific to sub-account
    crm_id: Optional[str] = None  # For filtering

# LP/Form generation options
class GenerationOptions(BaseModel):
    style_officiel: bool = False  # Look official/gov style
    primary_color: str = "#3B82F6"
    secondary_color: str = "#1E40AF"
    background_color: str = "#FFFFFF"
    logo_count: int = 1  # 1 or 2 logos
    logo_left_asset_id: Optional[str] = ""
    logo_right_asset_id: Optional[str] = ""
    show_trust_badges: bool = True
    show_certification: bool = True
    custom_css: Optional[str] = ""

# Form template configuration per account
class FormTemplateConfig(BaseModel):
    # Required fields
    phone_required: bool = True
    phone_digits: int = 10
    nom_required: bool = True
    # Optional fields to show
    show_civilite: bool = True
    show_prenom: bool = True
    show_email: bool = True
    show_departement: bool = True
    show_code_postal: bool = True
    show_type_logement: bool = True
    show_statut_occupant: bool = True
    show_facture: bool = True
    # France metro postal codes only (01-95)
    postal_code_france_metro_only: bool = True
    # Form style
    form_style: str = "modern"  # modern, classic, minimal

# Account model (renamed from SubAccount)
class NamedRedirectURL(BaseModel):
    name: str  # "Google", "Taboola", "Facebook"
    url: str

class AccountImage(BaseModel):
    name: str  # "Bannière principale", "Image produit"
    url: str

class AccountCreate(BaseModel):
    crm_id: str
    name: str
    domain: Optional[str] = ""
    product_types: List[str] = ["solaire"]  # Can have multiple: solaire, pac, isolation
    # Logos
    logo_main_url: Optional[str] = ""  # Logo principal (gauche)
    logo_secondary_url: Optional[str] = ""  # Logo secondaire (droite)  
    logo_small_url: Optional[str] = ""  # Petit logo / badge
    favicon_url: Optional[str] = ""
    # Bibliothèque d'images du compte
    images: List[AccountImage] = []  # [{"name": "Bannière", "url": "..."}, ...]
    # Textes légaux
    privacy_policy_text: Optional[str] = ""  # Texte direct, pas URL
    legal_mentions_text: Optional[str] = ""
    # Style
    layout: str = "center"  # left, right, center
    primary_color: Optional[str] = "#3B82F6"
    secondary_color: Optional[str] = "#1E40AF"
    style_officiel: bool = False  # Look officiel/gov style
    # TRACKING GTM - Au niveau du compte
    gtm_pixel_header: Optional[str] = ""  # Code dans <head> (Facebook Pixel, etc.)
    gtm_conversion_code: Optional[str] = ""  # Code de conversion (déclenché après validation tel)
    gtm_cta_code: Optional[str] = ""  # Code CTA click
    # URLs de redirection nommées (plusieurs possibles)
    named_redirect_urls: List[NamedRedirectURL] = []  # [{"name": "Google", "url": "..."}, ...]
    default_redirect_url: Optional[str] = ""  # URL par défaut si aucune nommée
    # Notes
    notes: Optional[str] = ""
    # Form template configuration
    form_template: Optional[FormTemplateConfig] = None

# For backwards compatibility, keep SubAccountCreate as alias
SubAccountCreate = AccountCreate

class LPCreate(BaseModel):
    account_id: str
    code: str  # Code unique de référence (LP-TAB-V1)
    name: str
    url: Optional[str] = ""  # URL de la LP
    source_type: str = "native"  # native, google, facebook, tiktok
    source_name: Optional[str] = ""  # Taboola, Outbrain, etc.
    # Type de LP
    lp_type: str = "redirect"  # redirect (vers form externe) ou integrated (form dans LP)
    redirect_url_name: Optional[str] = ""  # Nom de l'URL de redirection (depuis le compte)
    form_url: Optional[str] = ""  # URL du formulaire (si redirect) ou intégré
    # Stockage du code HTML
    html_code: Optional[str] = ""  # Code HTML complet de la LP
    # Notes
    notes: Optional[str] = ""
    status: str = "active"

class FormCreate(BaseModel):
    account_id: str
    code: str  # Code unique (PV-TAB-001)
    name: str
    url: Optional[str] = ""  # URL du formulaire
    product_type: str = "panneaux"  # panneaux, pompes, isolation
    source_type: str = "native"
    source_name: Optional[str] = ""  # Taboola, Outbrain, etc.
    # Type de formulaire
    form_type: str = "standalone"  # standalone (page séparée) ou integrated (dans LP)
    lp_ids: List[str] = []  # LPs liées à ce formulaire
    # Tracking
    tracking_type: str = "redirect"  # gtm, redirect, none
    redirect_url_name: Optional[str] = ""  # Nom de l'URL de redirection (depuis le compte)
    # Stockage du code HTML
    html_code: Optional[str] = ""  # Code HTML complet du formulaire
    # Clés API pour l'intégration des leads
    crm_api_key: Optional[str] = ""  # Clé API du CRM destination (ZR7/MDL) - fournie par vous
    # Exclusion du routage inter-CRM (pour éviter doublons cross-CRM)
    exclude_from_routing: bool = False  # Si True, pas de reroutage vers autre CRM
    # Notes
    notes: Optional[str] = ""
    status: str = "active"
    # Override template settings (if different from sub-account defaults)
    custom_fields_config: Optional[Dict[str, Any]] = None

class LeadData(BaseModel):
    # Champs requis par ZR7/MDL API
    phone: str  # Obligatoire pour l'envoi
    register_date: Optional[int] = None  # Timestamp auto-généré si absent
    # Champs optionnels (tous de la doc API)
    nom: Optional[str] = ""
    prenom: Optional[str] = ""
    civilite: Optional[str] = ""  # M., Mme
    email: Optional[str] = ""
    # Custom fields ZR7/MDL
    departement: Optional[str] = ""
    code_postal: Optional[str] = ""
    superficie_logement: Optional[str] = ""  # "120m²"
    chauffage_actuel: Optional[str] = ""  # "Électrique", "Gaz", "Fioul"
    type_logement: Optional[str] = ""  # Maison, Appartement
    statut_occupant: Optional[str] = ""  # Propriétaire, Locataire
    facture_electricite: Optional[str] = ""
    # Référence formulaire/LP
    form_id: Optional[str] = "default"
    form_code: Optional[str] = ""
    lp_code: Optional[str] = ""
    # SÉCURITÉ : Clé API obligatoire pour authentifier la requête
    api_key: Optional[str] = ""  # internal_api_key du formulaire

class CommentCreate(BaseModel):
    entity_type: str  # lp, form
    entity_id: str
    content: str

class CTAClickTrack(BaseModel):
    lp_code: str
    domain: Optional[str] = ""

class FormStartTrack(BaseModel):
    form_code: str
    lp_code: Optional[str] = ""

# Validation helper for France metro postal codes (01-95)
FRANCE_METRO_DEPTS = [str(i).zfill(2) for i in range(1, 96)] + ["2A", "2B"]

def validate_phone_fr(phone: str) -> tuple:
    """Validate French phone number (10 digits)"""
    digits = ''.join(filter(str.isdigit, phone))
    if len(digits) == 9 and not digits.startswith('0'):
        digits = '0' + digits
    if len(digits) != 10:
        return False, "Le téléphone doit contenir 10 chiffres"
    if not digits.startswith('0'):
        return False, "Le téléphone doit commencer par 0"
    return True, digits

def validate_postal_code_fr(code: str) -> tuple:
    """Validate French metropolitan postal code"""
    if not code:
        return True, code
    digits = ''.join(filter(str.isdigit, code))
    if len(digits) != 5:
        return False, "Le code postal doit contenir 5 chiffres"
    dept = digits[:2]
    if dept not in FRANCE_METRO_DEPTS and digits[:3] not in ["971", "972", "973", "974", "976"]:
        # Allow DOM-TOM but can be restricted
        pass
    if dept not in FRANCE_METRO_DEPTS:
        return False, "Code postal France métropolitaine uniquement (01-95)"
    return True, digits

# ==================== AUTH HELPERS ====================

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def generate_token() -> str:
    return secrets.token_urlsafe(32)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    token = credentials.credentials
    session = await db.sessions.find_one({"token": token, "expires_at": {"$gt": datetime.now(timezone.utc).isoformat()}})
    
    if not session:
        raise HTTPException(status_code=401, detail="Session expirée")
    
    user = await db.users.find_one({"id": session["user_id"]}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur non trouvé")
    
    return user

async def get_optional_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        return None
    try:
        return await get_current_user(credentials)
    except:
        return None

async def require_admin(user: dict = Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Accès admin requis")
    return user

def get_account_filter(user: dict) -> dict:
    """
    Retourne un filtre MongoDB pour restreindre les données aux comptes autorisés.
    - Si l'utilisateur est admin ou n'a pas de restriction (allowed_accounts vide), retourne {}
    - Sinon, retourne un filtre sur les IDs de comptes autorisés
    """
    if user.get("role") == "admin":
        return {}
    
    allowed_accounts = user.get("allowed_accounts", [])
    if not allowed_accounts:
        # Pas de restriction définie = accès à tous
        return {}
    
    return {"id": {"$in": allowed_accounts}}

def get_account_ids_filter(user: dict) -> dict:
    """
    Retourne un filtre MongoDB pour les entités liées à un account_id.
    Utilisé pour LPs, Forms, etc.
    """
    if user.get("role") == "admin":
        return {}
    
    allowed_accounts = user.get("allowed_accounts", [])
    if not allowed_accounts:
        return {}
    
    return {"account_id": {"$in": allowed_accounts}}

async def log_activity(user_id: str, user_email: str, action: str, entity_type: str = "", entity_id: str = "", details: str = ""):
    await db.activity_logs.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "user_email": user_email,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "details": details,
        "created_at": datetime.now(timezone.utc).isoformat()
    })

async def log_alert(level: str, category: str, message: str, details: dict = None):
    """
    Enregistre une alerte dans la base de données pour le monitoring.
    Niveaux: INFO, WARNING, ERROR, CRITICAL
    """
    alert = {
        "id": str(uuid.uuid4()),
        "level": level,
        "category": category,
        "message": message,
        "details": details or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "resolved": False
    }
    await db.system_alerts.insert_one(alert)
    
    # Log aussi dans la console pour surveillance immédiate
    if level in ["ERROR", "CRITICAL"]:
        logger.error(f"[{category}] {message} - {details}")
    elif level == "WARNING":
        logger.warning(f"[{category}] {message}")
    else:
        logger.info(f"[{category}] {message}")

# ==================== SYSTÈME DE SANTÉ & MONITORING ====================

@api_router.get("/health")
async def health_check():
    """
    Vérification de santé du système - À appeler après chaque mise à jour.
    Retourne l'état de tous les composants critiques.
    """
    health = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {}
    }
    errors = []
    
    try:
        # Test connexion MongoDB
        await db.command("ping")
        health["checks"]["database"] = {"status": "ok", "message": "MongoDB connecté"}
    except Exception as e:
        health["checks"]["database"] = {"status": "error", "message": str(e)}
        errors.append("database")
    
    try:
        # Vérifier les collections critiques
        leads_count = await db.leads.count_documents({})
        forms_count = await db.forms.count_documents({})
        users_count = await db.users.count_documents({})
        health["checks"]["collections"] = {
            "status": "ok",
            "leads": leads_count,
            "forms": forms_count,
            "users": users_count
        }
    except Exception as e:
        health["checks"]["collections"] = {"status": "error", "message": str(e)}
        errors.append("collections")
    
    try:
        # Vérifier les stats de leads (cohérence)
        leads_success = await db.leads.count_documents({"api_status": "success"})
        leads_failed = await db.leads.count_documents({"api_status": "failed"})
        leads_pending = await db.leads.count_documents({"api_status": "pending"})
        leads_total = leads_success + leads_failed + leads_pending
        health["checks"]["leads_stats"] = {
            "status": "ok",
            "total": leads_count,
            "success": leads_success,
            "failed": leads_failed,
            "pending": leads_pending,
            "coherent": leads_total <= leads_count
        }
    except Exception as e:
        health["checks"]["leads_stats"] = {"status": "error", "message": str(e)}
        errors.append("leads_stats")
    
    try:
        # Vérifier les alertes non résolues
        unresolved_alerts = await db.system_alerts.count_documents({"resolved": False, "level": {"$in": ["ERROR", "CRITICAL"]}})
        health["checks"]["alerts"] = {
            "status": "warning" if unresolved_alerts > 0 else "ok",
            "unresolved_critical": unresolved_alerts
        }
    except Exception as e:
        health["checks"]["alerts"] = {"status": "error", "message": str(e)}
    
    # Statut global
    if errors:
        health["status"] = "unhealthy"
        health["errors"] = errors
        await log_alert("CRITICAL", "HEALTH_CHECK", f"Système en erreur: {', '.join(errors)}")
    
    return health

@api_router.get("/health/stats")
async def health_stats(user: dict = Depends(get_current_user)):
    """
    Statistiques détaillées du système pour l'admin.
    """
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Accès admin requis")
    
    stats = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "leads": {
            "total": await db.leads.count_documents({}),
            "today": await db.leads.count_documents({
                "created_at": {"$gte": datetime.now(timezone.utc).replace(hour=0, minute=0, second=0).isoformat()}
            }),
            "success": await db.leads.count_documents({"api_status": "success"}),
            "failed": await db.leads.count_documents({"api_status": "failed"}),
            "by_product": {
                "PV": await db.leads.count_documents({"product_type": "PV"}),
                "PAC": await db.leads.count_documents({"product_type": "PAC"}),
                "ITE": await db.leads.count_documents({"product_type": "ITE"})
            }
        },
        "forms": {
            "total": await db.forms.count_documents({}),
            "active": await db.forms.count_documents({"status": "active"}),
            "archived": await db.forms.count_documents({"status": "archived"})
        },
        "alerts": {
            "unresolved": await db.system_alerts.count_documents({"resolved": False}),
            "critical": await db.system_alerts.count_documents({"resolved": False, "level": "CRITICAL"}),
            "errors": await db.system_alerts.count_documents({"resolved": False, "level": "ERROR"})
        }
    }
    return stats

@api_router.get("/alerts")
async def get_alerts(resolved: bool = False, limit: int = 50, user: dict = Depends(get_current_user)):
    """
    Récupère les alertes système.
    """
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Accès admin requis")
    
    query = {"resolved": resolved}
    alerts = await db.system_alerts.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return {"alerts": alerts, "count": len(alerts)}

@api_router.put("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str, user: dict = Depends(get_current_user)):
    """
    Marque une alerte comme résolue.
    """
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Accès admin requis")
    
    result = await db.system_alerts.update_one(
        {"id": alert_id},
        {"$set": {"resolved": True, "resolved_at": datetime.now(timezone.utc).isoformat(), "resolved_by": user["id"]}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Alerte non trouvée")
    
    return {"success": True}

# ==================== CLÉ API GLOBALE ENDPOINTS ====================

@api_router.get("/settings/api-key")
async def get_global_api_key(user: dict = Depends(get_current_user)):
    """
    Récupère la clé API globale du CRM.
    Comme Landbot: 1 clé globale pour tout le compte.
    """
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Seul l'admin peut voir la clé API")
    
    api_key = await get_or_create_global_api_key()
    return {
        "api_key": api_key,
        "usage": "Header: Authorization: Token VOTRE_CLE_API",
        "endpoint": "POST /api/v1/leads"
    }

@api_router.post("/settings/api-key/regenerate")
async def regenerate_global_api_key(user: dict = Depends(get_current_user)):
    """
    Régénère la clé API globale. ATTENTION: Invalide l'ancienne clé!
    """
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Seul l'admin peut régénérer la clé API")
    
    # Supprimer l'ancienne clé
    await db.system_config.delete_one({"type": "global_api_key"})
    
    # Créer une nouvelle clé
    new_api_key = f"crm_{secrets.token_urlsafe(32)}"
    await db.system_config.insert_one({
        "type": "global_api_key",
        "api_key": new_api_key,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    await log_alert("WARNING", "API_KEY_REGENERATED", f"Clé API globale régénérée par {user['email']}")
    
    return {
        "success": True,
        "api_key": new_api_key,
        "message": "Nouvelle clé API générée. L'ancienne clé ne fonctionne plus."
    }

# ==================== AUTH ENDPOINTS ====================

@api_router.post("/auth/register")
async def register(user: UserCreate):
    existing = await db.users.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email déjà utilisé")
    
    user_doc = {
        "id": str(uuid.uuid4()),
        "email": user.email,
        "password": hash_password(user.password),
        "nom": user.nom,
        "role": user.role,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user_doc)
    
    return {"success": True, "message": "Utilisateur créé"}

@api_router.post("/auth/login")
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email})
    if not user or user["password"] != hash_password(credentials.password):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    
    token = generate_token()
    expires = datetime.now(timezone.utc) + timedelta(days=7)
    
    await db.sessions.insert_one({
        "token": token,
        "user_id": user["id"],
        "expires_at": expires.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    await log_activity(user["id"], user["email"], "login", details="Connexion réussie")
    
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "nom": user["nom"],
            "role": user["role"]
        }
    }

@api_router.post("/auth/logout")
async def logout(user: dict = Depends(get_current_user), credentials: HTTPAuthorizationCredentials = Depends(security)):
    await db.sessions.delete_one({"token": credentials.credentials})
    await log_activity(user["id"], user["email"], "logout", details="Déconnexion")
    return {"success": True}

@api_router.get("/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    return user

@api_router.post("/auth/init-admin")
async def init_admin():
    """Create initial admin user if no users exist"""
    count = await db.users.count_documents({})
    if count > 0:
        raise HTTPException(status_code=400, detail="Des utilisateurs existent déjà")
    
    admin_doc = {
        "id": str(uuid.uuid4()),
        "email": "energiebleuciel@gmail.com",
        "password": hash_password("92Ruemarxdormoy"),
        "nom": "Admin",
        "role": "admin",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(admin_doc)
    return {"success": True, "message": "Admin créé"}

# ==================== CRM ENDPOINTS ====================

@api_router.get("/crms")
async def get_crms(user: dict = Depends(get_current_user)):
    crms = await db.crms.find({}, {"_id": 0}).to_list(100)
    return {"crms": crms}

@api_router.get("/crms/{crm_id}")
async def get_crm(crm_id: str, user: dict = Depends(get_current_user)):
    crm = await db.crms.find_one({"id": crm_id}, {"_id": 0})
    if not crm:
        raise HTTPException(status_code=404, detail="CRM non trouvé")
    return crm

@api_router.put("/crms/{crm_id}")
async def update_crm(crm_id: str, crm_update: CRMUpdate, user: dict = Depends(require_admin)):
    """Update CRM including commandes (orders by product/department)"""
    update_data = {k: v for k, v in crm_update.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="Aucune donnée à mettre à jour")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.crms.update_one({"id": crm_id}, {"$set": update_data})
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="CRM non trouvé")
    
    await log_activity(user["id"], user["email"], "update", "crm", crm_id, "CRM mis à jour (commandes)")
    return {"success": True}

@api_router.post("/crms")
async def create_crm(crm: CRMCreate, user: dict = Depends(require_admin)):
    crm_doc = {
        "id": str(uuid.uuid4()),
        **crm.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.crms.insert_one(crm_doc)
    await log_activity(user["id"], user["email"], "create", "crm", crm_doc["id"], f"CRM créé: {crm.name}")
    return {"success": True, "crm": {k: v for k, v in crm_doc.items() if k != "_id"}}

@api_router.post("/crms/init")
async def init_crms(user: dict = Depends(require_admin)):
    """Initialize default CRMs, sub-accounts, diffusion sources and product types"""
    existing = await db.crms.count_documents({})
    if existing > 0:
        return {"message": "CRMs déjà initialisés"}
    
    # Create CRMs
    mdl_id = str(uuid.uuid4())
    zr7_id = str(uuid.uuid4())
    crms = [
        {"id": mdl_id, "name": "Maison du Lead", "slug": "mdl", "api_url": "https://maison-du-lead.com/lead/api/create_lead/", "description": "CRM Maison du Lead", "created_at": datetime.now(timezone.utc).isoformat()},
        {"id": zr7_id, "name": "ZR7 Digital", "slug": "zr7", "api_url": "https://app.zr7-digital.fr/lead/api/create_lead/", "description": "CRM ZR7", "created_at": datetime.now(timezone.utc).isoformat()}
    ]
    await db.crms.insert_many(crms)
    
    # Create Accounts (comptes)
    accounts = [
        # MDL accounts
        {"id": str(uuid.uuid4()), "crm_id": mdl_id, "name": "MDL", "domain": "", "product_types": ["solaire", "pac", "isolation"], "created_at": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid.uuid4()), "crm_id": mdl_id, "name": "SPOOT", "domain": "", "product_types": ["solaire", "pac"], "created_at": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid.uuid4()), "crm_id": mdl_id, "name": "OBJECTIF ACADEMIE", "domain": "", "product_types": ["solaire"], "created_at": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid.uuid4()), "crm_id": mdl_id, "name": "AUDIT GREEN", "domain": "", "product_types": ["solaire", "pac", "isolation"], "created_at": datetime.now(timezone.utc).isoformat()},
        # ZR7 accounts
        {"id": str(uuid.uuid4()), "crm_id": zr7_id, "name": "ZR7", "domain": "", "product_types": ["solaire", "pac", "isolation"], "created_at": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid.uuid4()), "crm_id": zr7_id, "name": "AZ", "domain": "", "product_types": ["solaire", "pac"], "created_at": datetime.now(timezone.utc).isoformat()},
    ]
    await db.accounts.insert_many(accounts)
    
    # Create diffusion sources
    diffusion_sources = [
        # Native
        {"id": str(uuid.uuid4()), "name": "Taboola", "category": "native", "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid.uuid4()), "name": "Outbrain", "category": "native", "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid.uuid4()), "name": "MGID", "category": "native", "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid.uuid4()), "name": "Mediago", "category": "native", "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid.uuid4()), "name": "Yahoo Gemini", "category": "native", "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()},
        # Google
        {"id": str(uuid.uuid4()), "name": "Google Ads", "category": "google", "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid.uuid4()), "name": "YouTube Ads", "category": "google", "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()},
        # Meta
        {"id": str(uuid.uuid4()), "name": "Facebook Ads", "category": "facebook", "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid.uuid4()), "name": "Instagram Ads", "category": "facebook", "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()},
        # TikTok
        {"id": str(uuid.uuid4()), "name": "TikTok Ads", "category": "tiktok", "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()},
    ]
    await db.diffusion_sources.insert_many(diffusion_sources)
    
    # Create product types with instructions
    product_types = [
        {
            "id": str(uuid.uuid4()), 
            "name": "Panneaux solaires", 
            "slug": "solaire", 
            "aide_montant": "10 000€",
            "aides_liste": ["MaPrimeRenov", "CEE", "Autoconsommation", "TVA réduite"],
            "description": "Installation de panneaux photovoltaïques",
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()), 
            "name": "Pompe à chaleur", 
            "slug": "pac", 
            "aide_montant": "10 000€",
            "aides_liste": ["MaPrimeRenov", "CEE", "TVA réduite"],
            "description": "Installation de pompe à chaleur air/eau",
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()), 
            "name": "Isolation Extérieure", 
            "slug": "isolation", 
            "aide_montant": "13 000€",
            "aides_liste": ["MaPrimeRenov", "CEE", "TVA réduite"],
            "description": "Isolation thermique par l'extérieur (ITE)",
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
    ]
    await db.product_types.insert_many(product_types)
    
    return {"success": True, "message": "CRMs, comptes, sources de diffusion et types de produits initialisés"}

# ==================== DIFFUSION SOURCES ENDPOINTS ====================

@api_router.get("/diffusion-sources")
async def get_diffusion_sources(category: Optional[str] = None, user: dict = Depends(get_current_user)):
    query = {"category": category} if category else {}
    sources = await db.diffusion_sources.find(query, {"_id": 0}).sort("name", 1).to_list(100)
    return {"sources": sources}

@api_router.post("/diffusion-sources")
async def create_diffusion_source(source: DiffusionSourceCreate, user: dict = Depends(get_current_user)):
    source_doc = {
        "id": str(uuid.uuid4()),
        **source.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.diffusion_sources.insert_one(source_doc)
    return {"success": True, "source": {k: v for k, v in source_doc.items() if k != "_id"}}

@api_router.delete("/diffusion-sources/{source_id}")
async def delete_diffusion_source(source_id: str, user: dict = Depends(require_admin)):
    result = await db.diffusion_sources.delete_one({"id": source_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Source non trouvée")
    return {"success": True}

# ==================== PRODUCT TYPES ENDPOINTS ====================

@api_router.get("/product-types")
async def get_product_types(user: dict = Depends(get_current_user)):
    types = await db.product_types.find({}, {"_id": 0}).to_list(100)
    return {"product_types": types}

@api_router.post("/product-types")
async def create_product_type(product: ProductTypeCreate, user: dict = Depends(get_current_user)):
    product_doc = {
        "id": str(uuid.uuid4()),
        **product.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.product_types.insert_one(product_doc)
    return {"success": True, "product_type": {k: v for k, v in product_doc.items() if k != "_id"}}

@api_router.put("/product-types/{type_id}")
async def update_product_type(type_id: str, product: ProductTypeCreate, user: dict = Depends(get_current_user)):
    result = await db.product_types.update_one(
        {"id": type_id},
        {"$set": {**product.model_dump(), "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Type de produit non trouvé")
    return {"success": True}

@api_router.delete("/product-types/{type_id}")
async def delete_product_type(type_id: str, user: dict = Depends(require_admin)):
    result = await db.product_types.delete_one({"id": type_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Type de produit non trouvé")
    return {"success": True}

# ==================== ACCOUNT ENDPOINTS (renamed from sub-accounts) ====================

@api_router.get("/accounts")
async def get_accounts(crm_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    query = {"crm_id": crm_id} if crm_id else {}
    
    # Appliquer le filtre par comptes autorisés (sécurité multi-tenant)
    account_filter = get_account_filter(user)
    if account_filter:
        query = {**query, **account_filter}
    
    accounts = await db.accounts.find(query, {"_id": 0}).to_list(100)
    return {"accounts": accounts}

# Keep old route for backwards compatibility
@api_router.get("/sub-accounts")
async def get_sub_accounts_compat(crm_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    query = {"crm_id": crm_id} if crm_id else {}
    accounts = await db.accounts.find(query, {"_id": 0}).to_list(100)
    return {"sub_accounts": accounts, "accounts": accounts}

@api_router.get("/accounts/{account_id}")
async def get_account(account_id: str, user: dict = Depends(get_current_user)):
    account = await db.accounts.find_one({"id": account_id}, {"_id": 0})
    if not account:
        raise HTTPException(status_code=404, detail="Compte non trouvé")
    return {"account": account}

@api_router.get("/sub-accounts/{account_id}")
async def get_sub_account_compat(account_id: str, user: dict = Depends(get_current_user)):
    account = await db.accounts.find_one({"id": account_id}, {"_id": 0})
    if not account:
        raise HTTPException(status_code=404, detail="Sous-compte non trouvé")
    return account

@api_router.post("/accounts")
async def create_account(account: AccountCreate, user: dict = Depends(get_current_user)):
    account_doc = {
        "id": str(uuid.uuid4()),
        **account.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user["id"]
    }
    await db.accounts.insert_one(account_doc)
    await log_activity(user["id"], user["email"], "create", "account", account_doc["id"], f"Compte créé: {account.name}")
    return {"success": True, "account": {k: v for k, v in account_doc.items() if k != "_id"}}

# Keep old route for backwards compatibility
@api_router.post("/sub-accounts")
async def create_sub_account_compat(account: AccountCreate, user: dict = Depends(get_current_user)):
    return await create_account(account, user)

@api_router.put("/accounts/{account_id}")
async def update_account(account_id: str, account: AccountCreate, user: dict = Depends(get_current_user)):
    result = await db.accounts.update_one(
        {"id": account_id},
        {"$set": {**account.model_dump(), "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Compte non trouvé")
    await log_activity(user["id"], user["email"], "update", "account", account_id, f"Compte modifié: {account.name}")
    return {"success": True}

@api_router.put("/sub-accounts/{account_id}")
async def update_sub_account_compat(account_id: str, account: SubAccountCreate, user: dict = Depends(get_current_user)):
    result = await db.accounts.update_one(
        {"id": account_id},
        {"$set": {**account.model_dump(), "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Sous-compte non trouvé")
    await log_activity(user["id"], user["email"], "update", "sub_account", account_id, f"Sous-compte modifié: {account.name}")
    return {"success": True}

@api_router.delete("/accounts/{account_id}")
async def delete_account(account_id: str, user: dict = Depends(require_admin)):
    result = await db.accounts.delete_one({"id": account_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Compte non trouvé")
    await log_activity(user["id"], user["email"], "delete", "account", account_id, "Compte supprimé")
    return {"success": True}

@api_router.delete("/sub-accounts/{account_id}")
async def delete_sub_account_compat(account_id: str, user: dict = Depends(require_admin)):
    result = await db.accounts.delete_one({"id": account_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Sous-compte non trouvé")
    await log_activity(user["id"], user["email"], "delete", "sub_account", account_id, "Sous-compte supprimé")
    return {"success": True}

# ==================== ASSETS ENDPOINTS ====================

@api_router.get("/assets")
async def get_assets(crm_id: Optional[str] = None, sub_account_id: Optional[str] = None, global_only: bool = False, user: dict = Depends(get_current_user)):
    """Get assets - can filter by CRM, sub-account, or get only global assets"""
    query = {}
    
    if global_only:
        query["sub_account_id"] = None
    elif sub_account_id:
        # Get assets for specific sub-account + global assets
        query["$or"] = [{"sub_account_id": sub_account_id}, {"sub_account_id": None}]
    elif crm_id:
        # Get assets for all sub-accounts of this CRM + global assets
        sub_accounts = await db.accounts.find({"crm_id": crm_id}, {"id": 1}).to_list(100)
        sub_account_ids = [sa["id"] for sa in sub_accounts]
        query["$or"] = [{"sub_account_id": {"$in": sub_account_ids}}, {"sub_account_id": None}, {"crm_id": crm_id}]
    
    assets = await db.assets.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"assets": assets}

@api_router.post("/assets")
async def create_asset(asset: AssetCreate, user: dict = Depends(get_current_user)):
    asset_doc = {
        "id": str(uuid.uuid4()),
        **asset.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user["id"]
    }
    await db.assets.insert_one(asset_doc)
    await log_activity(user["id"], user["email"], "create", "asset", asset_doc["id"], f"Asset créé: {asset.label}")
    return {"success": True, "asset": {k: v for k, v in asset_doc.items() if k != "_id"}}

@api_router.put("/assets/{asset_id}")
async def update_asset(asset_id: str, asset: AssetCreate, user: dict = Depends(get_current_user)):
    result = await db.assets.update_one(
        {"id": asset_id},
        {"$set": {**asset.model_dump(), "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Asset non trouvé")
    await log_activity(user["id"], user["email"], "update", "asset", asset_id, f"Asset modifié: {asset.label}")
    return {"success": True}

@api_router.delete("/assets/{asset_id}")
async def delete_asset(asset_id: str, user: dict = Depends(require_admin)):
    """Delete an asset - Admin only"""
    result = await db.assets.delete_one({"id": asset_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Asset non trouvé")
    await log_activity(user["id"], user["email"], "delete", "asset", asset_id, "Asset supprimé")
    return {"success": True}

# ==================== LP ENDPOINTS ====================

@api_router.get("/lps")
async def get_lps(sub_account_id: Optional[str] = None, crm_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    query = {}
    
    # Appliquer le filtre par comptes autorisés (sécurité multi-tenant)
    account_filter = get_account_ids_filter(user)
    allowed_account_ids = user.get("allowed_accounts", []) if user.get("role") != "admin" and user.get("allowed_accounts") else None
    
    if sub_account_id:
        # Vérifier que l'utilisateur a accès à ce compte
        if allowed_account_ids and sub_account_id not in allowed_account_ids:
            return {"lps": []}
        query["sub_account_id"] = sub_account_id
    elif crm_id:
        # Get all sub-accounts for this CRM
        crm_query = {"crm_id": crm_id}
        if allowed_account_ids:
            crm_query["id"] = {"$in": allowed_account_ids}
        sub_accounts = await db.accounts.find(crm_query, {"id": 1}).to_list(100)
        sub_account_ids = [sa["id"] for sa in sub_accounts]
        if sub_account_ids:
            query["sub_account_id"] = {"$in": sub_account_ids}
        else:
            return {"lps": []}
    elif allowed_account_ids:
        # Pas de filtre CRM, mais l'utilisateur a des restrictions
        query["sub_account_id"] = {"$in": allowed_account_ids}
    
    lps = await db.lps.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    # Add stats for each LP
    for lp in lps:
        lp["stats"] = {
            "cta_clicks": await db.cta_clicks.count_documents({"lp_code": lp["code"]}),
            "forms_started": await db.form_starts.count_documents({"lp_code": lp["code"]}),
            "leads": await db.leads.count_documents({"lp_code": lp["code"]})
        }
    
    return {"lps": lps}

@api_router.get("/lps/{lp_id}")
async def get_lp(lp_id: str, user: dict = Depends(get_current_user)):
    lp = await db.lps.find_one({"id": lp_id}, {"_id": 0})
    if not lp:
        raise HTTPException(status_code=404, detail="LP non trouvée")
    return lp

@api_router.post("/lps")
async def create_lp(lp: LPCreate, user: dict = Depends(get_current_user)):
    lp_doc = {
        "id": str(uuid.uuid4()),
        **lp.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user["id"]
    }
    await db.lps.insert_one(lp_doc)
    await log_activity(user["id"], user["email"], "create", "lp", lp_doc["id"], f"LP créée: {lp.code}")
    return {"success": True, "lp": {k: v for k, v in lp_doc.items() if k != "_id"}}

@api_router.put("/lps/{lp_id}")
async def update_lp(lp_id: str, lp: LPCreate, user: dict = Depends(get_current_user)):
    result = await db.lps.update_one(
        {"id": lp_id},
        {"$set": {**lp.model_dump(), "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="LP non trouvée")
    await log_activity(user["id"], user["email"], "update", "lp", lp_id, f"LP modifiée: {lp.code}")
    return {"success": True}

@api_router.delete("/lps/{lp_id}")
async def delete_lp(lp_id: str, user: dict = Depends(require_admin)):
    result = await db.lps.delete_one({"id": lp_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="LP non trouvée")
    await log_activity(user["id"], user["email"], "delete", "lp", lp_id, "LP supprimée")
    return {"success": True}

@api_router.post("/lps/{lp_id}/duplicate")
async def duplicate_lp(lp_id: str, new_code: str, new_name: str, user: dict = Depends(get_current_user)):
    """Duplicate a LP with a new code and name"""
    lp = await db.lps.find_one({"id": lp_id}, {"_id": 0})
    if not lp:
        raise HTTPException(status_code=404, detail="LP non trouvée")
    
    # Create new LP with same config but new code/name
    new_lp = {
        **lp,
        "id": str(uuid.uuid4()),
        "code": new_code,
        "name": new_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user["id"],
        "status": "active"
    }
    # Remove updated_at if exists
    new_lp.pop("updated_at", None)
    
    await db.lps.insert_one(new_lp)
    await log_activity(user["id"], user["email"], "duplicate", "lp", new_lp["id"], f"LP dupliquée: {lp['code']} -> {new_code}")
    return {"success": True, "lp": {k: v for k, v in new_lp.items() if k != "_id"}}

# ==================== FORM ENDPOINTS ====================

@api_router.get("/forms")
async def get_forms(
    sub_account_id: Optional[str] = None, 
    crm_id: Optional[str] = None, 
    product_type: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    query = {}
    
    # Appliquer le filtre par comptes autorisés (sécurité multi-tenant)
    allowed_account_ids = user.get("allowed_accounts", []) if user.get("role") != "admin" and user.get("allowed_accounts") else None
    
    if sub_account_id:
        # Vérifier que l'utilisateur a accès à ce compte
        if allowed_account_ids and sub_account_id not in allowed_account_ids:
            return {"forms": []}
        query["sub_account_id"] = sub_account_id
    elif crm_id:
        # Get all sub-accounts for this CRM
        crm_query = {"crm_id": crm_id}
        if allowed_account_ids:
            crm_query["id"] = {"$in": allowed_account_ids}
        sub_accounts = await db.accounts.find(crm_query, {"id": 1}).to_list(100)
        sub_account_ids = [sa["id"] for sa in sub_accounts]
        if sub_account_ids:
            query["sub_account_id"] = {"$in": sub_account_ids}
        else:
            return {"forms": []}
    elif allowed_account_ids:
        # Pas de filtre CRM, mais l'utilisateur a des restrictions
        query["sub_account_id"] = {"$in": allowed_account_ids}
    
    # Filtre par type de produit
    if product_type:
        query["product_type"] = product_type
    
    forms = await db.forms.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    # Add stats for each form
    for form in forms:
        form["stats"] = {
            "started": await db.form_starts.count_documents({"form_code": form["code"]}),
            "completed": await db.leads.count_documents({"form_code": form["code"]}),
            "success": await db.leads.count_documents({"form_code": form["code"], "api_status": "success"}),
            "failed": await db.leads.count_documents({"form_code": form["code"], "api_status": "failed"})
        }
        if form["stats"]["started"] > 0:
            form["stats"]["conversion_rate"] = round(form["stats"]["completed"] / form["stats"]["started"] * 100, 1)
        else:
            form["stats"]["conversion_rate"] = 0
    
    return {"forms": forms}

@api_router.get("/forms/{form_id}")
async def get_form(form_id: str, user: dict = Depends(get_current_user)):
    form = await db.forms.find_one({"id": form_id}, {"_id": 0})
    if not form:
        raise HTTPException(status_code=404, detail="Formulaire non trouvé")
    return form

@api_router.post("/forms")
async def create_form(form: FormCreate, user: dict = Depends(get_current_user)):
    # Générer une clé API interne unique pour ce CRM
    internal_api_key = str(uuid.uuid4())
    
    form_doc = {
        "id": str(uuid.uuid4()),
        **form.model_dump(),
        "internal_api_key": internal_api_key,  # Clé pour recevoir les leads sur CE CRM
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user["id"]
    }
    await db.forms.insert_one(form_doc)
    await log_activity(user["id"], user["email"], "create", "form", form_doc["id"], f"Formulaire créé: {form.code}")
    return {"success": True, "form": {k: v for k, v in form_doc.items() if k != "_id"}}

@api_router.put("/forms/{form_id}")
async def update_form(form_id: str, form: FormCreate, user: dict = Depends(get_current_user)):
    """
    Mettre à jour un formulaire.
    PROTECTION: La clé API CRM (crm_api_key) ne peut PAS être modifiée après création.
    Seul le code, nom, et paramètres non-critiques peuvent être changés.
    """
    # Récupérer le formulaire existant pour préserver les champs protégés
    existing_form = await db.forms.find_one({"id": form_id}, {"_id": 0})
    if not existing_form:
        raise HTTPException(status_code=404, detail="Formulaire non trouvé")
    
    # Préparer les données de mise à jour
    update_data = form.model_dump()
    
    # ============ CHAMPS PROTÉGÉS (non modifiables après création) ============
    
    # PROTECTION 1: Le CODE FORMULAIRE ne peut JAMAIS être modifié
    # (sinon les formulaires web externes cesseraient de fonctionner)
    update_data["code"] = existing_form["code"]
    
    # PROTECTION 2: Préserver la clé API CRM d'origine
    if existing_form.get("crm_api_key"):
        update_data["crm_api_key"] = existing_form["crm_api_key"]
    
    # PROTECTION 3: Préserver internal_api_key
    if existing_form.get("internal_api_key"):
        update_data["internal_api_key"] = existing_form["internal_api_key"]
    
    # PROTECTION 4: Préserver le product_type d'origine (critique pour le routage)
    if existing_form.get("product_type"):
        update_data["product_type"] = existing_form["product_type"]
    
    # PROTECTION 5: Préserver le sub_account_id (lien avec le compte)
    if existing_form.get("sub_account_id"):
        update_data["sub_account_id"] = existing_form["sub_account_id"]
    
    # =========================================================================
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.forms.update_one(
        {"id": form_id},
        {"$set": update_data}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Formulaire non trouvé")
    await log_activity(user["id"], user["email"], "update", "form", form_id, f"Formulaire modifié: {existing_form['code']}")
    return {"success": True, "protected_fields": ["code", "crm_api_key", "product_type", "sub_account_id"]}

@api_router.delete("/forms/{form_id}")
async def delete_form(form_id: str, user: dict = Depends(require_admin)):
    """
    ARCHIVE un formulaire au lieu de le supprimer définitivement.
    - Les leads associés restent dans la base avec leur product_type
    - Le formulaire est marqué comme 'archived' mais reste consultable
    - Seul l'admin peut archiver/supprimer
    """
    # Vérifier que le formulaire existe
    form = await db.forms.find_one({"id": form_id}, {"_id": 0})
    if not form:
        raise HTTPException(status_code=404, detail="Formulaire non trouvé")
    
    # ARCHIVER au lieu de supprimer
    await db.forms.update_one(
        {"id": form_id},
        {"$set": {
            "status": "archived",
            "archived_at": datetime.now(timezone.utc).isoformat(),
            "archived_by": user["id"]
        }}
    )
    
    # Compter les leads associés (ils restent dans la base)
    leads_count = await db.leads.count_documents({"form_code": form.get("code")})
    
    await log_activity(user["id"], user["email"], "archive", "form", form_id, 
                      f"Formulaire archivé: {form.get('code')} ({leads_count} leads conservés)")
    
    return {"success": True, "message": f"Formulaire archivé. {leads_count} leads conservés dans la base."}

@api_router.delete("/forms/{form_id}/permanent")
async def permanent_delete_form(form_id: str, confirm_code: str, user: dict = Depends(require_admin)):
    """
    Suppression PERMANENTE d'un formulaire - UNIQUEMENT pour l'admin avec code de confirmation.
    Les leads restent TOUJOURS dans la base avec leur product_type.
    """
    # Vérifier le code de confirmation (les 8 premiers caractères de l'ID)
    if confirm_code != form_id[:8]:
        raise HTTPException(status_code=400, detail=f"Code de confirmation incorrect. Entrez les 8 premiers caractères de l'ID: {form_id[:8]}")
    
    form = await db.forms.find_one({"id": form_id}, {"_id": 0})
    if not form:
        raise HTTPException(status_code=404, detail="Formulaire non trouvé")
    
    # Compter les leads qui resteront
    leads_count = await db.leads.count_documents({"form_code": form.get("code")})
    
    # Supprimer le formulaire
    result = await db.forms.delete_one({"id": form_id})
    
    await log_activity(user["id"], user["email"], "permanent_delete", "form", form_id, 
                      f"Formulaire SUPPRIMÉ: {form.get('code')} ({leads_count} leads conservés)")
    
    return {"success": True, "message": f"Formulaire supprimé définitivement. {leads_count} leads conservés."}
    return {"success": True}

@api_router.post("/forms/generate-missing-keys")
async def generate_missing_api_keys(user: dict = Depends(require_admin)):
    """Générer les clés API internes pour les formulaires qui n'en ont pas"""
    forms_without_key = await db.forms.find(
        {"$or": [{"internal_api_key": {"$exists": False}}, {"internal_api_key": ""}]}
    ).to_list(1000)
    
    updated_count = 0
    for form in forms_without_key:
        new_key = str(uuid.uuid4())
        await db.forms.update_one(
            {"id": form["id"]},
            {"$set": {"internal_api_key": new_key}}
        )
        updated_count += 1
    
    return {"success": True, "updated_count": updated_count}

@api_router.post("/forms/{form_id}/regenerate-key")
async def regenerate_form_api_key(form_id: str, user: dict = Depends(get_current_user)):
    """Régénérer la clé API interne d'un formulaire"""
    new_key = str(uuid.uuid4())
    result = await db.forms.update_one(
        {"id": form_id},
        {"$set": {"internal_api_key": new_key}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Formulaire non trouvé")
    await log_activity(user["id"], user["email"], "regenerate_key", "form", form_id, "Clé API régénérée")
    return {"success": True, "internal_api_key": new_key}

@api_router.post("/forms/{form_id}/duplicate")
async def duplicate_form(form_id: str, new_code: str, new_name: str, new_crm_api_key: str, user: dict = Depends(get_current_user)):
    """Duplicate a Form with a new code, name, and CRM API key"""
    form = await db.forms.find_one({"id": form_id}, {"_id": 0})
    if not form:
        raise HTTPException(status_code=404, detail="Formulaire non trouvé")
    
    # Générer une nouvelle clé API interne pour le formulaire dupliqué
    new_internal_api_key = str(uuid.uuid4())
    
    # Create new form with same config but new code/name/api_keys
    new_form = {
        **form,
        "id": str(uuid.uuid4()),
        "code": new_code,
        "name": new_name,
        "crm_api_key": new_crm_api_key,  # Nouvelle clé API ZR7/MDL
        "internal_api_key": new_internal_api_key,  # Nouvelle clé interne
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user["id"],
        "status": "active"
    }
    # Remove old api_key field and updated_at if exists
    new_form.pop("api_key", None)
    new_form.pop("updated_at", None)
    
    await db.forms.insert_one(new_form)
    await log_activity(user["id"], user["email"], "duplicate", "form", new_form["id"], f"Formulaire dupliqué: {form['code']} -> {new_code}")
    return {"success": True, "form": {k: v for k, v in new_form.items() if k != "_id"}}

# ==================== TRACKING ENDPOINTS (PUBLIC) ====================

@api_router.post("/track/cta-click")
async def track_cta_click(data: CTAClickTrack):
    """Track CTA clicks on LPs - called from LP tracking script"""
    await db.cta_clicks.insert_one({
        "id": str(uuid.uuid4()),
        "lp_code": data.lp_code,
        "domain": data.domain,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    return {"success": True}

@api_router.post("/track/form-start")
async def track_form_start(data: FormStartTrack):
    """Track form starts - called when form is loaded"""
    await db.form_starts.insert_one({
        "id": str(uuid.uuid4()),
        "form_code": data.form_code,
        "lp_code": data.lp_code,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    return {"success": True}

# ==================== LEAD SUBMISSION ====================

async def send_lead_to_crm(lead_doc: dict, api_url: str, api_key: str) -> tuple:
    """Helper function to send a lead to external CRM (ZR7/MDL)
    Format conforme à la doc API ZR7/MDL
    """
    # Build custom_fields avec tous les champs de la doc
    custom_fields = {}
    
    # Ajouter chaque champ s'il existe
    if lead_doc.get("superficie_logement"):
        custom_fields["superficie_logement"] = {"value": lead_doc["superficie_logement"]}
    if lead_doc.get("chauffage_actuel"):
        custom_fields["chauffage_actuel"] = {"value": lead_doc["chauffage_actuel"]}
    if lead_doc.get("departement"):
        custom_fields["departement"] = {"value": lead_doc["departement"]}
    if lead_doc.get("code_postal"):
        custom_fields["code_postal"] = {"value": lead_doc["code_postal"]}
    if lead_doc.get("type_logement"):
        custom_fields["type_logement"] = {"value": lead_doc["type_logement"]}
    if lead_doc.get("statut_occupant"):
        custom_fields["statut_occupant"] = {"value": lead_doc["statut_occupant"]}
    if lead_doc.get("facture_electricite"):
        custom_fields["facture_electricite"] = {"value": lead_doc["facture_electricite"]}
    
    lead_payload = {
        "phone": lead_doc["phone"],
        "register_date": lead_doc["register_date"],
        "nom": lead_doc.get("nom", ""),
        "prenom": lead_doc.get("prenom", ""),
        "email": lead_doc.get("email", ""),
    }
    
    # Ajouter civilite si présent (champ standard selon doc API)
    if lead_doc.get("civilite"):
        lead_payload["civilite"] = lead_doc["civilite"]
    
    # Ajouter custom_fields seulement s'il y en a
    if custom_fields:
        lead_payload["custom_fields"] = custom_fields
    
    api_status = "failed"
    api_response = None
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            response = await http_client.post(
                api_url,
                json=lead_payload,
                headers={"Authorization": api_key, "Content-Type": "application/json"}
            )
            data = response.json()
            api_response = str(data)
            
            if response.status_code == 201:
                api_status = "success"
            elif "doublon" in str(data.get("message", "")).lower():
                api_status = "duplicate"
            else:
                api_status = "failed"
    except Exception as e:
        api_status = "failed"
        api_response = str(e)
    
    return api_status, api_response

# ==================== NOUVEAU SYSTÈME API v1 (Style Landbot) ====================

class LeadDataV1(BaseModel):
    """
    Modèle pour le nouveau système API v1 avec clé globale.
    L'authentification se fait via le header Authorization.
    """
    form_id: str  # Identifiant unique du formulaire
    phone: str  # Obligatoire
    nom: Optional[str] = ""
    prenom: Optional[str] = ""
    civilite: Optional[str] = ""  # M., Mme
    email: Optional[str] = ""
    departement: Optional[str] = ""
    code_postal: Optional[str] = ""
    superficie_logement: Optional[str] = ""
    chauffage_actuel: Optional[str] = ""
    type_logement: Optional[str] = ""
    statut_occupant: Optional[str] = ""
    facture_electricite: Optional[str] = ""

from fastapi import Header

@api_router.post("/v1/leads")
async def submit_lead_v1(
    lead: LeadDataV1,
    authorization: Optional[str] = Header(None)
):
    """
    🚀 NOUVEAU ENDPOINT API v1 - Style Landbot
    
    Authentification via header (pas dans le body):
    - Header: Authorization: Token VOTRE_CLE_API_GLOBALE
    - Body: { "form_id": "abc123", "phone": "0612345678", ... }
    
    La clé API globale est visible dans: Paramètres > Clé API
    Chaque formulaire a un form_id unique visible dans: Formulaires
    """
    # Vérifier l'authentification par header
    if not authorization:
        raise HTTPException(
            status_code=401, 
            detail={
                "error": "Clé API manquante",
                "help": "Ajoutez le header: Authorization: Token VOTRE_CLE_API",
                "get_key": "Paramètres > Clé API dans le dashboard"
            }
        )
    
    # Vérifier la clé API globale
    is_valid = await verify_global_api_key(authorization)
    if not is_valid:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Clé API invalide",
                "help": "Vérifiez votre clé dans: Paramètres > Clé API"
            }
        )
    
    # Valider les données
    phone = lead.phone.strip() if lead.phone else ""
    if not phone:
        raise HTTPException(status_code=400, detail="Le numéro de téléphone est requis")
    
    form_id = lead.form_id.strip() if lead.form_id else ""
    if not form_id:
        raise HTTPException(status_code=400, detail="Le form_id est requis")
    
    # Chercher le formulaire par son ID unique
    form_config = await db.forms.find_one({"id": form_id})
    if not form_config:
        # Essayer aussi par code (rétrocompatibilité)
        form_config = await db.forms.find_one({"code": form_id})
    
    if not form_config:
        raise HTTPException(
            status_code=404, 
            detail={
                "error": "Formulaire non trouvé",
                "form_id": form_id,
                "help": "Vérifiez le form_id dans: Formulaires"
            }
        )
    
    # Vérifier que le formulaire n'est pas archivé
    if form_config.get("status") == "archived":
        raise HTTPException(status_code=403, detail="Ce formulaire est archivé et n'accepte plus de leads.")
    
    # Le reste du traitement est identique à l'ancien endpoint
    timestamp = int(datetime.now(timezone.utc).timestamp())
    
    account_id = form_config.get("account_id") or form_config.get("sub_account_id")
    account = await db.accounts.find_one({"id": account_id}) if account_id else None
    origin_crm = await db.crms.find_one({"id": account.get("crm_id")}) if account else None
    
    # Type de produit du formulaire
    product_type = form_config.get("product_type", "PV").upper()
    product_map = {"PANNEAUX": "PV", "POMPES": "PAC", "ISOLATION": "ITE", "SOLAIRE": "PV"}
    product_type = product_map.get(product_type, product_type)
    
    departement = lead.departement or ""
    
    # Vérifier si ce formulaire est exclu du routage inter-CRM
    exclude_from_routing = form_config.get("exclude_from_routing", False)
    
    # Variables pour le routage
    target_crm = origin_crm
    routing_reason = "direct_to_origin"
    api_url = form_config.get("crm_api_url") or (origin_crm.get("api_url") if origin_crm else None)
    api_key = form_config.get("crm_api_key") or (origin_crm.get("api_key") if origin_crm else None)
    can_send = bool(api_url and api_key)
    
    # Anti-doublon amélioré
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    existing_lead = await db.leads.find_one({
        "phone": phone,
        "product_type": product_type,
        "created_at": {"$gte": today_start}
    })
    
    if existing_lead:
        return {
            "success": False,
            "status": "duplicate_today",
            "message": f"Ce numéro a déjà soumis un lead {product_type} aujourd'hui"
        }
    
    # Stocker le lead
    lead_doc = {
        "id": str(uuid.uuid4()),
        "form_id": form_config.get("id", ""),
        "form_code": form_config.get("code", ""),
        "lp_code": "",
        "account_id": account_id or "",
        "product_type": product_type,
        "origin_crm_id": origin_crm.get("id") if origin_crm else "",
        "origin_crm_name": origin_crm.get("name") if origin_crm else "",
        "origin_crm_slug": origin_crm.get("slug") if origin_crm else "",
        "target_crm_id": target_crm.get("id") if target_crm else "",
        "target_crm_name": target_crm.get("name") if target_crm else "",
        "target_crm_slug": target_crm.get("slug") if target_crm else "",
        "routing_reason": routing_reason,
        "phone": phone,
        "nom": (lead.nom or "").strip(),
        "prenom": (lead.prenom or "").strip(),
        "civilite": lead.civilite or "",
        "email": lead.email or "",
        "departement": departement,
        "code_postal": lead.code_postal or "",
        "superficie_logement": lead.superficie_logement or "",
        "chauffage_actuel": lead.chauffage_actuel or "",
        "type_logement": lead.type_logement or "",
        "statut_occupant": lead.statut_occupant or "",
        "facture_electricite": lead.facture_electricite or "",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "register_date": timestamp,
        "api_status": "pending" if can_send else "no_config",
        "api_url": api_url,
        "sent_to_crm": False,
        "retry_count": 0,
        "api_version": "v1"  # Marqueur pour savoir que c'est via la nouvelle API
    }
    
    await db.leads.insert_one(lead_doc)
    
    api_status = "no_config"
    
    if can_send:
        api_status, api_response = await send_lead_to_crm(lead_doc, api_url, api_key)
        
        status_detail = f"{api_status}"
        if api_status == "success":
            status_detail = f"envoyé/{target_crm.get('slug', 'crm')}"
        elif api_status == "duplicate":
            status_detail = f"doublon/{target_crm.get('slug', 'crm')}"
        
        await db.leads.update_one(
            {"id": lead_doc["id"]},
            {"$set": {
                "api_status": api_status,
                "status_detail": status_detail,
                "api_response": api_response,
                "sent_to_crm": api_status in ["success", "duplicate"],
                "sent_at": datetime.now(timezone.utc).isoformat()
            }}
        )
    
    return {
        "success": True if api_status in ["success", "duplicate", "no_config"] else False,
        "lead_id": lead_doc["id"],
        "status": api_status,
        "product_type": product_type,
        "target_crm": target_crm.get("name") if target_crm else None,
        "message": "Lead enregistré et envoyé" if api_status == "success" else "Lead enregistré"
    }

# ==================== ANCIEN ENDPOINT (rétrocompatibilité) ====================

@api_router.post("/submit-lead")
async def submit_lead(lead: LeadData):
    """
    Soumission de lead avec ROUTAGE INTELLIGENT (OPTIONNEL) :
    
    SÉCURITÉ : La clé API (api_key) est OBLIGATOIRE pour authentifier la requête.
    
    SI les commandes sont configurées sur les CRMs :
      1. Vérifier si le CRM d'origine a une commande pour ce produit/département
      2. Si NON, vérifier si l'autre CRM a une commande
      3. Si AUCUN n'a de commande, envoyer au CRM d'origine (fallback)
    
    SI les commandes NE SONT PAS configurées :
      → Envoi normal vers le CRM d'origine du formulaire
    
    Protection anti-doublon : pas d'envoi 2 fois le même jour
    """
    timestamp = lead.register_date or int(datetime.now(timezone.utc).timestamp())
    phone = lead.phone.strip() if lead.phone else ""
    
    if not phone:
        raise HTTPException(status_code=400, detail="Le numéro de téléphone est requis")
    
    # ============ SÉCURITÉ : VÉRIFICATION CLÉ API ============
    api_key = lead.api_key.strip() if lead.api_key else ""
    form_code = lead.form_code.strip() if lead.form_code else ""
    
    if not api_key:
        raise HTTPException(status_code=401, detail="Clé API manquante. Ajoutez 'api_key' dans votre requête.")
    
    # Chercher le formulaire par clé API
    form_config = await db.forms.find_one({"internal_api_key": api_key})
    
    if not form_config:
        raise HTTPException(status_code=401, detail="Clé API invalide ou formulaire non trouvé.")
    
    # Si form_code fourni, vérifier qu'il correspond
    if form_code and form_config.get("code") != form_code:
        raise HTTPException(status_code=401, detail="Le form_code ne correspond pas à la clé API.")
    
    # Vérifier que le formulaire n'est pas archivé
    if form_config.get("status") == "archived":
        raise HTTPException(status_code=403, detail="Ce formulaire est archivé et n'accepte plus de leads.")
    # =========================================================
    
    account_id = form_config.get("account_id") or form_config.get("sub_account_id")
    account = await db.accounts.find_one({"id": account_id}) if account_id else None
    origin_crm = await db.crms.find_one({"id": account.get("crm_id")}) if account else None
    
    # Type de produit du formulaire (PAC, PV, ITE)
    product_type = form_config.get("product_type", "PV").upper()
    product_map = {"PANNEAUX": "PV", "POMPES": "PAC", "ISOLATION": "ITE", "SOLAIRE": "PV"}
    product_type = product_map.get(product_type, product_type)
    
    departement = lead.departement or ""
    
    # Vérifier si ce formulaire est exclu du routage inter-CRM
    exclude_from_routing = form_config.get("exclude_from_routing", False)
    
    # === PROTECTION ANTI-DOUBLON (même téléphone + même produit par jour) ===
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    existing_today = await db.leads.find_one({
        "phone": phone,
        "product_type": product_type,  # Même produit
        "sent_to_crm": True,
        "created_at": {"$gte": today_start.isoformat()}
    })
    
    if existing_today:
        lead_doc = {
            "id": str(uuid.uuid4()),
            "form_id": lead.form_id or "",
            "form_code": lead.form_code or "",
            "lp_code": lead.lp_code or "",
            "account_id": account_id or "",
            "product_type": product_type,
            "phone": phone,
            "nom": (lead.nom or "").strip(),
            "prenom": (lead.prenom or "").strip(),
            "civilite": lead.civilite or "",
            "email": lead.email or "",
            "departement": departement,
            "code_postal": lead.code_postal or "",
            "superficie_logement": lead.superficie_logement or "",
            "chauffage_actuel": lead.chauffage_actuel or "",
            "type_logement": lead.type_logement or "",
            "statut_occupant": lead.statut_occupant or "",
            "facture_electricite": lead.facture_electricite or "",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "register_date": timestamp,
            "api_status": "duplicate_today",
            "api_response": f"Doublon {product_type} du jour (lead_id: {existing_today['id']})",
            "sent_to_crm": False,
            "retry_count": 0
        }
        await db.leads.insert_one(lead_doc)
        return {"success": True, "message": f"Lead enregistré (doublon {product_type} du jour)", "status": "duplicate_today"}
    
    # === ROUTAGE ===
    target_crm = origin_crm
    routing_reason = "direct_to_origin"
    
    # Vérifier si les commandes sont configurées sur le CRM d'origine
    origin_commandes = origin_crm.get("commandes", {}) if origin_crm else {}
    commandes_actives = bool(origin_commandes and any(origin_commandes.values()))
    
    # Routage intelligent SEULEMENT si:
    # - Commandes configurées
    # - Département présent
    # - Formulaire NON exclu du routage
    if commandes_actives and departement and not exclude_from_routing:
        # Les commandes sont configurées → routage intelligent
        origin_depts = origin_commandes.get(product_type, [])
        
        if departement in origin_depts:
            # CRM d'origine a la commande
            target_crm = origin_crm
            routing_reason = "origin_has_order"
        else:
            # Chercher un autre CRM qui a la commande
            all_crms = await db.crms.find({}, {"_id": 0}).to_list(10)
            found_other = False
            
            for other_crm in all_crms:
                if other_crm.get("id") != origin_crm.get("id"):
                    other_commandes = other_crm.get("commandes", {})
                    other_depts = other_commandes.get(product_type, [])
                    
                    if departement in other_depts:
                        # Vérifier la limite de leads inter-CRM pour ce produit
                        routing_limits = other_crm.get("routing_limits", {})
                        limit = routing_limits.get(product_type, 0)
                        
                        if limit > 0:
                            # Compter les leads déjà routés ce mois vers ce CRM pour ce produit
                            now = datetime.now(timezone.utc)
                            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                            rerouted_count = await db.leads.count_documents({
                                "target_crm_id": other_crm.get("id"),
                                "product_type": product_type,
                                "routing_reason": {"$regex": "^rerouted_"},
                                "created_at": {"$gte": month_start.isoformat()}
                            })
                            
                            if rerouted_count >= limit:
                                # Limite atteinte, ne pas rerouter vers ce CRM
                                continue
                        
                        target_crm = other_crm
                        routing_reason = f"rerouted_to_{other_crm.get('slug', 'other')}"
                        found_other = True
                        break
            
            if not found_other:
                # Aucun CRM n'a la commande ou limites atteintes → fallback origine
                target_crm = origin_crm
                routing_reason = "no_order_fallback_origin"
    
    # Déterminer l'URL et la clé API
    api_url = target_crm.get("api_url", "") if target_crm else ""
    api_key = form_config.get("crm_api_key") or form_config.get("api_key") or ""
    
    can_send = bool(phone and api_url and api_key)
    
    # Stocker le lead avec infos complètes de la plateforme cible
    lead_doc = {
        "id": str(uuid.uuid4()),
        "form_id": lead.form_id or "",
        "form_code": lead.form_code or "",
        "lp_code": lead.lp_code or "",
        "account_id": account_id or "",
        "product_type": product_type,
        "origin_crm_id": origin_crm.get("id") if origin_crm else "",
        "origin_crm_name": origin_crm.get("name") if origin_crm else "",
        "origin_crm_slug": origin_crm.get("slug") if origin_crm else "",
        "target_crm_id": target_crm.get("id") if target_crm else "",
        "target_crm_name": target_crm.get("name") if target_crm else "",
        "target_crm_slug": target_crm.get("slug") if target_crm else "",
        "routing_reason": routing_reason,
        "phone": phone,
        "nom": (lead.nom or "").strip(),
        "prenom": (lead.prenom or "").strip(),
        "civilite": lead.civilite or "",
        "email": lead.email or "",
        "departement": departement,
        "code_postal": lead.code_postal or "",
        "superficie_logement": lead.superficie_logement or "",
        "chauffage_actuel": lead.chauffage_actuel or "",
        "type_logement": lead.type_logement or "",
        "statut_occupant": lead.statut_occupant or "",
        "facture_electricite": lead.facture_electricite or "",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "register_date": timestamp,
        "api_status": "pending" if can_send else "no_config",
        "api_url": api_url,
        "sent_to_crm": False,
        "retry_count": 0
    }
    
    await db.leads.insert_one(lead_doc)
    
    api_status = "no_config"
    
    if can_send:
        api_status, api_response = await send_lead_to_crm(lead_doc, api_url, api_key)
        
        # Construire le statut détaillé avec plateforme
        status_detail = f"{api_status}"
        if api_status == "success":
            status_detail = f"envoyé/{target_crm.get('slug', 'crm')}"
        elif api_status == "duplicate":
            status_detail = f"doublon/{target_crm.get('slug', 'crm')}"
        
        await db.leads.update_one(
            {"id": lead_doc["id"]},
            {"$set": {
                "api_status": api_status,
                "status_detail": status_detail,
                "api_response": api_response,
                "sent_to_crm": api_status in ["success", "duplicate"],
                "sent_at": datetime.now(timezone.utc).isoformat()
            }}
        )
    
    return {"success": True, "message": "Lead enregistré", "status": api_status, "routing": routing_reason}

# ==================== LEADS MANAGEMENT ====================

@api_router.get("/leads")
async def get_leads(
    crm_id: Optional[str] = None,
    sub_account_id: Optional[str] = None,
    form_code: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 100,
    user: dict = Depends(get_current_user)
):
    query = {}
    
    # Appliquer le filtre par comptes autorisés (sécurité multi-tenant)
    allowed_account_ids = user.get("allowed_accounts", []) if user.get("role") != "admin" and user.get("allowed_accounts") else None
    
    # Filter by CRM - get all form codes belonging to this CRM's sub-accounts
    if crm_id:
        crm_query = {"crm_id": crm_id}
        if allowed_account_ids:
            crm_query["id"] = {"$in": allowed_account_ids}
        sub_accounts = await db.accounts.find(crm_query, {"id": 1}).to_list(100)
        sub_account_ids = [sa["id"] for sa in sub_accounts]
        if sub_account_ids:
            forms = await db.forms.find({"sub_account_id": {"$in": sub_account_ids}}, {"code": 1}).to_list(100)
            form_codes = [f["code"] for f in forms if f.get("code")]
            if form_codes:
                query["form_code"] = {"$in": form_codes}
            else:
                return {"leads": [], "count": 0}
        else:
            return {"leads": [], "count": 0}
    elif allowed_account_ids:
        # Pas de filtre CRM mais l'utilisateur a des restrictions
        forms = await db.forms.find({"sub_account_id": {"$in": allowed_account_ids}}, {"code": 1}).to_list(100)
        form_codes = [f["code"] for f in forms if f.get("code")]
        if form_codes:
            query["form_code"] = {"$in": form_codes}
        else:
            return {"leads": [], "count": 0}
    
    if status:
        query["api_status"] = status
    if form_code:
        query["form_code"] = form_code
    if date_from:
        query["created_at"] = {"$gte": date_from}
    if date_to:
        query.setdefault("created_at", {})["$lte"] = date_to
    
    leads = await db.leads.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return {"leads": leads, "count": len(leads)}

@api_router.post("/leads/retry/{lead_id}")
async def retry_lead(lead_id: str, user: dict = Depends(get_current_user)):
    """Retry sending a single lead to CRM"""
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead non trouvé")
    
    # Vérifier que le lead a un téléphone valide
    if not lead.get("phone"):
        return {"success": False, "error": "Lead sans numéro de téléphone"}
    
    # Get API config
    form_config = await db.forms.find_one({"code": lead.get("form_code")})
    if not form_config:
        return {"success": False, "error": "Configuration formulaire non trouvée"}
    
    # Get account and CRM info
    account_id = form_config.get("account_id") or form_config.get("sub_account_id")
    account = await db.accounts.find_one({"id": account_id}) if account_id else None
    crm = await db.crms.find_one({"id": account.get("crm_id")}) if account else None
    
    api_url = crm.get("api_url") if crm else lead.get("api_url", "")
    api_key = form_config.get("crm_api_key") or form_config.get("api_key") or ""
    
    if not api_url or not api_key:
        return {"success": False, "error": "Configuration API manquante (URL ou clé)"}
    
    # Use the helper function
    api_status, api_response = await send_lead_to_crm(lead, api_url, api_key)
    
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {
            "api_status": api_status, 
            "api_response": api_response, 
            "retried_at": datetime.now(timezone.utc).isoformat(),
            "sent_to_crm": api_status in ["success", "duplicate"],
            "retry_count": lead.get("retry_count", 0) + 1
        }}
    )
    
    return {"success": True, "status": api_status}

@api_router.post("/leads/retry-failed")
async def retry_failed_leads(hours: int = 24, user: dict = Depends(get_current_user)):
    """
    Job nocturne - Retry tous les leads échoués des dernières X heures
    À appeler via cron à 03h00: curl -X POST /api/leads/retry-failed?hours=24
    """
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    # Trouver les leads échoués dans la période
    failed_leads = await db.leads.find({
        "api_status": "failed",
        "sent_to_crm": False,
        "created_at": {"$gte": cutoff_time.isoformat()},
        "phone": {"$exists": True, "$ne": ""}
    }, {"_id": 0}).to_list(1000)
    
    results = {"total": len(failed_leads), "success": 0, "failed": 0, "skipped": 0}
    
    for lead in failed_leads:
        # Get form config
        form_config = await db.forms.find_one({"code": lead.get("form_code")})
        if not form_config:
            results["skipped"] += 1
            continue
        
        # Get account and CRM info
        account_id = form_config.get("account_id") or form_config.get("sub_account_id")
        account = await db.accounts.find_one({"id": account_id}) if account_id else None
        crm = await db.crms.find_one({"id": account.get("crm_id")}) if account else None
        
        api_url = crm.get("api_url") if crm else ""
        api_key = form_config.get("crm_api_key") or form_config.get("api_key") or ""
        
        if not api_url or not api_key:
            results["skipped"] += 1
            continue
        
        # Retry send
        api_status, api_response = await send_lead_to_crm(lead, api_url, api_key)
        
        await db.leads.update_one(
            {"id": lead["id"]},
            {"$set": {
                "api_status": api_status,
                "api_response": api_response,
                "retried_at": datetime.now(timezone.utc).isoformat(),
                "sent_to_crm": api_status in ["success", "duplicate"],
                "retry_count": lead.get("retry_count", 0) + 1
            }}
        )
        
        if api_status in ["success", "duplicate"]:
            results["success"] += 1
        else:
            results["failed"] += 1
    
    await log_activity(user["id"], user["email"], "retry_batch", "leads", "", 
                      f"Retry nocturne: {results['success']} succès, {results['failed']} échecs, {results['skipped']} ignorés")
    
    return {"success": True, "results": results}

@api_router.delete("/leads/{lead_id}")
async def delete_lead(lead_id: str, user: dict = Depends(require_admin)):
    """
    ARCHIVE un lead au lieu de le supprimer.
    Les leads ne sont JAMAIS supprimés définitivement - ils sont conservés pour l'historique.
    """
    # Récupérer le lead
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead non trouvé")
    
    # Archiver au lieu de supprimer
    lead["archived"] = True
    lead["archived_at"] = datetime.now(timezone.utc).isoformat()
    lead["archived_by"] = user["id"]
    
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {"archived": True, "archived_at": lead["archived_at"], "archived_by": user["id"]}}
    )
    
    await log_activity(user["id"], user["email"], "archive", "lead", lead_id, "Lead archivé (conservé dans la base)")
    await log_alert("INFO", "LEAD_ARCHIVED", f"Lead {lead_id} archivé par {user['email']}")
    
    return {"success": True, "message": "Lead archivé (les données sont conservées)"}

class BulkDeleteRequest(BaseModel):
    lead_ids: List[str]

@api_router.post("/leads/bulk-delete")
async def delete_multiple_leads(request: BulkDeleteRequest, user: dict = Depends(require_admin)):
    """
    ARCHIVE plusieurs leads au lieu de les supprimer.
    Les leads ne sont JAMAIS supprimés définitivement.
    """
    if not request.lead_ids:
        raise HTTPException(status_code=400, detail="Aucun lead à archiver")
    
    # Archiver au lieu de supprimer
    result = await db.leads.update_many(
        {"id": {"$in": request.lead_ids}},
        {"$set": {
            "archived": True,
            "archived_at": datetime.now(timezone.utc).isoformat(),
            "archived_by": user["id"]
        }}
    )
    
    await log_activity(user["id"], user["email"], "archive", "leads", ",".join(request.lead_ids[:5]), f"{result.modified_count} leads archivés")
    await log_alert("INFO", "LEADS_BULK_ARCHIVED", f"{result.modified_count} leads archivés par {user['email']}")
    
    return {"success": True, "archived_count": result.modified_count, "message": "Leads archivés (données conservées)"}

# ==================== ARCHIVAGE & FACTURATION ====================

@api_router.post("/leads/archive")
async def archive_old_leads(months: int = 3, user: dict = Depends(require_admin)):
    """
    Archiver les leads de plus de X mois.
    Les leads sont MARQUÉS comme archivés mais restent dans la collection principale.
    """
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=months * 30)
    
    # Trouver les leads à archiver
    old_leads = await db.leads.find({
        "created_at": {"$lt": cutoff_date.isoformat()}
    }).to_list(10000)
    
    if not old_leads:
        return {"success": True, "archived_count": 0, "message": "Aucun lead à archiver"}
    
    # Ajouter la date d'archivage
    for lead in old_leads:
        lead["archived_at"] = datetime.now(timezone.utc).isoformat()
        lead.pop("_id", None)
    
    # Insérer dans leads_archived
    await db.leads_archived.insert_many(old_leads)
    
    # Supprimer de leads
    lead_ids = [lead["id"] for lead in old_leads]
    await db.leads.delete_many({"id": {"$in": lead_ids}})
    
    await log_activity(user["id"], user["email"], "archive", "leads", "", 
                      f"{len(old_leads)} leads archivés (> {months} mois)")
    
    return {
        "success": True, 
        "archived_count": len(old_leads),
        "cutoff_date": cutoff_date.isoformat()
    }

@api_router.get("/leads/archived")
async def get_archived_leads(
    limit: int = 100,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user: dict = Depends(require_admin)
):
    """Récupérer les leads archivés"""
    query = {}
    if date_from:
        query["created_at"] = {"$gte": date_from}
    if date_to:
        query.setdefault("created_at", {})["$lte"] = date_to
    
    leads = await db.leads_archived.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    total = await db.leads_archived.count_documents(query)
    
    return {"leads": leads, "count": len(leads), "total": total}

# Modèle pour marquer une période comme facturée
class BillingPeriodCreate(BaseModel):
    year: int
    month: int  # 1-12
    from_crm_id: str  # CRM qui paie
    to_crm_id: str    # CRM qui reçoit
    amount: float
    lead_count: int
    notes: Optional[str] = ""

@api_router.post("/billing/mark-invoiced")
async def mark_period_invoiced(billing: BillingPeriodCreate, user: dict = Depends(require_admin)):
    """Marquer une période comme facturée entre deux CRMs"""
    # Vérifier si déjà facturé
    existing = await db.billing_history.find_one({
        "year": billing.year,
        "month": billing.month,
        "from_crm_id": billing.from_crm_id,
        "to_crm_id": billing.to_crm_id
    })
    
    if existing:
        # Mettre à jour
        await db.billing_history.update_one(
            {"id": existing["id"]},
            {"$set": {
                "amount": billing.amount,
                "lead_count": billing.lead_count,
                "notes": billing.notes,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "updated_by": user["id"]
            }}
        )
        return {"success": True, "message": "Facturation mise à jour", "id": existing["id"]}
    
    # Créer nouvelle entrée
    billing_doc = {
        "id": str(uuid.uuid4()),
        "year": billing.year,
        "month": billing.month,
        "from_crm_id": billing.from_crm_id,
        "to_crm_id": billing.to_crm_id,
        "amount": billing.amount,
        "lead_count": billing.lead_count,
        "notes": billing.notes,
        "invoiced_at": datetime.now(timezone.utc).isoformat(),
        "invoiced_by": user["id"]
    }
    await db.billing_history.insert_one(billing_doc)
    
    # Récupérer les noms des CRMs pour le log
    from_crm = await db.crms.find_one({"id": billing.from_crm_id})
    to_crm = await db.crms.find_one({"id": billing.to_crm_id})
    
    await log_activity(user["id"], user["email"], "invoice", "billing", billing_doc["id"], 
                      f"Facturé {billing.month}/{billing.year}: {from_crm.get('name', '')} → {to_crm.get('name', '')} = {billing.amount}€")
    
    return {"success": True, "message": "Période marquée comme facturée", "id": billing_doc["id"]}

@api_router.get("/billing/history")
async def get_billing_history(
    year: Optional[int] = None,
    user: dict = Depends(require_admin)
):
    """Récupérer l'historique des facturations"""
    query = {}
    if year:
        query["year"] = year
    
    history = await db.billing_history.find(query, {"_id": 0}).sort([("year", -1), ("month", -1)]).to_list(100)
    
    # Enrichir avec les noms des CRMs
    crms = await db.crms.find({}, {"_id": 0}).to_list(10)
    crm_map = {crm["id"]: crm["name"] for crm in crms}
    
    for item in history:
        item["from_crm_name"] = crm_map.get(item.get("from_crm_id"), "Inconnu")
        item["to_crm_name"] = crm_map.get(item.get("to_crm_id"), "Inconnu")
    
    return {"history": history}

@api_router.delete("/billing/history/{billing_id}")
async def delete_billing_record(billing_id: str, user: dict = Depends(require_admin)):
    """Supprimer un enregistrement de facturation"""
    result = await db.billing_history.delete_one({"id": billing_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Enregistrement non trouvé")
    return {"success": True}

@api_router.get("/billing/dashboard")
async def get_billing_dashboard(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user: dict = Depends(require_admin)
):
    """
    Dashboard de facturation inter-CRM.
    Montre les leads envoyés par chaque CRM, routés vers d'autres CRMs, et les montants.
    """
    # Période par défaut : mois en cours
    now = datetime.now(timezone.utc)
    if not date_from:
        date_from = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    if not date_to:
        date_to = now.isoformat()
    
    date_query = {"created_at": {"$gte": date_from, "$lte": date_to}}
    
    # Récupérer tous les CRMs avec leurs prix
    crms = await db.crms.find({}, {"_id": 0}).to_list(10)
    crm_map = {crm["id"]: crm for crm in crms}
    
    # Stats par CRM
    crm_stats = {}
    for crm in crms:
        crm_stats[crm["id"]] = {
            "crm_name": crm["name"],
            "crm_slug": crm.get("slug", ""),
            "lead_prices": crm.get("lead_prices", {}),
            # Leads originaires de ce CRM (form_code appartient à ce CRM)
            "leads_originated": {"PAC": 0, "PV": 0, "ITE": 0, "total": 0},
            # Leads envoyés vers ce CRM (target_crm_id = ce CRM)
            "leads_received": {"PAC": 0, "PV": 0, "ITE": 0, "total": 0},
            # Leads routés depuis ce CRM vers un autre
            "leads_rerouted_out": {"PAC": 0, "PV": 0, "ITE": 0, "total": 0},
            # Leads routés vers ce CRM depuis un autre
            "leads_rerouted_in": {"PAC": 0, "PV": 0, "ITE": 0, "total": 0},
            # Montants
            "amount_to_invoice": 0.0,  # Ce que ce CRM doit facturer aux autres
            "amount_to_pay": 0.0,      # Ce que ce CRM doit payer aux autres
        }
    
    # Récupérer tous les leads de la période avec succès
    leads = await db.leads.find({
        **date_query,
        "api_status": {"$in": ["success", "duplicate"]},
        "sent_to_crm": True
    }, {"_id": 0}).to_list(100000)
    
    # Calculer les stats
    for lead in leads:
        origin_crm_id = lead.get("origin_crm_id", "")
        target_crm_id = lead.get("target_crm_id", "")
        product_type = lead.get("product_type", "PV")
        routing_reason = lead.get("routing_reason", "direct_to_origin")
        
        # Normaliser le type de produit
        if product_type not in ["PAC", "PV", "ITE"]:
            product_type = "PV"
        
        # Leads originaires
        if origin_crm_id and origin_crm_id in crm_stats:
            crm_stats[origin_crm_id]["leads_originated"][product_type] += 1
            crm_stats[origin_crm_id]["leads_originated"]["total"] += 1
        
        # Leads reçus (envoyés vers le CRM cible)
        if target_crm_id and target_crm_id in crm_stats:
            crm_stats[target_crm_id]["leads_received"][product_type] += 1
            crm_stats[target_crm_id]["leads_received"]["total"] += 1
        
        # Routage inter-CRM
        if "rerouted_to" in routing_reason and origin_crm_id != target_crm_id:
            # Lead routé depuis origin vers target
            if origin_crm_id in crm_stats:
                crm_stats[origin_crm_id]["leads_rerouted_out"][product_type] += 1
                crm_stats[origin_crm_id]["leads_rerouted_out"]["total"] += 1
            
            if target_crm_id in crm_stats:
                crm_stats[target_crm_id]["leads_rerouted_in"][product_type] += 1
                crm_stats[target_crm_id]["leads_rerouted_in"]["total"] += 1
                
                # Calcul du montant à facturer
                target_prices = crm_stats[target_crm_id]["lead_prices"]
                price = target_prices.get(product_type, 0)
                
                # Le CRM cible facture au CRM origine
                crm_stats[target_crm_id]["amount_to_invoice"] += price
                if origin_crm_id in crm_stats:
                    crm_stats[origin_crm_id]["amount_to_pay"] += price
    
    # Calculer le solde net et le résumé de facturation
    billing_summary = []
    for crm_id, stats in crm_stats.items():
        net_balance = stats["amount_to_invoice"] - stats["amount_to_pay"]
        billing_summary.append({
            "crm_id": crm_id,
            "crm_name": stats["crm_name"],
            "crm_slug": stats["crm_slug"],
            "leads_originated": stats["leads_originated"],
            "leads_received": stats["leads_received"],
            "leads_rerouted_out": stats["leads_rerouted_out"],
            "leads_rerouted_in": stats["leads_rerouted_in"],
            "amount_to_invoice": round(stats["amount_to_invoice"], 2),
            "amount_to_pay": round(stats["amount_to_pay"], 2),
            "net_balance": round(net_balance, 2),
            "lead_prices": stats["lead_prices"]
        })
    
    # Détails des transferts inter-CRM
    transfers = []
    for crm_from in crms:
        for crm_to in crms:
            if crm_from["id"] != crm_to["id"]:
                # Compter les leads routés de crm_from vers crm_to
                transfer_leads = [l for l in leads 
                                 if l.get("origin_crm_id") == crm_from["id"] 
                                 and l.get("target_crm_id") == crm_to["id"]
                                 and "rerouted" in l.get("routing_reason", "")]
                
                if transfer_leads:
                    by_product = {"PAC": 0, "PV": 0, "ITE": 0}
                    amount = 0
                    for lead in transfer_leads:
                        pt = lead.get("product_type", "PV")
                        if pt in by_product:
                            by_product[pt] += 1
                        price = crm_to.get("lead_prices", {}).get(pt, 0)
                        amount += price
                    
                    transfers.append({
                        "from_crm": crm_from["name"],
                        "from_crm_id": crm_from["id"],
                        "to_crm": crm_to["name"],
                        "to_crm_id": crm_to["id"],
                        "count": len(transfer_leads),
                        "by_product": by_product,
                        "amount": round(amount, 2)
                    })
    
    return {
        "period": {"from": date_from, "to": date_to},
        "total_leads": len(leads),
        "crm_stats": billing_summary,
        "transfers": transfers
    }

# ==================== ANALYTICS ====================

@api_router.get("/analytics/stats")
async def get_analytics_stats(
    crm_id: Optional[str] = None,
    sub_account_id: Optional[str] = None,
    period: str = "today",  # today, week, month, custom
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    # Calculate date range based on period (French timezone)
    now = datetime.now(timezone.utc) + timedelta(hours=1)  # UTC+1 for France
    
    if period == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_date = now - timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "month":
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "custom" and date_from:
        start_date = datetime.fromisoformat(date_from)
    else:
        start_date = now - timedelta(days=30)
    
    end_date = datetime.fromisoformat(date_to) if date_to else now
    
    base_query = {"created_at": {"$gte": start_date.isoformat(), "$lte": end_date.isoformat()}}
    
    # Build CRM-specific filter for leads
    lead_query = {**base_query}
    lp_codes_filter = None
    form_codes_filter = None
    
    if crm_id:
        sub_accounts = await db.accounts.find({"crm_id": crm_id}, {"id": 1}).to_list(100)
        sub_account_ids = [sa["id"] for sa in sub_accounts]
        
        if sub_account_ids:
            # Get LP codes for CTA clicks filtering
            lps = await db.lps.find({"sub_account_id": {"$in": sub_account_ids}}, {"code": 1}).to_list(100)
            lp_codes_filter = [lp["code"] for lp in lps if lp.get("code")]
            
            # Get form codes for leads filtering  
            forms = await db.forms.find({"sub_account_id": {"$in": sub_account_ids}}, {"code": 1}).to_list(100)
            form_codes_filter = [f["code"] for f in forms if f.get("code")]
            
            if form_codes_filter:
                lead_query["form_code"] = {"$in": form_codes_filter}
            else:
                lead_query["form_code"] = {"$in": []}  # No forms = no leads
    
    # Build queries with CRM filter
    cta_query = {**base_query}
    if lp_codes_filter is not None:
        cta_query["lp_code"] = {"$in": lp_codes_filter} if lp_codes_filter else {"$in": []}
    
    form_start_query = {**base_query}
    if form_codes_filter is not None:
        form_start_query["form_code"] = {"$in": form_codes_filter} if form_codes_filter else {"$in": []}
    
    stats = {
        "period": period,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "cta_clicks": await db.cta_clicks.count_documents(cta_query),
        "forms_started": await db.form_starts.count_documents(form_start_query),
        "leads_total": await db.leads.count_documents(lead_query),
        "leads_success": await db.leads.count_documents({**lead_query, "api_status": "success"}),
        "leads_failed": await db.leads.count_documents({**lead_query, "api_status": "failed"}),
        "leads_duplicate": await db.leads.count_documents({**lead_query, "api_status": "duplicate"})
    }
    
    # Calculate conversion rates
    if stats["cta_clicks"] > 0:
        stats["cta_to_form_rate"] = round(stats["forms_started"] / stats["cta_clicks"] * 100, 1)
    else:
        stats["cta_to_form_rate"] = 0
    
    if stats["forms_started"] > 0:
        stats["form_to_lead_rate"] = round(stats["leads_total"] / stats["forms_started"] * 100, 1)
    else:
        stats["form_to_lead_rate"] = 0
    
    return stats

@api_router.get("/analytics/winners")
async def get_winners(
    crm_id: Optional[str] = None,
    period: str = "week",
    user: dict = Depends(get_current_user)
):
    """Get best and worst performing LPs and Forms"""
    now = datetime.now(timezone.utc) + timedelta(hours=1)
    
    if period == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_date = now - timedelta(days=7)
    else:
        start_date = now - timedelta(days=30)
    
    query = {"created_at": {"$gte": start_date.isoformat()}}
    
    # Filter by CRM if specified
    if crm_id:
        sub_accounts = await db.accounts.find({"crm_id": crm_id}, {"id": 1}).to_list(100)
        sub_account_ids = [sa["id"] for sa in sub_accounts]
        
        if sub_account_ids:
            forms = await db.forms.find({"sub_account_id": {"$in": sub_account_ids}}, {"code": 1}).to_list(100)
            form_codes = [f["code"] for f in forms if f.get("code")]
            if form_codes:
                query["form_code"] = {"$in": form_codes}
            else:
                return {"period": period, "lp_winners": [], "lp_losers": [], "form_winners": [], "form_losers": []}
        else:
            return {"period": period, "lp_winners": [], "lp_losers": [], "form_winners": [], "form_losers": []}
    
    # Get LP performance
    lp_pipeline = [
        {"$match": query},
        {"$group": {
            "_id": "$lp_code",
            "leads": {"$sum": 1},
            "success": {"$sum": {"$cond": [{"$eq": ["$api_status", "success"]}, 1, 0]}}
        }},
        {"$sort": {"leads": -1}},
        {"$limit": 10}
    ]
    lp_stats = await db.leads.aggregate(lp_pipeline).to_list(10)
    
    # Get Form performance
    form_pipeline = [
        {"$match": query},
        {"$group": {
            "_id": "$form_code",
            "leads": {"$sum": 1},
            "success": {"$sum": {"$cond": [{"$eq": ["$api_status", "success"]}, 1, 0]}}
        }},
        {"$sort": {"leads": -1}},
        {"$limit": 10}
    ]
    form_stats = await db.leads.aggregate(form_pipeline).to_list(10)
    
    # Calculate winners and losers
    lp_winners = [{"code": s["_id"], "leads": s["leads"], "success_rate": round(s["success"]/s["leads"]*100, 1) if s["leads"] > 0 else 0} for s in lp_stats if s["_id"]]
    form_winners = [{"code": s["_id"], "leads": s["leads"], "success_rate": round(s["success"]/s["leads"]*100, 1) if s["leads"] > 0 else 0} for s in form_stats if s["_id"]]
    
    return {
        "period": period,
        "lp_winners": sorted(lp_winners, key=lambda x: x["leads"], reverse=True)[:5],
        "lp_losers": sorted(lp_winners, key=lambda x: x["leads"])[:5] if len(lp_winners) > 5 else [],
        "form_winners": sorted(form_winners, key=lambda x: x["leads"], reverse=True)[:5],
        "form_losers": sorted(form_winners, key=lambda x: x["leads"])[:5] if len(form_winners) > 5 else []
    }

@api_router.get("/analytics/compare")
async def get_comparison_stats(
    crm_ids: Optional[str] = None,  # Comma-separated CRM IDs or "all"
    diffusion_category: Optional[str] = None,  # native, google, facebook, tiktok, all
    period: str = "week",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """
    Dashboard comparatif global - Compare stats par type de diffusion et CRM
    Permet de voir les performances en temps réel par source
    """
    now = datetime.now(timezone.utc) + timedelta(hours=1)
    
    # Calculate date range
    if period == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now - timedelta(days=30)
    elif period == "custom" and date_from:
        start_date = datetime.fromisoformat(date_from)
    else:
        start_date = now - timedelta(days=7)
    
    end_date = datetime.fromisoformat(date_to) if date_to else now
    base_query = {"created_at": {"$gte": start_date.isoformat(), "$lte": end_date.isoformat()}}
    
    # Get CRM filter
    crm_filter = []
    if crm_ids and crm_ids != "all":
        crm_filter = crm_ids.split(",")
    
    # Get all forms with their source info
    form_query = {}
    if crm_filter:
        sub_accounts = await db.accounts.find({"crm_id": {"$in": crm_filter}}, {"id": 1}).to_list(100)
        sub_account_ids = [sa["id"] for sa in sub_accounts]
        form_query["sub_account_id"] = {"$in": sub_account_ids}
    
    all_forms = await db.forms.find(form_query, {"_id": 0}).to_list(500)
    
    # Filter by diffusion category if specified
    if diffusion_category and diffusion_category != "all":
        # Get diffusion sources in this category
        sources = await db.diffusion_sources.find({"category": diffusion_category}, {"name": 1}).to_list(50)
        source_names = [s["name"].lower() for s in sources]
        all_forms = [f for f in all_forms if f.get("source_name", "").lower() in source_names or f.get("source_type") == diffusion_category]
    
    # Group forms by source type/category
    form_codes_by_source = {}
    for form in all_forms:
        source_type = form.get("source_type", "other")
        if source_type not in form_codes_by_source:
            form_codes_by_source[source_type] = []
        if form.get("code"):
            form_codes_by_source[source_type].append(form["code"])
    
    # Calculate stats per source
    stats_by_source = {}
    for source_type, form_codes in form_codes_by_source.items():
        if not form_codes:
            continue
        
        lead_query = {**base_query, "form_code": {"$in": form_codes}}
        form_start_query = {**base_query, "form_code": {"$in": form_codes}}
        
        leads_total = await db.leads.count_documents(lead_query)
        leads_success = await db.leads.count_documents({**lead_query, "api_status": "success"})
        forms_started = await db.form_starts.count_documents(form_start_query)
        
        # Calculate conversion rate (started → completed)
        conversion_rate = round(leads_total / forms_started * 100, 1) if forms_started > 0 else 0
        
        stats_by_source[source_type] = {
            "source_type": source_type,
            "forms_count": len(form_codes),
            "forms_started": forms_started,
            "leads_total": leads_total,
            "leads_success": leads_success,
            "conversion_rate": conversion_rate,  # % démarrés → finis
            "success_rate": round(leads_success / leads_total * 100, 1) if leads_total > 0 else 0
        }
    
    # Get totals
    all_form_codes = [f["code"] for f in all_forms if f.get("code")]
    total_query = {**base_query}
    if all_form_codes:
        total_query["form_code"] = {"$in": all_form_codes}
    
    total_stats = {
        "forms_started": await db.form_starts.count_documents({**base_query, "form_code": {"$in": all_form_codes}} if all_form_codes else base_query),
        "leads_total": await db.leads.count_documents(total_query if all_form_codes else base_query),
        "leads_success": await db.leads.count_documents({**total_query, "api_status": "success"} if all_form_codes else {**base_query, "api_status": "success"}),
        "cta_clicks": await db.cta_clicks.count_documents(base_query)
    }
    total_stats["conversion_rate"] = round(total_stats["leads_total"] / total_stats["forms_started"] * 100, 1) if total_stats["forms_started"] > 0 else 0
    
    # Get CRM breakdown if multiple CRMs selected
    crm_breakdown = {}
    crms = await db.crms.find({}, {"_id": 0}).to_list(10)
    for crm in crms:
        if crm_filter and crm["id"] not in crm_filter:
            continue
        
        crm_sub_accounts = await db.accounts.find({"crm_id": crm["id"]}, {"id": 1}).to_list(50)
        crm_sub_ids = [sa["id"] for sa in crm_sub_accounts]
        crm_forms = [f for f in all_forms if f.get("sub_account_id") in crm_sub_ids]
        crm_form_codes = [f["code"] for f in crm_forms if f.get("code")]
        
        if crm_form_codes:
            crm_lead_query = {**base_query, "form_code": {"$in": crm_form_codes}}
            crm_leads = await db.leads.count_documents(crm_lead_query)
            crm_success = await db.leads.count_documents({**crm_lead_query, "api_status": "success"})
            crm_started = await db.form_starts.count_documents({**base_query, "form_code": {"$in": crm_form_codes}})
            
            crm_breakdown[crm["slug"]] = {
                "name": crm["name"],
                "forms_count": len(crm_form_codes),
                "forms_started": crm_started,
                "leads_total": crm_leads,
                "leads_success": crm_success,
                "conversion_rate": round(crm_leads / crm_started * 100, 1) if crm_started > 0 else 0
            }
    
    return {
        "period": period,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "filters": {
            "crm_ids": crm_ids,
            "diffusion_category": diffusion_category
        },
        "totals": total_stats,
        "by_source": stats_by_source,
        "by_crm": crm_breakdown
    }

# ==================== COMMENTS ====================

@api_router.get("/comments")
async def get_comments(entity_type: str, entity_id: str, user: dict = Depends(get_current_user)):
    comments = await db.comments.find(
        {"entity_type": entity_type, "entity_id": entity_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return {"comments": comments}

@api_router.post("/comments")
async def create_comment(comment: CommentCreate, user: dict = Depends(get_current_user)):
    comment_doc = {
        "id": str(uuid.uuid4()),
        **comment.model_dump(),
        "user_id": user["id"],
        "user_name": user["nom"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.comments.insert_one(comment_doc)
    await log_activity(user["id"], user["email"], "comment", comment.entity_type, comment.entity_id, "Commentaire ajouté")
    return {"success": True, "comment": {k: v for k, v in comment_doc.items() if k != "_id"}}

# ==================== ACTIVITY LOG ====================

@api_router.get("/activity-logs")
async def get_activity_logs(limit: int = 100, user: dict = Depends(require_admin)):
    logs = await db.activity_logs.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return {"logs": logs}

# ==================== SCRIPT GENERATOR ====================

class BriefSelectionLP(BaseModel):
    lp_id: str
    # Infos dynamiques (saisies au moment de générer)
    cta_selector: Optional[str] = ""  # .cta-btn
    # Éléments à inclure du compte
    include_logo_main: bool = False
    include_logo_secondary: bool = False
    include_logo_small: bool = False
    include_favicon: bool = False
    include_images: List[str] = []  # Liste des noms d'images à inclure
    include_gtm_pixel: bool = False
    include_gtm_conversion: bool = False
    include_gtm_cta: bool = False
    include_privacy_policy: bool = False
    include_legal_mentions: bool = False
    include_colors: bool = False
    include_redirect_url: Optional[str] = None  # Nom de l'URL de redirection
    include_notes: bool = False
    include_html_code: bool = False  # Inclure le code HTML de la LP

class BriefSelectionForm(BaseModel):
    form_id: str
    # Infos dynamiques (saisies au moment de générer)
    crm_api_key: Optional[str] = ""  # Clé API CRM destination (ZR7/MDL)
    # Éléments à inclure du compte
    include_logo_main: bool = False
    include_logo_secondary: bool = False
    include_images: List[str] = []  # Liste des noms d'images à inclure
    include_gtm_pixel: bool = False
    include_gtm_conversion: bool = False
    include_privacy_policy: bool = False
    include_redirect_url: Optional[str] = None
    include_notes: bool = False
    include_html_code: bool = False  # Inclure le code HTML du form

@api_router.post("/generate-brief/lp")
async def generate_lp_brief(selection: BriefSelectionLP, user: dict = Depends(get_current_user)):
    """Generate LP brief based on selected elements"""
    lp = await db.lps.find_one({"id": selection.lp_id}, {"_id": 0})
    if not lp:
        raise HTTPException(status_code=404, detail="LP non trouvée")
    
    account_id = lp.get("account_id") or lp.get("sub_account_id")
    account = await db.accounts.find_one({"id": account_id}, {"_id": 0}) if account_id else None
    
    # Build brief based on selection
    lines = [f"=== BRIEF LP : {lp.get('code', '')} ===", ""]
    lines.append(f"Nom : {lp.get('name', '')}")
    lines.append(f"URL : {lp.get('url', '')}")
    lines.append(f"Compte : {account.get('name', '') if account else 'Non défini'}")
    lines.append(f"Source : {lp.get('source_name', '')} ({lp.get('source_type', '')})")
    lines.append(f"Type : {'Formulaire intégré' if lp.get('lp_type') == 'integrated' else 'Redirection'}")
    if lp.get('form_url'):
        lines.append(f"URL Formulaire : {lp.get('form_url')}")
    lines.append("")
    
    # Infos dynamiques saisies au moment de générer
    if selection.cta_selector:
        lines.append(f"Sélecteur CTA : {selection.cta_selector}")
        lines.append("")
    
    if selection.include_logo_main and account:
        lines.append(f"Logo principal : {account.get('logo_main_url', 'Non défini')}")
    if selection.include_logo_secondary and account:
        lines.append(f"Logo secondaire : {account.get('logo_secondary_url', 'Non défini')}")
    if selection.include_logo_small and account:
        lines.append(f"Petit logo : {account.get('logo_small_url', 'Non défini')}")
    if selection.include_favicon and account:
        lines.append(f"Favicon : {account.get('favicon_url', 'Non défini')}")
    
    if selection.include_gtm_pixel and account:
        lines.append("")
        lines.append("--- PIXEL GTM (header) ---")
        lines.append(account.get('gtm_pixel_header', 'Non configuré'))
    
    if selection.include_gtm_conversion and account:
        lines.append("")
        lines.append("--- CODE CONVERSION GTM ---")
        lines.append(account.get('gtm_conversion_code', 'Non configuré'))
    
    if selection.include_gtm_cta and account:
        lines.append("")
        lines.append("--- CODE CTA GTM ---")
        lines.append(account.get('gtm_cta_code', 'Non configuré'))
    
    if selection.include_redirect_url and account:
        lines.append("")
        lines.append(f"--- URL REDIRECTION ({selection.include_redirect_url}) ---")
        named_urls = account.get('named_redirect_urls', [])
        found_url = next((u.get('url', '') for u in named_urls if u.get('name') == selection.include_redirect_url), None)
        if found_url:
            lines.append(found_url)
        else:
            lines.append(account.get('default_redirect_url', 'Non configuré'))
    
    if selection.include_privacy_policy and account:
        lines.append("")
        lines.append("--- POLITIQUE CONFIDENTIALITÉ ---")
        lines.append(account.get('privacy_policy_text', 'Non configuré'))
    
    if selection.include_legal_mentions and account:
        lines.append("")
        lines.append("--- MENTIONS LÉGALES ---")
        lines.append(account.get('legal_mentions_text', 'Non configuré'))
    
    if selection.include_colors and account:
        lines.append("")
        lines.append(f"Couleur principale : {account.get('primary_color', '#3B82F6')}")
        lines.append(f"Couleur secondaire : {account.get('secondary_color', '#1E40AF')}")
    
    if selection.include_notes:
        lines.append("")
        lines.append("--- NOTES ---")
        lines.append(lp.get('notes', '') or (account.get('notes', '') if account else ''))
    
    if selection.include_html_code and lp.get('html_code'):
        lines.append("")
        lines.append("--- CODE HTML DE LA LP ---")
        lines.append(lp.get('html_code', ''))
    
    return {"brief": "\n".join(lines), "lp": lp, "account": account}

@api_router.post("/generate-brief/form")
async def generate_form_brief(selection: BriefSelectionForm, user: dict = Depends(get_current_user)):
    """Generate Form brief based on selected elements"""
    form = await db.forms.find_one({"id": selection.form_id}, {"_id": 0})
    if not form:
        raise HTTPException(status_code=404, detail="Formulaire non trouvé")
    
    account_id = form.get("account_id") or form.get("sub_account_id")
    account = await db.accounts.find_one({"id": account_id}, {"_id": 0}) if account_id else None
    crm = await db.crms.find_one({"id": account.get("crm_id")}) if account else None
    
    # Count leads for this form
    lead_count = await db.leads.count_documents({"form_code": form.get('code')})
    
    # Build brief based on selection
    lines = [f"=== BRIEF FORMULAIRE : {form.get('code', '')} ===", ""]
    lines.append(f"Nom : {form.get('name', '')}")
    lines.append(f"URL : {form.get('url', '')}")
    lines.append(f"Compte : {account.get('name', '') if account else 'Non défini'}")
    lines.append(f"CRM destination : {crm.get('name', 'Non défini') if crm else 'Non défini'}")
    lines.append(f"Source : {form.get('source_name', '')} ({form.get('source_type', '')})")
    lines.append(f"Type produit : {form.get('product_type', 'panneaux')}")
    lines.append(f"Type : {'Intégré dans LP' if form.get('form_type') == 'integrated' else 'Page séparée'}")
    lines.append(f"Tracking : {form.get('tracking_type', 'redirect')}")
    lines.append(f"Nombre de leads : {lead_count}")
    
    # === SECTION VALIDATIONS OBLIGATOIRES ===
    lines.append("")
    lines.append("=" * 60)
    lines.append("=== ⚠️ VALIDATIONS OBLIGATOIRES (BLOQUANTES) ===")
    lines.append("=" * 60)
    lines.append("")
    lines.append("Le formulaire DOIT bloquer l'envoi si ces conditions ne sont pas remplies :")
    lines.append("")
    lines.append("1️⃣ TÉLÉPHONE (obligatoire)")
    lines.append("   - Champ requis, ne peut pas être vide")
    lines.append("   - Bloquer l'étape suivante si non rempli")
    lines.append("")
    lines.append("2️⃣ NOM (obligatoire)")
    lines.append("   - Champ requis, minimum 2 caractères")
    lines.append("   - Bloquer l'étape suivante si non rempli")
    lines.append("")
    lines.append("3️⃣ DÉPARTEMENT (France métropolitaine uniquement)")
    lines.append("   - Valeurs autorisées : 01 à 95")
    lines.append("   - CORSE NON ACCEPTÉE (2A, 2B)")
    lines.append("   - DOM-TOM NON ACCEPTÉS (971, 972, 973, 974, 976)")
    lines.append("   - Bloquer l'étape suivante si département invalide")
    lines.append("")
    lines.append("📋 CODE VALIDATION JAVASCRIPT :")
    lines.append("```javascript")
    lines.append("// Validation téléphone")
    lines.append("function validatePhone(phone) {")
    lines.append("  return phone && phone.trim().length > 0;")
    lines.append("}")
    lines.append("")
    lines.append("// Validation nom")
    lines.append("function validateNom(nom) {")
    lines.append("  return nom && nom.trim().length >= 2;")
    lines.append("}")
    lines.append("")
    lines.append("// Validation département France métropolitaine (01-95 uniquement)")
    lines.append("function validateDepartement(dept) {")
    lines.append("  if (!dept) return false;")
    lines.append("  const d = dept.toString().trim();")
    lines.append("  const num = parseInt(d, 10);")
    lines.append("  return num >= 1 && num <= 95;")
    lines.append("}")
    lines.append("")
    lines.append("// Exemple d'utilisation - BLOQUE si invalide")
    lines.append("function canProceedToNextStep() {")
    lines.append("  const phone = document.getElementById('phone').value;")
    lines.append("  const nom = document.getElementById('nom').value;")
    lines.append("  const dept = document.getElementById('departement').value;")
    lines.append("  ")
    lines.append("  if (!validatePhone(phone)) {")
    lines.append("    alert('Veuillez saisir votre numéro de téléphone');")
    lines.append("    return false;")
    lines.append("  }")
    lines.append("  if (!validateNom(nom)) {")
    lines.append("    alert('Veuillez saisir votre nom (minimum 2 caractères)');")
    lines.append("    return false;")
    lines.append("  }")
    lines.append("  if (!validateDepartement(dept)) {")
    lines.append("    alert('Département invalide. France métropolitaine uniquement (01-95)');")
    lines.append("    return false;")
    lines.append("  }")
    lines.append("  return true;")
    lines.append("}")
    lines.append("```")
    lines.append("")
    lines.append("=" * 60)
    
    # === SECTION API CE CRM (TOUJOURS AFFICHÉE) ===
    lines.append("")
    lines.append("=" * 60)
    lines.append("=== INTÉGRATION API - CE CRM ===")
    lines.append("=" * 60)
    lines.append("")
    lines.append("Pour envoyer les leads depuis votre formulaire HTML vers ce CRM :")
    lines.append("")
    lines.append("🔑 CLÉ API : [MASQUÉE - Voir page Formulaires]")
    lines.append(f"📝 CODE FORMULAIRE : {form.get('code', '')}")
    lines.append(f"📍 ENDPOINT : POST https://rdz-group-ltd.online/api/submit-lead")
    lines.append("")
    lines.append("⚠️ SÉCURITÉ : La clé API n'est PAS affichée ici pour des raisons de sécurité.")
    lines.append("   → Allez dans 'Formulaires' et cliquez sur l'icône 🔑 pour copier la clé.")
    lines.append("   → NE PARTAGEZ JAMAIS cette clé publiquement.")
    lines.append("")
    lines.append("📋 HEADERS :")
    lines.append("   Content-Type: application/json")
    lines.append("")
    lines.append("📋 BODY (JSON) :")
    lines.append("{")
    lines.append('  "api_key": "[VOTRE_CLÉ_API]",    // ⚠️ OBLIGATOIRE - Copiez depuis page Formulaires')
    lines.append(f'  "form_code": "{form.get("code", "")}",')
    lines.append('  "phone": "0612345678",        // ⚠️ OBLIGATOIRE')
    lines.append('  "nom": "Dupont",              // ⚠️ OBLIGATOIRE (min 2 car.)')
    lines.append('  "departement": "75",          // ⚠️ OBLIGATOIRE (France métro)')
    lines.append('  "prenom": "Jean",             // optionnel')
    lines.append('  "civilite": "M.",             // optionnel (M., Mme)')
    lines.append('  "email": "email@example.com", // optionnel')
    lines.append('  "code_postal": "75001",       // optionnel')
    lines.append('  "superficie_logement": "120", // optionnel')
    lines.append('  "chauffage_actuel": "Gaz",    // optionnel')
    lines.append('  "type_logement": "Maison",    // optionnel')
    lines.append('  "statut_occupant": "Propriétaire", // optionnel')
    lines.append('  "facture_electricite": "150"  // optionnel')
    lines.append("}")
    lines.append("")
    lines.append("📋 EXEMPLE COMPLET AVEC VALIDATION :")
    lines.append("```javascript")
    lines.append("// Configuration - REMPLACEZ [VOTRE_CLÉ_API] par votre vraie clé (page Formulaires)")
    lines.append("const API_KEY = '[VOTRE_CLÉ_API]';  // ⚠️ À récupérer dans Formulaires > icône 🔑")
    lines.append(f"const FORM_CODE = '{form.get('code', '')}';")
    lines.append("const ENDPOINT = 'https://rdz-group-ltd.online/api/submit-lead';")
    lines.append("")
    lines.append("document.getElementById('form').addEventListener('submit', function(e) {")
    lines.append("  e.preventDefault();")
    lines.append("  ")
    lines.append("  // Vérifier les validations obligatoires")
    lines.append("  if (!canProceedToNextStep()) return;")
    lines.append("  ")
    lines.append("  // Envoi vers le CRM")
    lines.append("  fetch(ENDPOINT, {")
    lines.append("    method: 'POST',")
    lines.append("    headers: { 'Content-Type': 'application/json' },")
    lines.append("    body: JSON.stringify({")
    lines.append("      api_key: API_KEY,              // ⚠️ OBLIGATOIRE")
    lines.append("      form_code: FORM_CODE,")
    lines.append("      phone: document.getElementById('phone').value,")
    lines.append("      nom: document.getElementById('nom').value,")
    lines.append("      departement: document.getElementById('departement').value,")
    lines.append("      email: document.getElementById('email').value || ''")
    lines.append("    })")
    lines.append("  })")
    lines.append("  .then(res => res.json())")
    lines.append("  .then(data => {")
    lines.append("    if (data.success) {")
    lines.append("      window.location.href = '/merci';")
    lines.append("    } else {")
    lines.append("      console.error('Erreur:', data.detail);")
    lines.append("      alert('Erreur: ' + (data.detail || 'Problème lors de l\\'envoi'));")
    lines.append("    }")
    lines.append("  })")
    lines.append("  .catch(err => {")
    lines.append("    console.error('Erreur réseau:', err);")
    lines.append("    alert('Erreur de connexion');")
    lines.append("  });")
    lines.append("});")
    lines.append("```")
    lines.append("")
    lines.append("=" * 60)
    
    # Clé API CRM destination (ZR7/MDL) - saisie dynamiquement
    if selection.crm_api_key:
        lines.append("")
        lines.append("=== CLÉ API CRM DESTINATION (ZR7/MDL) ===")
        lines.append(f"Clé : {selection.crm_api_key}")
        if crm:
            lines.append(f"URL API : {crm.get('api_url', 'Non configurée')}")
    
    # Champs du formulaire
    lines.append("")
    lines.append("=== CHAMPS DU FORMULAIRE ===")
    lines.append("⚠️ OBLIGATOIRES (bloquants) :")
    lines.append("   - Téléphone")
    lines.append("   - Nom (min 2 caractères)")
    lines.append("   - Département (France métropolitaine : 01-95, 2A, 2B)")
    lines.append("")
    lines.append("📋 OPTIONNELS :")
    lines.append("   prenom, civilite, email, code_postal, superficie_logement,")
    lines.append("   chauffage_actuel, type_logement, statut_occupant, facture_electricite")
    
    # Logos
    if selection.include_logo_main and account:
        lines.append("")
        lines.append(f"Logo principal : {account.get('logo_main_url', 'Non défini')}")
    if selection.include_logo_secondary and account:
        lines.append(f"Logo secondaire : {account.get('logo_secondary_url', 'Non défini')}")
    
    # Images du compte
    if selection.include_images and account:
        account_images = account.get('images', [])
        for img_name in selection.include_images:
            img = next((i for i in account_images if i.get('name') == img_name), None)
            if img:
                lines.append(f"Image '{img_name}' : {img.get('url', 'Non défini')}")
    
    if selection.include_gtm_pixel and account:
        lines.append("")
        lines.append("--- PIXEL GTM (header) ---")
        lines.append(account.get('gtm_pixel_header', 'Non configuré'))
    
    if selection.include_gtm_conversion and account:
        lines.append("")
        lines.append("--- CODE CONVERSION GTM ---")
        lines.append(account.get('gtm_conversion_code', 'Non configuré'))
    
    if selection.include_redirect_url and account:
        lines.append("")
        lines.append(f"--- URL REDIRECTION ({selection.include_redirect_url}) ---")
        named_urls = account.get('named_redirect_urls', [])
        found_url = next((u.get('url', '') for u in named_urls if u.get('name') == selection.include_redirect_url), None)
        if found_url:
            lines.append(found_url)
        else:
            lines.append(account.get('default_redirect_url', 'Non configuré'))
    
    if selection.include_privacy_policy and account:
        lines.append("")
        lines.append("--- POLITIQUE CONFIDENTIALITÉ ---")
        lines.append(account.get('privacy_policy_text', 'Non configuré'))
    
    if selection.include_notes:
        lines.append("")
        lines.append("--- NOTES ---")
        lines.append(form.get('notes', '') or (account.get('notes', '') if account else ''))
    
    if selection.include_html_code and form.get('html_code'):
        lines.append("")
        lines.append("--- CODE HTML DU FORMULAIRE ---")
        lines.append(form.get('html_code', ''))
    
    return {"brief": "\n".join(lines), "form": form, "account": account}

@api_router.get("/generate-script/lp/{lp_id}")
async def generate_lp_script(lp_id: str, user: dict = Depends(get_current_user)):
    """Generate configuration brief for LP - text format for Emergent"""
    lp = await db.lps.find_one({"id": lp_id}, {"_id": 0})
    if not lp:
        raise HTTPException(status_code=404, detail="LP non trouvée")
    
    # Get account (try both field names for compatibility)
    account_id = lp.get("account_id") or lp.get("sub_account_id")
    account = await db.accounts.find_one({"id": account_id}, {"_id": 0}) if account_id else None
    
    # Build text brief
    brief = f"""=== BRIEF LP : {lp.get('code', 'Non défini')} ===

NOM : {lp.get('name', 'Non défini')}
TYPE : {lp.get('lp_type', 'redirect')} {'(formulaire intégré dans la LP)' if lp.get('lp_type') == 'integrated' else '(redirection vers formulaire externe)'}
SOURCE : {lp.get('source_name', 'Non défini')} ({lp.get('source_type', 'native')})

--- COMPTE ---
Nom du compte : {account.get('name', 'Non défini') if account else 'Non défini'}
Domaine : {account.get('domain', 'Non défini') if account else 'Non défini'}

--- LOGOS ---
Logo principal (gauche) : {account.get('logo_left_url', 'Non défini') if account else 'Non défini'}
Logo secondaire (droite) : {account.get('logo_right_url', 'Non défini') if account else 'Non défini'}
Petit logo (favicon) : {account.get('logo_small_url', 'Non défini') if account else 'Non défini'}

--- TRACKING GTM ---
Pixel Header (dans <head>) : 
{account.get('gtm_head', 'Non configuré') if account else 'Non configuré'}

Code GTM Body :
{account.get('gtm_body', 'Non configuré') if account else 'Non configuré'}

--- CTA ---
Sélecteur CSS des boutons CTA : {lp.get('cta_selector', '.cta-btn')}
URL de redirection CTA : {lp.get('form_url', 'Non défini')}

--- LÉGAL ---
Politique de confidentialité : {account.get('privacy_policy_url', 'Non défini') if account else 'Non défini'}
Mentions légales : {account.get('legal_mentions_url', 'Non défini') if account else 'Non défini'}
Texte popup légal : {account.get('legal_popup_text', 'Non défini') if account else 'Non défini'}

--- COULEURS ---
Couleur principale : {account.get('primary_color', '#2563eb') if account else '#2563eb'}
Couleur secondaire : {account.get('secondary_color', '#1e40af') if account else '#1e40af'}

--- NOTES ---
{lp.get('generation_notes', 'Aucune note')}
"""
    
    return {"brief": brief, "lp": lp, "account": account}

@api_router.get("/generate-script/form/{form_id}")
async def generate_form_script(form_id: str, user: dict = Depends(get_current_user)):
    """Generate configuration brief for Form - text format for Emergent"""
    form = await db.forms.find_one({"id": form_id}, {"_id": 0})
    if not form:
        raise HTTPException(status_code=404, detail="Formulaire non trouvé")
    
    # Get account (try both field names for compatibility)
    account_id = form.get("account_id") or form.get("sub_account_id")
    account = await db.accounts.find_one({"id": account_id}, {"_id": 0}) if account_id else None
    
    # Get linked LPs
    lp_ids = form.get('lp_ids', [])
    linked_lps = []
    if lp_ids:
        linked_lps = await db.lps.find({"id": {"$in": lp_ids}}, {"_id": 0, "code": 1, "name": 1}).to_list(100)
    
    lps_text = "\n".join([f"  - {lp.get('code')} : {lp.get('name')}" for lp in linked_lps]) if linked_lps else "Aucune LP liée (formulaire standalone)"
    
    # Tracking type description
    tracking_type = form.get('tracking_type', 'redirect')
    if tracking_type == 'gtm':
        tracking_desc = "GTM - Déclencher le code de conversion après validation du téléphone (10 chiffres)"
    elif tracking_type == 'redirect':
        tracking_desc = "Redirection - Rediriger vers une page merci après soumission"
    else:
        tracking_desc = "Aucun tracking de conversion"
    
    # Build text brief
    brief = f"""=== BRIEF FORMULAIRE : {form.get('code', 'Non défini')} ===

NOM : {form.get('name', 'Non défini')}
TYPE DE PRODUIT : {form.get('product_type', 'panneaux')}
SOURCE : {form.get('source_name', 'Non défini')} ({form.get('source_type', 'native')})

--- MODE ---
Type : {form.get('form_type', 'standalone')} {'(formulaire intégré dans une LP)' if form.get('form_type') == 'integrated' else '(formulaire sur page séparée)'}

LPs liées :
{lps_text}

--- COMPTE ---
Nom du compte : {account.get('name', 'Non défini') if account else 'Non défini'}

--- LOGOS ---
Intégrer logo : {account.get('logo_left_url', 'Non') if account and account.get('logo_left_url') else 'Non'}
Logo URL : {account.get('logo_left_url', '') if account else ''}

--- CHAMPS OBLIGATOIRES ---
- Téléphone (10 chiffres) : OUI
- Nom : OUI  
- Département/Code postal : OUI

--- TRACKING CONVERSION ---
Type : {tracking_type}
Description : {tracking_desc}

Code de conversion (si GTM) :
{account.get('conversion_code', 'Non configuré') if account else 'Non configuré'}

URL de redirection (si redirect) :
{form.get('redirect_url_override') or (account.get('redirect_url') if account else '') or 'Non configuré'}

--- API CRM ---
Clé API : {form.get('api_key', 'Non configuré')}
CRM destination : {'MDL' if account and 'mdl' in account.get('name', '').lower() else 'ZR7' if account else 'Non défini'}

--- NOTES ---
{form.get('generation_notes', 'Aucune note')}
"""
    
    return {"brief": brief, "form": form, "account": account}

# ==================== USERS MANAGEMENT ====================

@api_router.get("/users")
async def get_users(user: dict = Depends(require_admin)):
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(100)
    return {"users": users}

@api_router.put("/users/{user_id}/role")
async def update_user_role(user_id: str, role: str, admin: dict = Depends(require_admin)):
    if role not in ["admin", "editor", "viewer"]:
        raise HTTPException(status_code=400, detail="Rôle invalide")
    
    result = await db.users.update_one({"id": user_id}, {"$set": {"role": role}})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    await log_activity(admin["id"], admin["email"], "update_role", "user", user_id, f"Rôle changé en: {role}")
    return {"success": True}

@api_router.put("/users/{user_id}")
async def update_user(user_id: str, update: UserUpdate, admin: dict = Depends(require_admin)):
    """Update user role and/or allowed accounts"""
    update_data = {}
    
    if update.role is not None:
        if update.role not in ["admin", "editor", "viewer"]:
            raise HTTPException(status_code=400, detail="Rôle invalide")
        update_data["role"] = update.role
    
    if update.allowed_accounts is not None:
        update_data["allowed_accounts"] = update.allowed_accounts
    
    if not update_data:
        raise HTTPException(status_code=400, detail="Aucune donnée à mettre à jour")
    
    result = await db.users.update_one({"id": user_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    details = []
    if update.role:
        details.append(f"Rôle: {update.role}")
    if update.allowed_accounts is not None:
        details.append(f"Comptes: {len(update.allowed_accounts)} autorisés")
    
    await log_activity(admin["id"], admin["email"], "update", "user", user_id, ", ".join(details))
    return {"success": True}

@api_router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(require_admin)):
    if admin["id"] == user_id:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas vous supprimer")
    
    result = await db.users.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    await db.sessions.delete_many({"user_id": user_id})
    await log_activity(admin["id"], admin["email"], "delete", "user", user_id, "Utilisateur supprimé")
    return {"success": True}

# ==================== LEGACY ENDPOINTS ====================

@api_router.get("/")
async def root():
    return {"message": "CRM API OK", "version": "2.0"}

@api_router.get("/admin/stats")
async def legacy_admin_stats():
    total = await db.leads.count_documents({})
    success = await db.leads.count_documents({"api_status": "success"})
    failed = await db.leads.count_documents({"api_status": "failed"})
    duplicate = await db.leads.count_documents({"api_status": "duplicate"})
    return {"total": total, "success": success, "failed": failed, "duplicate": duplicate}

@api_router.get("/admin/forms")
async def legacy_admin_forms():
    pipeline = [
        {"$group": {
            "_id": {"form_id": "$form_id", "form_code": "$form_code"},
            "total": {"$sum": 1},
            "success": {"$sum": {"$cond": [{"$eq": ["$api_status", "success"]}, 1, 0]}},
            "failed": {"$sum": {"$cond": [{"$eq": ["$api_status", "failed"]}, 1, 0]}}
        }}
    ]
    results = await db.leads.aggregate(pipeline).to_list(100)
    forms = [{"form_id": r["_id"].get("form_id", "default"), "form_code": r["_id"].get("form_code", ""), "total": r["total"], "success": r["success"], "failed": r["failed"]} for r in results]
    return {"forms": forms}

# ==================== APP SETUP ====================

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
