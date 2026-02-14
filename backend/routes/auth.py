"""
RDZ CRM - Routes Auth
Login / Logout / Session / User CRUD with granular permissions.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timezone, timedelta
import uuid

from models.auth import UserLogin, UserCreate, UserUpdate
from config import db, hash_password, generate_token, now_iso
from services.activity_logger import log_activity
from services.permissions import (
    get_preset_permissions,
    VALID_ROLES,
    ALL_PERMISSION_KEYS,
    user_has_permission,
    get_entity_scope_from_request,
)

router = APIRouter(prefix="/auth", tags=["Auth"])
security = HTTPBearer(auto_error=False)


# ==================== HELPERS ====================

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Récupère l'utilisateur connecté depuis le token."""
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

    if not user.get("is_active", user.get("active", True)):
        raise HTTPException(status_code=403, detail="Compte désactivé")

    # Ensure permissions exist (migration safety)
    if not user.get("permissions"):
        user["permissions"] = get_preset_permissions(user.get("role", "viewer"))

    return user


async def require_admin(user: dict = Depends(get_current_user)):
    """Admin or super_admin access."""
    if user.get("role") not in ("admin", "super_admin"):
        raise HTTPException(status_code=403, detail="Accès admin requis")
    return user


# ==================== LOGIN / LOGOUT ====================

@router.post("/login")
async def login(data: UserLogin, request: Request):
    """Connexion utilisateur."""
    user = await db.users.find_one(
        {"email": data.email.lower().strip()},
        {"_id": 0}
    )

    if not user:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")

    if user.get("password") != hash_password(data.password):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")

    if not user.get("is_active", user.get("active", True)):
        raise HTTPException(status_code=403, detail="Compte désactivé")

    token = generate_token()
    expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

    await db.sessions.insert_one({
        "token": token,
        "user_id": user["id"],
        "created_at": now_iso(),
        "expires_at": expires_at
    })

    await log_activity(
        user=user,
        action="login",
        entity_type="user",
        entity_id=user["id"],
        ip_address=request.client.host if request.client else None
    )

    permissions = user.get("permissions") or get_preset_permissions(user.get("role", "viewer"))

    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "nom": user.get("nom", ""),
            "entity": user.get("entity", ""),
            "role": user.get("role", "viewer"),
            "permissions": permissions,
        }
    }


