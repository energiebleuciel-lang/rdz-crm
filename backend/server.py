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

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    nom: str
    role: str

class CRMCreate(BaseModel):
    name: str  # "Maison du Lead", "ZR7"
    slug: str  # "mdl", "zr7"
    api_url: str
    description: Optional[str] = ""

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
    # Redirect URL par défaut
    default_redirect_url: Optional[str] = ""
    # Notes
    notes: Optional[str] = ""
    # Form template configuration
    form_template: Optional[FormTemplateConfig] = None

# For backwards compatibility, keep SubAccountCreate as alias
SubAccountCreate = AccountCreate

class LPCreate(BaseModel):
    account_id: str  # Renamed from sub_account_id
    code: str  # LP-TAB-V1
    name: str
    url: Optional[str] = ""
    source_type: str  # native, google, facebook, tiktok
    source_name: str  # Taboola, Outbrain, Google Ads
    cta_selector: str = ".cta-btn"
    screenshot_url: Optional[str] = ""
    diffusion_url: Optional[str] = ""
    notes: Optional[str] = ""
    status: str = "active"  # active, paused, archived
    # LP type configuration
    lp_type: str = "redirect"  # redirect (LP redirects to form URL), integrated (form embedded in LP)
    form_url: Optional[str] = ""  # URL of external form (for redirect type)
    # Generation notes/comments
    generation_notes: Optional[str] = ""

class FormCreate(BaseModel):
    account_id: str  # Renamed from sub_account_id
    lp_ids: List[str] = []  # List of LP IDs linked to this form
    code: str  # PV-TAB-001
    name: str
    product_type: str  # panneaux, pompes, isolation
    source_type: str
    source_name: str
    api_key: str  # API key for the CRM
    # Tracking type - juste le choix, le code est dans le compte
    tracking_type: str = "gtm"  # gtm, redirect, none
    # Override redirect URL (sinon utilise celle du compte)
    redirect_url_override: Optional[str] = ""
    screenshot_url: Optional[str] = ""
    notes: Optional[str] = ""
    status: str = "active"
    # Generation notes
    generation_notes: Optional[str] = ""
    screenshot_url: Optional[str] = ""
    notes: Optional[str] = ""
    status: str = "active"
    # Form type
    form_type: str = "standalone"  # standalone (separate page), integrated (in LP)
    # Generation notes/comments
    generation_notes: Optional[str] = ""  # Additional comments for script generation
    # Override template settings (if different from sub-account defaults)
    custom_fields_config: Optional[Dict[str, Any]] = None

