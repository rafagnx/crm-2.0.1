from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timedelta
import jwt
import bcrypt
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="CRM Kanban API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24 * 7  # 7 days

security = HTTPBearer()

# Enums
class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"

class LeadStatus(str, Enum):
    NEW = "novo"
    QUALIFIED = "qualificado"
    PROPOSAL = "proposta"
    NEGOTIATION = "negociacao"
    CLOSED_WON = "fechado_ganho"
    CLOSED_LOST = "fechado_perdido"

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    password_hash: str
    role: UserRole = UserRole.USER
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True

class UserCreate(BaseModel):
    email: str
    name: str
    password: str
    role: UserRole = UserRole.USER

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: UserRole
    created_at: datetime
    is_active: bool

class Lead(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    company: str = ""
    contact_name: str = ""
    email: str = ""
    phone: str = ""
    status: LeadStatus = LeadStatus.NEW
    tags: List[str] = []
    notes: str = ""
    value: float = 0.0
    assigned_to: str = ""  # User ID
    created_by: str = ""   # User ID
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    position: int = 0  # For drag & drop ordering

class LeadCreate(BaseModel):
    title: str
    company: str = ""
    contact_name: str = ""
    email: str = ""
    phone: str = ""
    status: LeadStatus = LeadStatus.NEW
    tags: List[str] = []
    notes: str = ""
    value: float = 0.0
    assigned_to: str = ""

class LeadUpdate(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[LeadStatus] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    value: Optional[float] = None
    assigned_to: Optional[str] = None
    position: Optional[int] = None

class Activity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    lead_id: str
    user_id: str
    action: str
    details: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class KanbanColumn(BaseModel):
    status: LeadStatus
    title: str
    color: str
    leads: List[Lead] = []

# Authentication helpers
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_jwt_token(user_id: str, email: str, role: str) -> str:
    payload = {
        'user_id': user_id,
        'email': email,
        'role': role,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_jwt_token(token: str) -> Dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    payload = verify_jwt_token(credentials.credentials)
    user = await db.users.find_one({"id": payload["user_id"]})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return User(**user)

# Authentication Routes
@api_router.post("/auth/register")
async def register(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password
    hashed_password = hash_password(user_data.password)
    
    # Create user
    user = User(
        email=user_data.email,
        name=user_data.name,
        password_hash=hashed_password,
        role=user_data.role
    )
    
    await db.users.insert_one(user.dict())
    
    # Create JWT token
    token = create_jwt_token(user.id, user.email, user.role.value)
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserResponse(**user.dict())
    }

@api_router.post("/auth/login")
async def login(user_data: UserLogin):
    # Find user
    user = await db.users.find_one({"email": user_data.email})
    if not user or not verify_password(user_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user["is_active"]:
        raise HTTPException(status_code=401, detail="Account deactivated")
    
    # Create JWT token
    token = create_jwt_token(user["id"], user["email"], user["role"])
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserResponse(**user)
    }

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(**current_user.dict())

# User Routes
@api_router.get("/users", response_model=List[UserResponse])
async def get_users(current_user: User = Depends(get_current_user)):
    users = await db.users.find({"is_active": True}).to_list(1000)
    return [UserResponse(**user) for user in users]

# Lead Routes
@api_router.post("/leads", response_model=Lead)
async def create_lead(lead_data: LeadCreate, current_user: User = Depends(get_current_user)):
    lead = Lead(**lead_data.dict(), created_by=current_user.id)
    
    # Get max position for the status
    max_position = await db.leads.find_one(
        {"status": lead.status}, 
        sort=[("position", -1)]
    )
    if max_position:
        lead.position = max_position["position"] + 1
    
    await db.leads.insert_one(lead.dict())
    
    # Log activity
    activity = Activity(
        lead_id=lead.id,
        user_id=current_user.id,
        action="created",
        details=f"Lead '{lead.title}' created"
    )
    await db.activities.insert_one(activity.dict())
    
    return lead

@api_router.get("/leads", response_model=List[Lead])
async def get_leads(current_user: User = Depends(get_current_user)):
    leads = await db.leads.find().sort("position", 1).to_list(1000)
    return [Lead(**lead) for lead in leads]

@api_router.get("/leads/{lead_id}", response_model=Lead)
async def get_lead(lead_id: str, current_user: User = Depends(get_current_user)):
    lead = await db.leads.find_one({"id": lead_id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return Lead(**lead)

@api_router.put("/leads/{lead_id}", response_model=Lead)
async def update_lead(
    lead_id: str, 
    lead_update: LeadUpdate, 
    current_user: User = Depends(get_current_user)
):
    lead = await db.leads.find_one({"id": lead_id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Update fields
    update_data = {k: v for k, v in lead_update.dict().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": update_data}
    )
    
    # Get updated lead
    updated_lead = await db.leads.find_one({"id": lead_id})
    
    # Log activity
    activity = Activity(
        lead_id=lead_id,
        user_id=current_user.id,
        action="updated",
        details=f"Lead updated"
    )
    await db.activities.insert_one(activity.dict())
    
    return Lead(**updated_lead)

@api_router.delete("/leads/{lead_id}")
async def delete_lead(lead_id: str, current_user: User = Depends(get_current_user)):
    result = await db.leads.delete_one({"id": lead_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Log activity
    activity = Activity(
        lead_id=lead_id,
        user_id=current_user.id,
        action="deleted",
        details=f"Lead deleted"
    )
    await db.activities.insert_one(activity.dict())
    
    return {"message": "Lead deleted successfully"}

# Kanban Board Routes
@api_router.get("/kanban", response_model=List[KanbanColumn])
async def get_kanban_board(current_user: User = Depends(get_current_user)):
    # Define column structure
    columns = [
        {"status": LeadStatus.NEW, "title": "Novo", "color": "#3B82F6"},
        {"status": LeadStatus.QUALIFIED, "title": "Qualificado", "color": "#10B981"},
        {"status": LeadStatus.PROPOSAL, "title": "Proposta", "color": "#F59E0B"},
        {"status": LeadStatus.NEGOTIATION, "title": "Negociação", "color": "#EF4444"},
        {"status": LeadStatus.CLOSED_WON, "title": "Fechado (Ganho)", "color": "#059669"},
        {"status": LeadStatus.CLOSED_LOST, "title": "Fechado (Perdido)", "color": "#6B7280"}
    ]
    
    kanban_columns = []
    for column in columns:
        leads = await db.leads.find({"status": column["status"]}).sort("position", 1).to_list(1000)
        kanban_columns.append(KanbanColumn(
            status=column["status"],
            title=column["title"],
            color=column["color"],
            leads=[Lead(**lead) for lead in leads]
        ))
    
    return kanban_columns

@api_router.post("/kanban/move")
async def move_lead(
    data: Dict,
    current_user: User = Depends(get_current_user)
):
    lead_id = data.get("lead_id")
    new_status = data.get("new_status")
    new_position = data.get("new_position", 0)
    
    if not lead_id or not new_status:
        raise HTTPException(status_code=400, detail="lead_id and new_status are required")
    
    # Update lead status and position
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {"status": new_status, "position": new_position, "updated_at": datetime.utcnow()}}
    )
    
    # Log activity
    activity = Activity(
        lead_id=lead_id,
        user_id=current_user.id,
        action="moved",
        details=f"Lead moved to {new_status}"
    )
    await db.activities.insert_one(activity.dict())
    
    return {"message": "Lead moved successfully"}

# Activity Routes
@api_router.get("/leads/{lead_id}/activities", response_model=List[Activity])
async def get_lead_activities(lead_id: str, current_user: User = Depends(get_current_user)):
    activities = await db.activities.find({"lead_id": lead_id}).sort("timestamp", -1).to_list(1000)
    return [Activity(**activity) for activity in activities]

# Dashboard/Stats Routes
@api_router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: User = Depends(get_current_user)):
    # Count leads by status
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    status_counts = await db.leads.aggregate(pipeline).to_list(None)
    
    # Total value
    value_pipeline = [
        {"$group": {"_id": None, "total_value": {"$sum": "$value"}}}
    ]
    value_result = await db.leads.aggregate(value_pipeline).to_list(None)
    total_value = value_result[0]["total_value"] if value_result else 0
    
    # Recent activities
    recent_activities = await db.activities.find().sort("timestamp", -1).limit(10).to_list(10)
    
    return {
        "status_counts": {item["_id"]: item["count"] for item in status_counts},
        "total_value": total_value,
        "recent_activities": [Activity(**activity) for activity in recent_activities]
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
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