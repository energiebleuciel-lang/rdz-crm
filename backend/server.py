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

class LeadResponse(BaseModel):
    success: bool
    message: str
    duplicate: Optional[bool] = False

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
    This avoids CORS issues from the frontend
    """
    timestamp = int(datetime.now(timezone.utc).timestamp())
    
    # Format phone number
    phone = ''.join(filter(str.isdigit, lead.phone))
    if len(phone) == 9 and not phone.startswith('0'):
        phone = '0' + phone
    
    # Prepare data for external API
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
    
    logger.info(f"Submitting lead: {lead.nom}, phone: {phone}, dept: {lead.departement}")
    
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
            logger.info(f"API Response: status={response.status_code}, data={data}")
            
            if response.status_code == 201:
                return LeadResponse(success=True, message="Lead créé avec succès")
            elif response.status_code == 200 and "doublon" in str(data.get("message", "")).lower():
                return LeadResponse(success=True, message="Lead déjà enregistré", duplicate=True)
            else:
                return LeadResponse(
                    success=False, 
                    message=data.get("message") or data.get("error") or "Erreur lors de la création"
                )
                
    except httpx.TimeoutException:
        logger.error("API Timeout")
        return LeadResponse(success=False, message="Timeout - le serveur ne répond pas")
    except Exception as e:
        logger.error(f"API Error: {str(e)}")
        return LeadResponse(success=False, message=f"Erreur: {str(e)}")

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