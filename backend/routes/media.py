"""
Routes pour la gestion des Médias (Images)
- Upload, liste, suppression d'images
- Partagé entre tous les CRMs (ZR7 et MDL)
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from config import db, now_iso
from routes.auth import get_current_user
from typing import Optional
import uuid
import os
import shutil
from pathlib import Path

router = APIRouter(prefix="/media", tags=["Media"])

# Dossier de stockage des médias
MEDIA_DIR = Path("/app/backend/static/media")
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

# Types de fichiers autorisés
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


@router.get("")
async def list_media(
    category: Optional[str] = None,
    crm_id: Optional[str] = None,
    limit: int = 100,
    user: dict = Depends(get_current_user)
):
    """
    Liste tous les médias
    - category: filtrer par catégorie (logo, banner, icon, other)
    - crm_id: filtrer par CRM (ou None pour médias partagés)
    """
    query = {}
    
    if category:
        query["category"] = category
    
    # Si crm_id spécifié, montrer les médias de ce CRM + les médias partagés
    if crm_id:
        query["$or"] = [
            {"crm_id": crm_id},
            {"shared": True},
            {"crm_id": None},
            {"crm_id": ""}
        ]
    
    media = await db.media.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    
    # Ajouter l'URL complète
    for m in media:
        m["url"] = f"/api/media/file/{m['id']}"
    
    return {"media": media, "count": len(media)}


@router.get("/file/{media_id}")
async def get_media_file(media_id: str):
    """Récupère le fichier média"""
    media = await db.media.find_one({"id": media_id})
    if not media:
        raise HTTPException(status_code=404, detail="Média non trouvé")
    
    file_path = MEDIA_DIR / media.get("filename")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Fichier non trouvé")
    
    return FileResponse(
        file_path,
        media_type=media.get("mime_type", "image/jpeg"),
        filename=media.get("original_name")
    )


@router.post("")
async def upload_media(
    file: UploadFile = File(...),
    name: str = Form(...),
    category: str = Form("other"),
    description: str = Form(""),
    shared: bool = Form(True),
    crm_id: str = Form(""),
    user: dict = Depends(get_current_user)
):
    """
    Upload un nouveau média
    - shared=True: disponible pour tous les CRMs
    - crm_id: associer à un CRM spécifique (optionnel)
    """
    # Vérifier l'extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Extension non autorisée. Extensions valides: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Vérifier la taille
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Fichier trop volumineux. Maximum: {MAX_FILE_SIZE // 1024 // 1024} MB"
        )
    
    # Générer un nom unique
    media_id = str(uuid.uuid4())
    filename = f"{media_id}{ext}"
    file_path = MEDIA_DIR / filename
    
    # Sauvegarder le fichier
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Déterminer le type MIME
    mime_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".svg": "image/svg+xml"
    }
    
    # Créer l'entrée en base
    media_doc = {
        "id": media_id,
        "name": name,
        "filename": filename,
        "original_name": file.filename,
        "mime_type": mime_types.get(ext, "image/jpeg"),
        "size": len(content),
        "category": category,  # logo, banner, icon, other
        "description": description,
        "shared": shared,  # Partagé entre CRMs
        "crm_id": crm_id if crm_id else None,  # CRM spécifique (optionnel)
        "uploaded_by": user["id"],
        "created_at": now_iso()
    }
    
    await db.media.insert_one(media_doc)
    media_doc.pop("_id", None)
    media_doc["url"] = f"/api/media/file/{media_id}"
    
    return {"success": True, "media": media_doc}


@router.put("/{media_id}")
async def update_media(
    media_id: str,
    name: str = Form(None),
    category: str = Form(None),
    description: str = Form(None),
    shared: bool = Form(None),
    crm_id: str = Form(None),
    user: dict = Depends(get_current_user)
):
    """Met à jour les métadonnées d'un média"""
    media = await db.media.find_one({"id": media_id})
    if not media:
        raise HTTPException(status_code=404, detail="Média non trouvé")
    
    update_data = {}
    if name is not None:
        update_data["name"] = name
    if category is not None:
        update_data["category"] = category
    if description is not None:
        update_data["description"] = description
    if shared is not None:
        update_data["shared"] = shared
    if crm_id is not None:
        update_data["crm_id"] = crm_id if crm_id else None
    
    if update_data:
        update_data["updated_at"] = now_iso()
        await db.media.update_one({"id": media_id}, {"$set": update_data})
    
    updated = await db.media.find_one({"id": media_id}, {"_id": 0})
    updated["url"] = f"/api/media/file/{media_id}"
    
    return {"success": True, "media": updated}


@router.delete("/{media_id}")
async def delete_media(media_id: str, user: dict = Depends(get_current_user)):
    """Supprime un média"""
    media = await db.media.find_one({"id": media_id})
    if not media:
        raise HTTPException(status_code=404, detail="Média non trouvé")
    
    # Supprimer le fichier
    file_path = MEDIA_DIR / media.get("filename")
    if file_path.exists():
        file_path.unlink()
    
    # Supprimer de la base
    await db.media.delete_one({"id": media_id})
    
    return {"success": True, "deleted_id": media_id}


@router.get("/categories")
async def list_categories(user: dict = Depends(get_current_user)):
    """Liste les catégories de médias"""
    return {
        "categories": [
            {"key": "logo", "label": "Logos"},
            {"key": "banner", "label": "Bannières"},
            {"key": "icon", "label": "Icônes"},
            {"key": "background", "label": "Arrière-plans"},
            {"key": "other", "label": "Autres"}
        ]
    }


@router.get("/stats")
async def media_stats(user: dict = Depends(get_current_user)):
    """Statistiques des médias"""
    total = await db.media.count_documents({})
    shared = await db.media.count_documents({"shared": True})
    
    # Par catégorie
    categories = {}
    for cat in ["logo", "banner", "icon", "background", "other"]:
        categories[cat] = await db.media.count_documents({"category": cat})
    
    # Par CRM
    crms = await db.crms.find({}, {"_id": 0, "id": 1, "name": 1, "slug": 1}).to_list(10)
    by_crm = {}
    for crm in crms:
        by_crm[crm["slug"]] = await db.media.count_documents({"crm_id": crm["id"]})
    
    return {
        "total": total,
        "shared": shared,
        "by_category": categories,
        "by_crm": by_crm
    }
