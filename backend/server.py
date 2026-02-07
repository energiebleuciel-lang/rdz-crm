from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import httpx


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# API Lead Configuration
LEAD_API_URL = 'https://maison-du-lead.com/lead/api/create_lead/'
LEAD_API_KEY = '0c21a444-2fc9-412f-9092-658cb6d62de6'

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")  # Ignore MongoDB's _id field
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

# Lead Model
class LeadData(BaseModel):
    phone: str
    nom: str
    email: Optional[str] = ""
    departement: Optional[str] = ""
    type_logement: Optional[str] = ""
    statut_occupant: Optional[str] = ""
    facture_electricite: Optional[str] = ""
    # Multi-form support
    form_id: Optional[str] = "default"
    form_name: Optional[str] = "Formulaire Principal"

class LeadResponse(BaseModel):
    success: bool
    message: str
    duplicate: Optional[bool] = False

# Form Configuration Model
class FormConfig(BaseModel):
    form_id: str
    form_name: str
    api_url: str
    api_key: str
    redirect_url: str
    active: bool = True

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Hello World"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    
    # Convert to dict and serialize datetime to ISO string for MongoDB
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    # Exclude MongoDB's _id field from the query results
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    
    # Convert ISO string timestamps back to datetime objects
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks

# Lead submission endpoint (proxy to avoid CORS issues)
@api_router.post("/submit-lead", response_model=LeadResponse)
async def submit_lead(lead: LeadData):
    """
    Proxy endpoint to submit leads to the external API
    ALWAYS saves lead to MongoDB first, then sends to external API
    """
    timestamp = int(datetime.now(timezone.utc).timestamp())
    
    # Format phone number
    phone = ''.join(filter(str.isdigit, lead.phone))
    if len(phone) == 9 and not phone.startswith('0'):
        phone = '0' + phone
    
    # Prepare lead document for MongoDB
    lead_doc = {
        "id": str(uuid.uuid4()),
        "phone": phone,
        "nom": lead.nom,
        "email": lead.email or "",
        "departement": lead.departement or "",
        "type_logement": lead.type_logement or "",
        "statut_occupant": lead.statut_occupant or "",
        "facture_electricite": lead.facture_electricite or "",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "register_date": timestamp,
        "api_status": "pending",  # pending, success, failed, duplicate
        "api_response": None,
        "api_attempts": 0
    }
    
    # STEP 1: ALWAYS save to MongoDB first (never lose a lead!)
    try:
        await db.leads.insert_one(lead_doc)
        logger.info(f"Lead saved to MongoDB: {lead.nom}, phone: {phone}, id: {lead_doc['id']}")
    except Exception as e:
        logger.error(f"MongoDB Error: {str(e)}")
        # Continue anyway - try to send to API
    
    # STEP 2: Send to external API
    lead_payload = {
        "phone": phone,
        "register_date": timestamp,
        "nom": lead.nom,
        "prenom": "",
        "email": lead.email or "",
        "custom_fields": {
            "departement": {"value": lead.departement or ""},
            "type_logement": {"value": lead.type_logement or ""},
            "statut_occupant": {"value": lead.statut_occupant or ""},
            "facture_electricite": {"value": lead.facture_electricite or ""},
        }
    }
    
    logger.info(f"Sending lead to external API: {lead.nom}, phone: {phone}")
    
    api_status = "failed"
    api_response = None
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            response = await http_client.post(
                LEAD_API_URL,
                json=lead_payload,
                headers={
                    "Authorization": LEAD_API_KEY,
                    "Content-Type": "application/json"
                }
            )
            
            data = response.json()
            api_response = str(data)
            logger.info(f"API Response: status={response.status_code}, data={data}")
            
            if response.status_code == 201:
                api_status = "success"
                result = LeadResponse(success=True, message="Lead créé avec succès")
            elif response.status_code == 200 and "doublon" in str(data.get("message", "")).lower():
                api_status = "duplicate"
                result = LeadResponse(success=True, message="Lead déjà enregistré", duplicate=True)
            else:
                api_status = "failed"
                result = LeadResponse(
                    success=False, 
                    message=data.get("message") or data.get("error") or "Erreur lors de la création"
                )
                
    except httpx.TimeoutException:
        logger.error("API Timeout")
        api_status = "failed"
        api_response = "Timeout"
        result = LeadResponse(success=False, message="Timeout - le serveur ne répond pas")
    except Exception as e:
        logger.error(f"API Error: {str(e)}")
        api_status = "failed"
        api_response = str(e)
        result = LeadResponse(success=False, message=f"Erreur: {str(e)}")
    
    # STEP 3: Update MongoDB with API result
    try:
        await db.leads.update_one(
            {"id": lead_doc["id"]},
            {"$set": {
                "api_status": api_status,
                "api_response": api_response,
                "api_attempts": 1,
                "last_attempt_at": datetime.now(timezone.utc).isoformat()
            }}
        )
    except Exception as e:
        logger.error(f"MongoDB Update Error: {str(e)}")
    
    # Always return success to user (lead is saved anyway)
    return LeadResponse(success=True, message="Lead enregistré avec succès")


# Endpoint to get all leads (for admin)
@api_router.get("/leads")
async def get_leads(status: Optional[str] = None):
    """Get all leads, optionally filtered by API status"""
    query = {}
    if status:
        query["api_status"] = status
    
    leads = await db.leads.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return {"leads": leads, "count": len(leads)}


# Endpoint to retry failed leads
@api_router.post("/leads/retry-failed")
async def retry_failed_leads():
    """Retry sending failed leads to external API"""
    failed_leads = await db.leads.find({"api_status": "failed"}, {"_id": 0}).to_list(100)
    
    results = {"retried": 0, "success": 0, "failed": 0}
    
    for lead_doc in failed_leads:
        results["retried"] += 1
        
        lead_payload = {
            "phone": lead_doc["phone"],
            "register_date": lead_doc["register_date"],
            "nom": lead_doc["nom"],
            "prenom": "",
            "email": lead_doc.get("email", ""),
            "custom_fields": {
                "departement": {"value": lead_doc.get("departement", "")},
                "type_logement": {"value": lead_doc.get("type_logement", "")},
                "statut_occupant": {"value": lead_doc.get("statut_occupant", "")},
                "facture_electricite": {"value": lead_doc.get("facture_electricite", "")},
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                response = await http_client.post(
                    LEAD_API_URL,
                    json=lead_payload,
                    headers={
                        "Authorization": LEAD_API_KEY,
                        "Content-Type": "application/json"
                    }
                )
                
                data = response.json()
                
                if response.status_code == 201:
                    api_status = "success"
                    results["success"] += 1
                elif "doublon" in str(data.get("message", "")).lower():
                    api_status = "duplicate"
                    results["success"] += 1
                else:
                    api_status = "failed"
                    results["failed"] += 1
                
                await db.leads.update_one(
                    {"id": lead_doc["id"]},
                    {"$set": {
                        "api_status": api_status,
                        "api_response": str(data),
                        "api_attempts": lead_doc.get("api_attempts", 0) + 1,
                        "last_attempt_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
                
        except Exception as e:
            results["failed"] += 1
            logger.error(f"Retry failed for {lead_doc['id']}: {str(e)}")
    
    return results

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()