@router.post("/logout")
async def logout(
    user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    if credentials:
        await db.sessions.delete_one({"token": credentials.credentials})
    return {"success": True}


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Retourne user + permissions."""
    permissions = user.get("permissions") or get_preset_permissions(user.get("role", "viewer"))
    user["permissions"] = permissions
    return user


# ==================== USER CRUD (super_admin or users.manage) ====================

@router.get("/users")
async def list_users(user: dict = Depends(get_current_user)):
    """Liste utilisateurs. Requires users.manage."""
    if not user_has_permission(user, "users.manage"):
        raise HTTPException(status_code=403, detail="Permission requise: users.manage")

    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(200)
    return {"users": users}


@router.post("/users")
async def create_user(data: UserCreate, user: dict = Depends(get_current_user)):
    """Créer un utilisateur. Requires users.manage."""
    if not user_has_permission(user, "users.manage"):
        raise HTTPException(status_code=403, detail="Permission requise: users.manage")

    existing = await db.users.find_one({"email": data.email.lower().strip()})
    if existing:
        raise HTTPException(status_code=400, detail="Cet email existe déjà")

    # Cannot create super_admin unless you are super_admin
    if data.role == "super_admin" and user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Seul un super_admin peut créer un super_admin")

    permissions = data.permissions if data.permissions else get_preset_permissions(data.role)

    new_user = {
        "id": str(uuid.uuid4()),
        "email": data.email.lower().strip(),
        "password": hash_password(data.password),
        "nom": data.nom,
        "entity": data.entity.upper(),
        "role": data.role,
        "permissions": permissions,
        "is_active": True,
        "created_at": now_iso(),
        "created_by": user.get("id")
    }

    await db.users.insert_one(new_user)

    await log_activity(
        user=user,
        action="create_user",
        entity_type="user",
        entity_id=new_user["id"],
        entity_name=new_user["email"],
        details={"role": data.role, "entity": data.entity}
    )

    new_user.pop("password", None)
    new_user.pop("_id", None)
    return {"success": True, "user": new_user}


@router.put("/users/{user_id}")
async def update_user(user_id: str, data: UserUpdate, user: dict = Depends(get_current_user)):
    """Mettre à jour un utilisateur. Requires users.manage."""
    if not user_has_permission(user, "users.manage"):
        raise HTTPException(status_code=403, detail="Permission requise: users.manage")

    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    # Cannot modify super_admin unless you are super_admin
    if target.get("role") == "super_admin" and user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Impossible de modifier un super_admin")

    update_data = {}

    if data.nom is not None:
        update_data["nom"] = data.nom
    if data.entity is not None:
        update_data["entity"] = data.entity.upper()
    if data.role is not None:
        if data.role == "super_admin" and user.get("role") != "super_admin":
            raise HTTPException(status_code=403, detail="Impossible d'attribuer le rôle super_admin")
        update_data["role"] = data.role
        if data.permissions is None:
            update_data["permissions"] = get_preset_permissions(data.role)
    if data.permissions is not None:
        update_data["permissions"] = data.permissions
    if data.is_active is not None:
        update_data["is_active"] = data.is_active

    update_data["updated_at"] = now_iso()

    await db.users.update_one({"id": user_id}, {"$set": update_data})

    await log_activity(
        user=user,
        action="update_user",
        entity_type="user",
        entity_id=user_id,
        entity_name=target.get("email"),
        details={k: v for k, v in update_data.items() if k != "updated_at"}
    )

    updated = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    return {"success": True, "user": updated}


@router.delete("/users/{user_id}")
async def deactivate_user(user_id: str, user: dict = Depends(get_current_user)):
    """Désactiver un utilisateur. Requires users.manage."""
    if not user_has_permission(user, "users.manage"):
        raise HTTPException(status_code=403, detail="Permission requise: users.manage")

    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    if user_id == user.get("id"):
        raise HTTPException(status_code=400, detail="Impossible de désactiver votre propre compte")

    if target.get("role") == "super_admin" and user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Impossible de désactiver un super_admin")

    await db.users.update_one(
        {"id": user_id},
        {"$set": {"is_active": False, "deactivated_at": now_iso()}}
    )
    await db.sessions.delete_many({"user_id": user_id})

    await log_activity(
        user=user,
        action="deactivate_user",
        entity_type="user",
        entity_id=user_id,
        entity_name=target.get("email")
    )

    return {"success": True}


# ==================== PERMISSION INTROSPECTION ====================

@router.get("/permission-keys")
async def list_permission_keys(user: dict = Depends(get_current_user)):
    """Returns all permission keys and role presets (for user management UI)."""
    if not user_has_permission(user, "users.manage"):
        raise HTTPException(status_code=403, detail="Permission requise: users.manage")
    from services.permissions import ROLE_PRESETS
    return {
        "keys": ALL_PERMISSION_KEYS,
        "presets": ROLE_PRESETS,
        "roles": VALID_ROLES
    }


# ==================== API KEY ====================

@router.get("/api-key")
async def get_api_key(user: dict = Depends(get_current_user)):
    config = await db.system_config.find_one({"type": "global_api_key"})
    if not config:
        from config import generate_api_key
        api_key = generate_api_key()
        await db.system_config.insert_one({
            "type": "global_api_key",
            "api_key": api_key,
            "created_at": now_iso()
        })
        return {"api_key": api_key}
    return {"api_key": config.get("api_key")}


# ==================== ACTIVITY LOG ====================

@router.get("/activity-logs")
async def get_activity_logs(
    user_id: str = None,
    entity_type: str = None,
    action: str = None,
    limit: int = 100,
    skip: int = 0,
    user: dict = Depends(get_current_user)
):
    if not user_has_permission(user, "activity.view"):
        raise HTTPException(status_code=403, detail="Permission requise: activity.view")
    from services.activity_logger import get_activity_logs as get_logs
    return await get_logs(user_id, entity_type, action, limit, skip)
