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
        "leads": True, "departements": True, "commandes": True, "settings": True, "users": True
    },
    "editor": {
        "dashboard": True, "accounts": True, "lps": True, "forms": True,
        "leads": True, "departements": True, "commandes": False, "settings": False, "users": False
    },
    "viewer": {
        "dashboard": True, "accounts": False, "lps": True, "forms": True,
        "leads": True, "departements": True, "commandes": False, "settings": False, "users": False
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
async def login(data: UserLogin, request: Request):
    """Connexion utilisateur"""
    user = await db.users.find_one(
        {"email": data.email.lower().strip()},
        {"_id": 0}
    )
    
    if not user:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    
    if user.get("password") != hash_password(data.password):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    
    if user.get("active") == False:
        raise HTTPException(status_code=403, detail="Compte désactivé")
    
    # Créer session
    token = generate_token()
    expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    
    await db.sessions.insert_one({
        "token": token,
        "user_id": user["id"],
        "created_at": now_iso(),
        "expires_at": expires_at
    })
    
    # Log activité
    await log_activity(
        user=user,
        action="login",
        entity_type="user",
        entity_id=user["id"],
        ip_address=request.client.host if request.client else None
    )
    
    # Récupérer ou définir les permissions
    permissions = user.get("permissions") or DEFAULT_PERMISSIONS.get(user.get("role", "viewer"), {})
    
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "nom": user["nom"],
            "role": user["role"],
            "permissions": permissions
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
    permissions = user.get("permissions") or DEFAULT_PERMISSIONS.get(user.get("role", "viewer"), {})
    user["permissions"] = permissions
    return user


@router.post("/users", dependencies=[Depends(require_admin)])
async def create_user(data: UserCreate, current_user: dict = Depends(get_current_user)):
    """Créer un nouvel utilisateur (admin only)"""
    # Vérifier si email existe
    existing = await db.users.find_one({"email": data.email.lower().strip()})
    if existing:
        raise HTTPException(status_code=400, detail="Cet email existe déjà")
    
    # Permissions par défaut selon le rôle ou personnalisées
    permissions = data.permissions.dict() if data.permissions else DEFAULT_PERMISSIONS.get(data.role, {})
    
    user = {
        "id": str(uuid.uuid4()),
        "email": data.email.lower().strip(),
        "password": hash_password(data.password),
        "nom": data.nom,
        "role": data.role,
        "permissions": permissions,
        "active": True,
        "created_at": now_iso(),
        "created_by": current_user.get("id")
    }
    
    await db.users.insert_one(user)
    
    # Log activité
    await log_activity(
        user=current_user,
        action="create",
        entity_type="user",
        entity_id=user["id"],
        entity_name=user["email"],
        details={"role": data.role}
    )
    
    return {
        "success": True,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "nom": user["nom"],
            "role": user["role"],
            "permissions": permissions
        }
    }


@router.get("/users", dependencies=[Depends(require_admin)])
async def list_users():
    """Liste tous les utilisateurs (admin only)"""
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(100)
    return {"users": users}


@router.put("/users/{user_id}", dependencies=[Depends(require_admin)])
async def update_user(user_id: str, data: UserUpdate, current_user: dict = Depends(get_current_user)):
    """Mettre à jour un utilisateur (admin only)"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    update_data = {}
    
    if data.nom is not None:
        update_data["nom"] = data.nom
    if data.role is not None:
        update_data["role"] = data.role
        # Mettre à jour les permissions par défaut si le rôle change
        if data.permissions is None:
            update_data["permissions"] = DEFAULT_PERMISSIONS.get(data.role, {})
    if data.permissions is not None:
        update_data["permissions"] = data.permissions.dict()
    if data.active is not None:
        update_data["active"] = data.active
    
    update_data["updated_at"] = now_iso()
    
    await db.users.update_one({"id": user_id}, {"$set": update_data})
    
    # Log activité
    await log_activity(
        user=current_user,
        action="update",
        entity_type="user",
        entity_id=user_id,
        entity_name=user.get("email"),
        details=update_data
    )
    
    updated_user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    return {"success": True, "user": updated_user}


@router.delete("/users/{user_id}", dependencies=[Depends(require_admin)])
async def delete_user(user_id: str, current_user: dict = Depends(get_current_user)):
    """Désactiver un utilisateur (admin only)"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    if user_id == current_user.get("id"):
        raise HTTPException(status_code=400, detail="Impossible de supprimer votre propre compte")
    
    # Soft delete - désactiver plutôt que supprimer
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"active": False, "deactivated_at": now_iso()}}
    )
    
    # Invalider toutes les sessions
    await db.sessions.delete_many({"user_id": user_id})
    
    # Log activité
    await log_activity(
        user=current_user,
        action="delete",
        entity_type="user",
        entity_id=user_id,
        entity_name=user.get("email")
    )
    
    return {"success": True}


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



# ==================== JOURNAL D'ACTIVITÉ ====================

@router.get("/activity-logs", dependencies=[Depends(require_admin)])
async def get_activity_logs(
    user_id: str = None,
    entity_type: str = None,
    action: str = None,
    limit: int = 100,
    skip: int = 0
):
    """Récupère le journal d'activité (admin only)"""
    from services.activity_logger import get_activity_logs as get_logs
    return await get_logs(user_id, entity_type, action, limit, skip)