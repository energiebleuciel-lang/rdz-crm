"""
Routes d'authentification
- Login / Logout
- Session management
- User management avec permissions
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timezone, timedelta
import uuid

from models import UserLogin, UserCreate, UserUpdate, UserResponse, UserPermissions
from config import db, hash_password, generate_token, now_iso
from services.activity_logger import log_activity

router = APIRouter(prefix="/auth", tags=["Auth"])
security = HTTPBearer(auto_error=False)

# Permissions par défaut selon le rôle
DEFAULT_PERMISSIONS = {
    "admin": {
        "dashboard": True, "accounts": True, "lps": True, "forms": True,
        "leads": True, "commandes": True, "settings": True, "users": True
    },
    "editor": {
        "dashboard": True, "accounts": True, "lps": True, "forms": True,
        "leads": True, "commandes": False, "settings": False, "users": False
    },
    "viewer": {
        "dashboard": True, "accounts": False, "lps": True, "forms": True,
        "leads": True, "commandes": False, "settings": False, "users": False
    }
}


# ==================== HELPERS ====================

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Récupère l'utilisateur connecté depuis le token"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    token = credentials.credentials
    session = await db.sessions.find_one({
        "token": token,
        "expires_at": {"$gt": now_iso()}
    })
    
    if not session:
        raise HTTPException(status_code=401, detail="Session expirée")
    
    user = await db.users.find_one(
        {"id": session["user_id"]},
        {"_id": 0, "password": 0}
    )
    
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur non trouvé")
    
    return user


async def require_admin(user: dict = Depends(get_current_user)):
    """Vérifie que l'utilisateur est admin"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Accès admin requis")
    return user


# ==================== ROUTES ====================

@router.post("/login")
async def login(data: UserLogin):
    """Connexion utilisateur"""
    user = await db.users.find_one(
        {"email": data.email.lower().strip()},
        {"_id": 0}
    )
    
    if not user:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    
    if user.get("password") != hash_password(data.password):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    
    # Créer session
    token = generate_token()
    expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    
    await db.sessions.insert_one({
        "token": token,
        "user_id": user["id"],
        "created_at": now_iso(),
        "expires_at": expires_at
    })
    
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "nom": user["nom"],
            "role": user["role"]
        }
    }


@router.post("/logout")
async def logout(user: dict = Depends(get_current_user), credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Déconnexion - invalide le token"""
    if credentials:
        await db.sessions.delete_one({"token": credentials.credentials})
    return {"success": True}


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Retourne les infos de l'utilisateur connecté"""
    return user


@router.post("/users", dependencies=[Depends(require_admin)])
async def create_user(data: UserCreate):
    """Créer un nouvel utilisateur (admin only)"""
    # Vérifier si email existe
    existing = await db.users.find_one({"email": data.email.lower().strip()})
    if existing:
        raise HTTPException(status_code=400, detail="Cet email existe déjà")
    
    user = {
        "id": str(uuid.uuid4()),
        "email": data.email.lower().strip(),
        "password": hash_password(data.password),
        "nom": data.nom,
        "role": data.role,
        "created_at": now_iso()
    }
    
    await db.users.insert_one(user)
    
    return {
        "success": True,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "nom": user["nom"],
            "role": user["role"]
        }
    }


@router.get("/users", dependencies=[Depends(require_admin)])
async def list_users():
    """Liste tous les utilisateurs (admin only)"""
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(100)
    return {"users": users}


@router.get("/api-key")
async def get_api_key(user: dict = Depends(get_current_user)):
    """Récupère la clé API globale pour l'API v1"""
    config = await db.system_config.find_one({"type": "global_api_key"})
    
    if not config:
        # Créer la clé si elle n'existe pas
        from config import generate_api_key
        api_key = generate_api_key()
        await db.system_config.insert_one({
            "type": "global_api_key",
            "api_key": api_key,
            "created_at": now_iso()
        })
        return {"api_key": api_key}
    
    return {"api_key": config.get("api_key")}