class LeadData(BaseModel):
    phone: str
    nom: str
    email: Optional[str] = ""
    departement: Optional[str] = ""
    code_postal: Optional[str] = ""
    type_logement: Optional[str] = ""
    statut_occupant: Optional[str] = ""
    facture_electricite: Optional[str] = ""
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
    result = await db.sub_accounts.update_one(
        {"id": account_id},
        {"$set": {**account.model_dump(), "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Compte non trouvé")
    await log_activity(user["id"], user["email"], "update", "account", account_id, f"Compte modifié: {account.name}")
    return {"success": True}

@api_router.put("/sub-accounts/{account_id}")
async def update_sub_account_compat(account_id: str, account: SubAccountCreate, user: dict = Depends(get_current_user)):
    result = await db.sub_accounts.update_one(
        {"id": account_id},
        {"$set": {**account.model_dump(), "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Sous-compte non trouvé")
    await log_activity(user["id"], user["email"], "update", "sub_account", account_id, f"Sous-compte modifié: {account.name}")
    return {"success": True}

@api_router.delete("/accounts/{account_id}")
async def delete_account(account_id: str, user: dict = Depends(require_admin)):
    result = await db.sub_accounts.delete_one({"id": account_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Compte non trouvé")
    await log_activity(user["id"], user["email"], "delete", "account", account_id, "Compte supprimé")
    return {"success": True}

@api_router.delete("/sub-accounts/{account_id}")
async def delete_sub_account_compat(account_id: str, user: dict = Depends(require_admin)):
    result = await db.sub_accounts.delete_one({"id": account_id})
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
        sub_accounts = await db.sub_accounts.find({"crm_id": crm_id}, {"id": 1}).to_list(100)
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
async def delete_asset(asset_id: str, user: dict = Depends(get_current_user)):
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
        sub_accounts = await db.sub_accounts.find({"crm_id": crm_id}, {"id": 1}).to_list(100)
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
async def get_forms(sub_account_id: Optional[str] = None, crm_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    query = {}
    if sub_account_id:
        query["sub_account_id"] = sub_account_id
    elif crm_id:
        # Get all sub-accounts for this CRM
        sub_accounts = await db.sub_accounts.find({"crm_id": crm_id}, {"id": 1}).to_list(100)
        sub_account_ids = [sa["id"] for sa in sub_accounts]
        if sub_account_ids:
            query["sub_account_id"] = {"$in": sub_account_ids}
        else:
            return {"forms": []}
    
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
    form_doc = {
        "id": str(uuid.uuid4()),
        **form.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user["id"]
    }
    await db.forms.insert_one(form_doc)
    await log_activity(user["id"], user["email"], "create", "form", form_doc["id"], f"Formulaire créé: {form.code}")
    return {"success": True, "form": {k: v for k, v in form_doc.items() if k != "_id"}}

@api_router.put("/forms/{form_id}")
async def update_form(form_id: str, form: FormCreate, user: dict = Depends(get_current_user)):
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

@api_router.post("/forms/{form_id}/duplicate")
async def duplicate_form(form_id: str, new_code: str, new_name: str, new_api_key: str, user: dict = Depends(get_current_user)):
    """Duplicate a Form with a new code, name, and API key"""
    form = await db.forms.find_one({"id": form_id}, {"_id": 0})
    if not form:
        raise HTTPException(status_code=404, detail="Formulaire non trouvé")
    
    # Create new form with same config but new code/name/api_key
    new_form = {
        **form,
        "id": str(uuid.uuid4()),
        "code": new_code,
        "name": new_name,
        "api_key": new_api_key,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user["id"],
        "status": "active"
    }
    # Remove updated_at if exists
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

@api_router.post("/submit-lead")
async def submit_lead(lead: LeadData):
    """Submit a lead - validates, saves to DB and sends to CRM API"""
    timestamp = int(datetime.now(timezone.utc).timestamp())
    
    # Validate phone (10 digits, required)
    phone_valid, phone_result = validate_phone_fr(lead.phone)
    if not phone_valid:
        raise HTTPException(status_code=400, detail=phone_result)
    phone = phone_result
    
    # Validate nom (required)
    if not lead.nom or len(lead.nom.strip()) < 2:
        raise HTTPException(status_code=400, detail="Le nom est obligatoire (minimum 2 caractères)")
    
    # Validate postal code (France metro only if provided)
    code_postal = lead.code_postal or ""
    if code_postal:
        cp_valid, cp_result = validate_postal_code_fr(code_postal)
        if not cp_valid:
            raise HTTPException(status_code=400, detail=cp_result)
        code_postal = cp_result
    
    # Get form config
    form_config = await db.forms.find_one({"code": lead.form_code})
    if form_config:
        sub_account = await db.sub_accounts.find_one({"id": form_config.get("sub_account_id")})
        crm = await db.crms.find_one({"id": sub_account.get("crm_id")}) if sub_account else None
        api_url = crm.get("api_url") if crm else "https://maison-du-lead.com/lead/api/create_lead/"
        api_key = form_config.get("api_key", "")
    else:
        api_url = "https://maison-du-lead.com/lead/api/create_lead/"
        api_key = "0c21a444-2fc9-412f-9092-658cb6d62de6"
    
    lead_doc = {
        "id": str(uuid.uuid4()),
        "form_id": lead.form_id,
        "form_code": lead.form_code or "",
        "lp_code": lead.lp_code or "",
        "phone": phone,
        "nom": lead.nom.strip(),
        "email": lead.email or "",
        "departement": lead.departement or "",
        "code_postal": code_postal,
        "type_logement": lead.type_logement or "",
        "statut_occupant": lead.statut_occupant or "",
        "facture_electricite": lead.facture_electricite or "",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "register_date": timestamp,
        "api_status": "pending",
        "api_url": api_url
    }
    
    # Save to DB first
    await db.leads.insert_one(lead_doc)
    
    # Send to CRM API
    lead_payload = {
        "phone": phone,
        "register_date": timestamp,
        "nom": lead.nom.strip(),
        "prenom": "",
        "email": lead.email or "",
        "custom_fields": {
            "departement": {"value": lead.departement or ""},
            "code_postal": {"value": code_postal},
            "type_logement": {"value": lead.type_logement or ""},
            "statut_occupant": {"value": lead.statut_occupant or ""},
            "facture_electricite": {"value": lead.facture_electricite or ""}
        }
    }
    
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
    
    await db.leads.update_one(
        {"id": lead_doc["id"]},
        {"$set": {"api_status": api_status, "api_response": api_response}}
    )
    
    return {"success": True, "message": "Lead enregistré", "status": api_status}

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
        sub_accounts = await db.sub_accounts.find({"crm_id": crm_id}, {"id": 1}).to_list(100)
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
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead non trouvé")
    
    # Get API config
    form_config = await db.forms.find_one({"code": lead.get("form_code")})
    api_key = form_config.get("api_key") if form_config else "0c21a444-2fc9-412f-9092-658cb6d62de6"
    api_url = lead.get("api_url", "https://maison-du-lead.com/lead/api/create_lead/")
    
    lead_payload = {
        "phone": lead["phone"],
        "register_date": lead["register_date"],
        "nom": lead["nom"],
        "prenom": "",
        "email": lead.get("email", ""),
        "custom_fields": {
            "departement": {"value": lead.get("departement", "")},
            "type_logement": {"value": lead.get("type_logement", "")},
            "statut_occupant": {"value": lead.get("statut_occupant", "")},
            "facture_electricite": {"value": lead.get("facture_electricite", "")}
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            response = await http_client.post(
                api_url,
                json=lead_payload,
                headers={"Authorization": api_key, "Content-Type": "application/json"}
            )
            data = response.json()
            
            if response.status_code == 201:
                api_status = "success"
            elif "doublon" in str(data.get("message", "")).lower():
                api_status = "duplicate"
            else:
                api_status = "failed"
            
            await db.leads.update_one(
                {"id": lead_id},
                {"$set": {"api_status": api_status, "api_response": str(data), "retried_at": datetime.now(timezone.utc).isoformat()}}
            )
            
            return {"success": True, "status": api_status}
    except Exception as e:
        return {"success": False, "error": str(e)}

@api_router.delete("/leads/{lead_id}")
async def delete_lead(lead_id: str, user: dict = Depends(get_current_user)):
    """Delete a single lead"""
    result = await db.leads.delete_one({"id": lead_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead non trouvé")
    await log_activity(user["id"], user["email"], "delete", "lead", lead_id, "Lead supprimé")
    return {"success": True}

@api_router.delete("/leads")
async def delete_multiple_leads(lead_ids: List[str], user: dict = Depends(get_current_user)):
    """Delete multiple leads"""
    if not lead_ids:
        raise HTTPException(status_code=400, detail="Aucun lead à supprimer")
    
    result = await db.leads.delete_many({"id": {"$in": lead_ids}})
    await log_activity(user["id"], user["email"], "delete", "leads", ",".join(lead_ids[:5]), f"{result.deleted_count} leads supprimés")
    return {"success": True, "deleted_count": result.deleted_count}

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
        sub_accounts = await db.sub_accounts.find({"crm_id": crm_id}, {"id": 1}).to_list(100)
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
        sub_accounts = await db.sub_accounts.find({"crm_id": crm_id}, {"id": 1}).to_list(100)
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
        sub_accounts = await db.sub_accounts.find({"crm_id": {"$in": crm_filter}}, {"id": 1}).to_list(100)
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
        
        crm_sub_accounts = await db.sub_accounts.find({"crm_id": crm["id"]}, {"id": 1}).to_list(50)
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
    await log_activity(user["id"], user["email"], "comment", comment.entity_type, comment.entity_id, f"Commentaire ajouté")
    return {"success": True, "comment": {k: v for k, v in comment_doc.items() if k != "_id"}}

# ==================== ACTIVITY LOG ====================

@api_router.get("/activity-logs")
async def get_activity_logs(limit: int = 100, user: dict = Depends(require_admin)):
    logs = await db.activity_logs.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return {"logs": logs}

# ==================== SCRIPT GENERATOR ====================

@api_router.get("/generate-script/lp/{lp_id}")
async def generate_lp_script(lp_id: str, user: dict = Depends(get_current_user)):
    """Generate tracking script for LP"""
    lp = await db.lps.find_one({"id": lp_id}, {"_id": 0})
    if not lp:
        raise HTTPException(status_code=404, detail="LP non trouvée")
    
    sub_account = await db.sub_accounts.find_one({"id": lp.get("sub_account_id")}, {"_id": 0})
    
    backend_url = os.environ.get("BACKEND_URL", "https://rdz-group-ltd.online")
    
    script = f"""<!-- Tracking CTA - {lp['code']} -->
<script>
(function() {{
  var lpCode = '{lp['code']}';
  var backendUrl = '{backend_url}';
  
  // Track CTA clicks
  document.querySelectorAll('{lp.get('cta_selector', '.cta-btn')}').forEach(function(btn) {{
    btn.addEventListener('click', function() {{
      fetch(backendUrl + '/api/track/cta-click', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{ lp_code: lpCode, domain: window.location.hostname }})
      }});
    }});
  }});
}})();
</script>"""

    # Add pixel if configured
    if sub_account and sub_account.get("tracking_pixel_header"):
        script = sub_account["tracking_pixel_header"] + "\n\n" + script
    
    instructions = f"""
📋 INSTRUCTIONS POUR {lp['code']}

1️⃣ PIXEL HEADER (à mettre dans <head>)
{sub_account.get('tracking_pixel_header', '(Non configuré pour ce compte)')}

2️⃣ SCRIPT TRACKING CTA (à mettre avant </body>)
{script}

3️⃣ CONFIGURATION
- Sélecteur CTA : {lp.get('cta_selector', '.cta-btn')}
- Source : {lp.get('source_name', 'Non défini')}

⚠️ Ce script se déclenche quand un visiteur clique sur un bouton CTA.
"""
    
    return {"script": script, "instructions": instructions, "lp": lp}

@api_router.get("/generate-script/form/{form_id}")
async def generate_form_script(form_id: str, user: dict = Depends(get_current_user)):
    """Generate tracking and integration info for Form"""
    form = await db.forms.find_one({"id": form_id}, {"_id": 0})
    if not form:
        raise HTTPException(status_code=404, detail="Formulaire non trouvé")
    
    sub_account = await db.sub_accounts.find_one({"id": form.get("sub_account_id")}, {"_id": 0})
    
    backend_url = os.environ.get("BACKEND_URL", "https://rdz-group-ltd.online")
    
    # Form start tracking script
    form_start_script = f"""<!-- Tracking Form Start - {form['code']} -->
<script>
fetch('{backend_url}/api/track/form-start', {{
  method: 'POST',
  headers: {{'Content-Type': 'application/json'}},
  body: JSON.stringify({{ form_code: '{form['code']}', lp_code: new URLSearchParams(window.location.search).get('lp') || '' }})
}});
</script>"""

    # Conversion tracking
    if form.get("tracking_type") == "code":
        conversion_info = f"Code de conversion (après envoi téléphone):\n{form.get('tracking_code', '(Non configuré)')}"
    elif form.get("tracking_type") == "redirect":
        conversion_info = f"Redirection vers: {form.get('redirect_url', '(Non configuré)')}"
    else:
        conversion_info = f"Code: {form.get('tracking_code', '(Non configuré)')}\nRedirection: {form.get('redirect_url', '(Non configuré)')}"
    
    instructions = f"""
📋 INSTRUCTIONS POUR {form['code']}

1️⃣ TRACKING DÉMARRAGE (à mettre au chargement du formulaire)
{form_start_script}

2️⃣ CONFIGURATION API
- URL Backend: {backend_url}/api/submit-lead
- Form Code: {form['code']}
- Clé API CRM: {form.get('api_key', '(Non configuré)')}

3️⃣ TRACKING CONVERSION
Type: {form.get('tracking_type', 'redirect')}
{conversion_info}

4️⃣ LPs LIÉES
{', '.join(form.get('lp_ids', [])) or '(Aucune LP liée)'}
"""
    
    return {"form_start_script": form_start_script, "instructions": instructions, "form": form}

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
