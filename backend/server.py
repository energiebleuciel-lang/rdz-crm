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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI(title="CRM Leads System")
api_router = APIRouter(prefix="/api")
security = HTTPBearer(auto_error=False)

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
    if sub_account_id:
        query["sub_account_id"] = sub_account_id
    elif crm_id:
        # Get all sub-accounts for this CRM
        sub_accounts = await db.accounts.find({"crm_id": crm_id}, {"id": 1}).to_list(100)
        sub_account_ids = [sa["id"] for sa in sub_accounts]
        if sub_account_ids:
            query["sub_account_id"] = {"$in": sub_account_ids}
        else:
            return {"lps": []}
    
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
    if sub_account_id:
        query["sub_account_id"] = sub_account_id
    elif crm_id:
        # Get all sub-accounts for this CRM
        sub_accounts = await db.accounts.find({"crm_id": crm_id}, {"id": 1}).to_list(100)
        sub_account_ids = [sa["id"] for sa in sub_accounts]
        if sub_account_ids:
            query["sub_account_id"] = {"$in": sub_account_ids}
        else:
            return {"forms": []}
    
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
    # Ne pas écraser internal_api_key lors de la mise à jour
    result = await db.forms.update_one(
        {"id": form_id},
        {"$set": {**form.model_dump(), "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Formulaire non trouvé")
    await log_activity(user["id"], user["email"], "update", "form", form_id, f"Formulaire modifié: {form.code}")
    return {"success": True}

@api_router.delete("/forms/{form_id}")
async def delete_form(form_id: str, user: dict = Depends(require_admin)):
    result = await db.forms.delete_one({"id": form_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Formulaire non trouvé")
    await log_activity(user["id"], user["email"], "delete", "form", form_id, "Formulaire supprimé")
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

@api_router.post("/submit-lead")
async def submit_lead(lead: LeadData):
    """
    Soumission de lead avec ROUTAGE INTELLIGENT (OPTIONNEL) :
    
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
    
    # Get form config
    form_config = await db.forms.find_one({"code": lead.form_code})
    if not form_config:
        raise HTTPException(status_code=404, detail="Formulaire non trouvé")
    
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
                        target_crm = other_crm
                        routing_reason = f"rerouted_to_{other_crm.get('slug', 'other')}"
                        found_other = True
                        break
            
            if not found_other:
                # Aucun CRM n'a la commande → fallback origine
                target_crm = origin_crm
                routing_reason = "no_order_fallback_origin"
    
    # Déterminer l'URL et la clé API
    api_url = target_crm.get("api_url", "") if target_crm else ""
    api_key = form_config.get("crm_api_key") or form_config.get("api_key") or ""
    
    can_send = bool(phone and api_url and api_key)
    
    # Stocker le lead
    lead_doc = {
        "id": str(uuid.uuid4()),
        "form_id": lead.form_id or "",
        "form_code": lead.form_code or "",
        "lp_code": lead.lp_code or "",
        "account_id": account_id or "",
        "product_type": product_type,
        "origin_crm_id": origin_crm.get("id") if origin_crm else "",
        "target_crm_id": target_crm.get("id") if target_crm else "",
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
        
        await db.leads.update_one(
            {"id": lead_doc["id"]},
            {"$set": {
                "api_status": api_status, 
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
    
    # Filter by CRM - get all form codes belonging to this CRM's sub-accounts
    if crm_id:
        sub_accounts = await db.accounts.find({"crm_id": crm_id}, {"id": 1}).to_list(100)
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
    """Delete a single lead - Admin only"""
    result = await db.leads.delete_one({"id": lead_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead non trouvé")
    await log_activity(user["id"], user["email"], "delete", "lead", lead_id, "Lead supprimé")
    return {"success": True}

class BulkDeleteRequest(BaseModel):
    lead_ids: List[str]

@api_router.post("/leads/bulk-delete")
async def delete_multiple_leads(request: BulkDeleteRequest, user: dict = Depends(require_admin)):
    """Delete multiple leads - Admin only"""
    """Delete multiple leads"""
    if not request.lead_ids:
        raise HTTPException(status_code=400, detail="Aucun lead à supprimer")
    
    result = await db.leads.delete_many({"id": {"$in": request.lead_ids}})
    await log_activity(user["id"], user["email"], "delete", "leads", ",".join(request.lead_ids[:5]), f"{result.deleted_count} leads supprimés")
    return {"success": True, "deleted_count": result.deleted_count}

# ==================== ARCHIVAGE & FACTURATION ====================

@api_router.post("/leads/archive")
async def archive_old_leads(months: int = 3, user: dict = Depends(require_admin)):
    """
    Archiver les leads de plus de X mois.
    Les leads sont déplacés vers la collection 'leads_archived'.
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
    lines.append(f"🔑 CLÉ API : {form.get('internal_api_key', 'NON GÉNÉRÉE')}")
    lines.append(f"📍 ENDPOINT : POST {os.environ.get('BACKEND_URL', 'https://votre-domaine.com')}/api/submit-lead")
    lines.append("")
    lines.append("📋 HEADERS :")
    lines.append("   Content-Type: application/json")
    lines.append("")
    lines.append("📋 BODY (JSON) :")
    lines.append("{")
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
    lines.append("document.getElementById('form').addEventListener('submit', function(e) {")
    lines.append("  e.preventDefault();")
    lines.append("  ")
    lines.append("  // Vérifier les validations obligatoires")
    lines.append("  if (!canProceedToNextStep()) return;")
    lines.append("  ")
    lines.append("  // Envoi vers le CRM")
    lines.append("  fetch('/api/submit-lead', {")
    lines.append("    method: 'POST',")
    lines.append("    headers: { 'Content-Type': 'application/json' },")
    lines.append("    body: JSON.stringify({")
    lines.append(f"      form_code: '{form.get('code', '')}',")
    lines.append("      phone: document.getElementById('phone').value,")
    lines.append("      nom: document.getElementById('nom').value,")
    lines.append("      departement: document.getElementById('departement').value,")
    lines.append("      email: document.getElementById('email').value")
    lines.append("    })")
    lines.append("  })")
    lines.append("  .then(res => res.json())")
    lines.append("  .then(data => {")
    lines.append("    if (data.success) window.location.href = '/merci';")
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
