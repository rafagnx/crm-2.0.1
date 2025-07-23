from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
import uuid
from datetime import datetime, timedelta
import jwt
import bcrypt
from enum import Enum
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow
import json
from twilio.rest import Client

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

# Google Calendar Configuration
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
GOOGLE_SCOPES = ['https://www.googleapis.com/auth/calendar']

# Twilio WhatsApp Configuration
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.environ.get('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')

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

class EventType(str, Enum):
    FOLLOW_UP = "follow_up"
    MEETING = "meeting"
    CALL = "call"
    DEMO = "demo"

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    password_hash: str
    role: UserRole = UserRole.USER
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
    google_tokens: Optional[Dict] = None

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
    priority: str = "medium"  # low, medium, high
    assigned_to: str = ""  # User ID
    created_by: str = ""   # User ID
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    position: int = 0  # For drag & drop ordering
    next_follow_up: Optional[datetime] = None
    expected_close_date: Optional[datetime] = None
    source: str = ""  # website, referral, cold_call, etc.

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
    priority: str = "medium"
    assigned_to: str = ""
    next_follow_up: Optional[datetime] = None
    expected_close_date: Optional[datetime] = None
    source: str = ""

# Advanced Reports Models
class ReportFilter(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    period: Optional[str] = "month"  # day, week, month, quarter, year
    user_id: Optional[str] = None
    status: Optional[str] = None

class AdvancedStats(BaseModel):
    # Métricas principais
    total_leads: int
    leads_by_period: Dict[str, int]
    conversion_rates: Dict[str, float]
    avg_deal_size: float
    total_pipeline_value: float
    
    # Funil de vendas
    funnel_data: Dict[str, Dict[str, Union[int, float]]]
    
    # Performance por período
    period_comparison: Dict[str, Dict[str, Union[int, float]]]
    
    # Métricas por usuário/equipe
    team_performance: List[Dict[str, Union[str, int, float]]]
    
    # Origem dos leads
    lead_sources: Dict[str, int]
    
    # Tempo médio por etapa
    avg_time_by_stage: Dict[str, float]

class ExportRequest(BaseModel):
    format: str  # "pdf", "excel", "csv"
    report_type: str  # "leads", "performance", "funnel"
    filters: ReportFilter

# Notifications Models
class NotificationType(str, Enum):
    LEAD_CREATED = "lead_created"
    LEAD_UPDATED = "lead_updated"
    LEAD_STATUS_CHANGED = "lead_status_changed"
    LEAD_ASSIGNED = "lead_assigned"
    FOLLOW_UP_DUE = "follow_up_due"
    DEAL_WON = "deal_won"
    DEAL_LOST = "deal_lost"
    HIGH_VALUE_LEAD = "high_value_lead"

class NotificationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class Notification(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    type: NotificationType
    title: str
    message: str
    priority: NotificationPriority = NotificationPriority.MEDIUM
    is_read: bool = False
    lead_id: Optional[str] = None
    action_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    read_at: Optional[datetime] = None
    metadata: Dict[str, Any] = {}

class NotificationCreate(BaseModel):
    user_id: str
    type: NotificationType
    title: str
    message: str
    priority: NotificationPriority = NotificationPriority.MEDIUM
    lead_id: Optional[str] = None
    action_url: Optional[str] = None
    metadata: Dict[str, Any] = {}

class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None
    read_at: Optional[datetime] = None

class NotificationSettings(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    lead_created: bool = True
    lead_status_changed: bool = True
    lead_assigned: bool = True
    follow_up_due: bool = True
    high_value_leads: bool = True
    deal_closed: bool = True
    email_notifications: bool = False
    push_notifications: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

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
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    position: Optional[int] = None
    next_follow_up: Optional[datetime] = None
    expected_close_date: Optional[datetime] = None
    source: Optional[str] = None

class Activity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    lead_id: str
    user_id: str
    action: str
    details: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class AutomationRule(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    trigger_status: LeadStatus
    action: str  # create_task, send_email, schedule_follow_up
    action_params: Dict = {}
    created_by: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AutomationRuleCreate(BaseModel):
    name: str
    trigger_status: LeadStatus
    action: str
    action_params: Dict = {}

class CalendarEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    lead_id: str
    user_id: str
    title: str
    description: str = ""
    start_time: datetime
    end_time: datetime
    event_type: EventType
    google_event_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CalendarEventCreate(BaseModel):
    lead_id: str
    title: str
    description: str = ""
    start_time: datetime
    end_time: datetime
    event_type: EventType

# Theme System Models
class ThemeColors(BaseModel):
    primary: str = "#3b82f6"  # Blue
    secondary: str = "#6b7280"  # Gray
    success: str = "#10b981"  # Green
    warning: str = "#f59e0b"  # Amber
    danger: str = "#ef4444"  # Red
    background: str = "#f8fafc"  # Slate-50
    surface: str = "#ffffff"  # White
    text_primary: str = "#1e293b"  # Slate-800
    text_secondary: str = "#64748b"  # Slate-500

class ThemeSettings(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str = "Custom Theme"
    colors: ThemeColors = Field(default_factory=ThemeColors)
    logo_base64: Optional[str] = None  # Base64 encoded logo
    font_family: str = "Inter, system-ui, sans-serif"
    font_size_base: str = "14px"
    border_radius: str = "0.5rem"
    is_dark_mode: bool = False
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ThemeCreate(BaseModel):
    name: str = "Custom Theme"
    colors: Optional[ThemeColors] = None
    logo_base64: Optional[str] = None
    font_family: Optional[str] = "Inter, system-ui, sans-serif"
    font_size_base: Optional[str] = "14px"
    border_radius: Optional[str] = "0.5rem"
    is_dark_mode: Optional[bool] = False

class ThemeUpdate(BaseModel):
    name: Optional[str] = None
    colors: Optional[ThemeColors] = None
    logo_base64: Optional[str] = None
    font_family: Optional[str] = None
    font_size_base: Optional[str] = None
    border_radius: Optional[str] = None
    is_dark_mode: Optional[bool] = None

# Webhook System Models
class WebhookEvent(str, Enum):
    LEAD_CREATED = "lead.created"
    LEAD_UPDATED = "lead.updated"
    LEAD_STATUS_CHANGED = "lead.status_changed"
    LEAD_DELETED = "lead.deleted"
    USER_REGISTERED = "user.registered"

class Webhook(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    url: str
    events: List[WebhookEvent]
    secret: str = Field(default_factory=lambda: str(uuid.uuid4()))
    is_active: bool = True
    retry_count: int = 3
    timeout_seconds: int = 30
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_triggered: Optional[datetime] = None
    total_triggers: int = 0
    failed_triggers: int = 0

class WebhookCreate(BaseModel):
    name: str
    url: str
    events: List[WebhookEvent]
    retry_count: Optional[int] = 3
    timeout_seconds: Optional[int] = 30

class WebhookUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    events: Optional[List[WebhookEvent]] = None
    is_active: Optional[bool] = None
    retry_count: Optional[int] = None
    timeout_seconds: Optional[int] = None

class WebhookLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    webhook_id: str
    event: WebhookEvent
    payload: Dict
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None
    attempt_count: int = 1
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    success: bool = False

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

# Google Calendar helpers
async def get_google_calendar_service(user: User):
    if not user.google_tokens:
        return None
    
    creds = Credentials(
        token=user.google_tokens.get('access_token'),
        refresh_token=user.google_tokens.get('refresh_token'),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=GOOGLE_SCOPES
    )
    
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Update tokens in database
        await db.users.update_one(
            {"id": user.id},
            {"$set": {"google_tokens": {
                "access_token": creds.token,
                "refresh_token": creds.refresh_token
            }}}
        )
    
    return build('calendar', 'v3', credentials=creds)

async def create_google_event(service, event_data: CalendarEvent):
    event = {
        'summary': event_data.title,
        'description': event_data.description,
        'start': {
            'dateTime': event_data.start_time.isoformat(),
            'timeZone': 'America/Sao_Paulo',
        },
        'end': {
            'dateTime': event_data.end_time.isoformat(),
            'timeZone': 'America/Sao_Paulo',
        },
    }
    
    try:
        result = service.events().insert(calendarId='primary', body=event).execute()
        return result.get('id')
    except Exception as e:
        logging.error(f"Error creating Google Calendar event: {e}")
        return None

# Automation helpers
async def process_automation_rules(lead_id: str, new_status: LeadStatus, user_id: str):
    """Process automation rules when a lead changes status"""
    rules = await db.automation_rules.find({"trigger_status": new_status, "is_active": True}).to_list(100)
    
    for rule_data in rules:
        rule = AutomationRule(**rule_data)
        
        if rule.action == "schedule_follow_up":
            # Schedule automatic follow-up
            follow_up_date = datetime.utcnow() + timedelta(days=rule.action_params.get('days', 3))
            await db.leads.update_one(
                {"id": lead_id},
                {"$set": {"next_follow_up": follow_up_date}}
            )
            
            # Log activity
            activity = Activity(
                lead_id=lead_id,
                user_id=user_id,
                action="automated_follow_up_scheduled",
                details=f"Follow-up automatically scheduled for {follow_up_date.strftime('%Y-%m-%d')}"
            )
            await db.activities.insert_one(activity.dict())
        
        elif rule.action == "create_task":
            # Create a task/activity
            activity = Activity(
                lead_id=lead_id,
                user_id=user_id,
                action="automated_task_created",
                details=rule.action_params.get('task_description', 'Automated task created')
            )
            await db.activities.insert_one(activity.dict())

# Webhook helpers
import asyncio
import aiohttp
import hashlib
import hmac

def clean_payload_for_webhook(payload):
    """Clean payload of MongoDB ObjectId objects for webhook serialization"""
    import json
    from bson import ObjectId
    from datetime import datetime
    
    def json_serializer(obj):
        """JSON serializer for objects not serializable by default json code"""
        if isinstance(obj, ObjectId):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")
    
    # Convert to JSON and back to ensure all ObjectIds are converted to strings
    json_str = json.dumps(payload, default=json_serializer)
    return json.loads(json_str)

async def trigger_webhooks(event: WebhookEvent, payload: Dict, user_id: str):
    """Trigger all webhooks for a specific event"""
    webhooks = await db.webhooks.find({
        "user_id": user_id,
        "events": event,
        "is_active": True
    }, {"_id": 0}).to_list(100)
    
    # Process webhooks in background
    if webhooks:
        asyncio.create_task(process_webhooks(webhooks, event, payload))

async def process_webhooks(webhooks: List[Dict], event: WebhookEvent, payload: Dict):
    """Process webhooks asynchronously"""
    # Clean payload of ObjectId objects
    clean_payload = clean_payload_for_webhook(payload)
    
    for webhook_data in webhooks:
        webhook = Webhook(**webhook_data)
        await send_webhook(webhook, event, clean_payload)

async def send_webhook(webhook: Webhook, event: WebhookEvent, payload: Dict):
    """Send individual webhook with retry logic"""
    webhook_payload = {
        "event": event,
        "data": payload,
        "timestamp": datetime.utcnow().isoformat(),
        "webhook_id": webhook.id
    }
    
    # Create signature
    signature = create_webhook_signature(webhook.secret, webhook_payload)
    
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": signature,
        "X-Webhook-Event": event,
        "User-Agent": "CRM-Webhook/1.0"
    }
    
    log_entry = WebhookLog(
        webhook_id=webhook.id,
        event=event,
        payload=webhook_payload
    )
    
    for attempt in range(webhook.retry_count):
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=webhook.timeout_seconds)) as session:
                async with session.post(webhook.url, json=webhook_payload, headers=headers) as response:
                    log_entry.response_status = response.status
                    log_entry.response_body = await response.text()
                    log_entry.attempt_count = attempt + 1
                    log_entry.completed_at = datetime.utcnow()
                    
                    if 200 <= response.status < 300:
                        log_entry.success = True
                        await update_webhook_stats(webhook.id, success=True)
                        break
                    else:
                        log_entry.success = False
                        log_entry.error_message = f"HTTP {response.status}: {log_entry.response_body}"
                        
        except asyncio.TimeoutError:
            log_entry.error_message = "Request timeout"
            log_entry.attempt_count = attempt + 1
        except Exception as e:
            log_entry.error_message = str(e)
            log_entry.attempt_count = attempt + 1
            
        # Wait before retry (exponential backoff)
        if attempt < webhook.retry_count - 1:
            await asyncio.sleep(2 ** attempt)
    
    # Save log entry
    await db.webhook_logs.insert_one(log_entry.dict())
    
    # Update webhook stats if final attempt failed
    if not log_entry.success:
        await update_webhook_stats(webhook.id, success=False)

def create_webhook_signature(secret: str, payload: Dict) -> str:
    """Create HMAC signature for webhook verification"""
    import json
    from bson import ObjectId
    from datetime import datetime
    
    def json_serializer(obj):
        """JSON serializer for objects not serializable by default json code"""
        if isinstance(obj, ObjectId):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")
    
    payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'), default=json_serializer)
    signature = hmac.new(
        secret.encode('utf-8'),
        payload_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"

async def update_webhook_stats(webhook_id: str, success: bool):
    """Update webhook statistics"""
    update_data = {
        "$set": {"last_triggered": datetime.utcnow()},
        "$inc": {"total_triggers": 1}
    }
    
    if not success:
        update_data["$inc"]["failed_triggers"] = 1
    
    await db.webhooks.update_one(
        {"id": webhook_id},
        update_data
    )

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
    
    # Trigger webhook (using admin user_id as reference since this is registration)
    await trigger_webhooks(WebhookEvent.USER_REGISTERED, {
        "user": UserResponse(**user.dict()).dict(),
        "registration_date": user.created_at.isoformat()
    }, user.id)
    
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

# Google Calendar OAuth Routes
@api_router.get("/auth/google/connect")
async def connect_google_calendar(current_user: User = Depends(get_current_user)):
    """Initiate Google Calendar OAuth flow"""
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=GOOGLE_SCOPES
    )
    
    flow.redirect_uri = f"https://89863155-7754-4917-8455-8b0133abbbcd.preview.emergentagent.com/api/auth/google/callback"
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        state=current_user.id
    )
    
    return {"authorization_url": authorization_url}

@api_router.get("/auth/google/callback")
async def google_calendar_callback(code: str, state: str):
    """Handle Google Calendar OAuth callback"""
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=GOOGLE_SCOPES
    )
    
    flow.redirect_uri = f"https://89863155-7754-4917-8455-8b0133abbbcd.preview.emergentagent.com/api/auth/google/callback"
    flow.fetch_token(code=code)
    
    credentials = flow.credentials
    
    # Save tokens to user
    await db.users.update_one(
        {"id": state},
        {"$set": {"google_tokens": {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token
        }}}
    )
    
    return {"message": "Google Calendar connected successfully"}

# User Routes
@api_router.get("/users", response_model=List[UserResponse])
async def get_users(current_user: User = Depends(get_current_user)):
    users = await db.users.find({"is_active": True}, {"_id": 0}).to_list(1000)
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
    
    # Process automation rules
    await process_automation_rules(lead.id, lead.status, current_user.id)
    
    # Trigger webhooks
    await trigger_webhooks(WebhookEvent.LEAD_CREATED, lead.dict(), current_user.id)
    
    # Create notifications
    await notify_lead_event(lead.dict(), "created", current_user.id)
    
    return lead

@api_router.get("/leads", response_model=List[Lead])
async def get_leads(
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    priority: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    query = {}
    if status:
        query["status"] = status
    if assigned_to:
        query["assigned_to"] = assigned_to
    if priority:
        query["priority"] = priority
    
    leads = await db.leads.find(query, {"_id": 0}).sort("position", 1).to_list(1000)
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
    
    old_status = lead["status"]
    new_status = update_data.get("status", old_status)
    
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
    
    # Process automation rules if status changed
    if old_status != new_status:
        await process_automation_rules(lead_id, new_status, current_user.id)
        # Trigger status change webhook
        await trigger_webhooks(WebhookEvent.LEAD_STATUS_CHANGED, {
            "lead": updated_lead,
            "old_status": old_status,
            "new_status": new_status
        }, current_user.id)
    
    # Trigger general update webhook
    await trigger_webhooks(WebhookEvent.LEAD_UPDATED, updated_lead, current_user.id)
    
    return Lead(**updated_lead)

@api_router.delete("/leads/{lead_id}")
async def delete_lead(lead_id: str, current_user: User = Depends(get_current_user)):
    # Get lead before deletion for webhook
    lead = await db.leads.find_one({"id": lead_id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
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
    
    # Trigger webhook
    await trigger_webhooks(WebhookEvent.LEAD_DELETED, lead, current_user.id)
    
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
        leads = await db.leads.find({"status": column["status"]}, {"_id": 0}).sort("position", 1).to_list(1000)
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
    
    # Get old status for automation
    lead = await db.leads.find_one({"id": lead_id})
    old_status = lead["status"] if lead else None
    
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
    
    # Process automation rules if status changed
    if old_status != new_status:
        await process_automation_rules(lead_id, new_status, current_user.id)
        
        # Get updated lead for webhook
        updated_lead = await db.leads.find_one({"id": lead_id})
        
        # Trigger status change webhook
        await trigger_webhooks(WebhookEvent.LEAD_STATUS_CHANGED, {
            "lead": updated_lead,
            "old_status": old_status,
            "new_status": new_status
        }, current_user.id)
    
    return {"message": "Lead moved successfully"}

# Calendar Routes
@api_router.post("/calendar/events", response_model=CalendarEvent)
async def create_calendar_event(
    event_data: CalendarEventCreate, 
    current_user: User = Depends(get_current_user)
):
    event = CalendarEvent(**event_data.dict(), user_id=current_user.id)
    
    # Try to create Google Calendar event
    service = await get_google_calendar_service(current_user)
    if service:
        google_event_id = await create_google_event(service, event)
        event.google_event_id = google_event_id
    
    await db.calendar_events.insert_one(event.dict())
    
    # Log activity
    activity = Activity(
        lead_id=event.lead_id,
        user_id=current_user.id,
        action="event_created",
        details=f"Calendar event '{event.title}' scheduled for {event.start_time.strftime('%Y-%m-%d %H:%M')}"
    )
    await db.activities.insert_one(activity.dict())
    
    return event

@api_router.get("/calendar/events", response_model=List[CalendarEvent])
async def get_calendar_events(current_user: User = Depends(get_current_user)):
    events = await db.calendar_events.find({"user_id": current_user.id}, {"_id": 0}).sort("start_time", 1).to_list(1000)
    return [CalendarEvent(**event) for event in events]

# Automation Routes
@api_router.post("/automation/rules", response_model=AutomationRule)
async def create_automation_rule(
    rule_data: AutomationRuleCreate,
    current_user: User = Depends(get_current_user)
):
    rule = AutomationRule(**rule_data.dict(), created_by=current_user.id)
    await db.automation_rules.insert_one(rule.dict())
    return rule

@api_router.get("/automation/rules", response_model=List[AutomationRule])
async def get_automation_rules(current_user: User = Depends(get_current_user)):
    rules = await db.automation_rules.find({"created_by": current_user.id}, {"_id": 0}).to_list(1000)
    return [AutomationRule(**rule) for rule in rules]

# Activity Routes
@api_router.get("/leads/{lead_id}/activities", response_model=List[Activity])
async def get_lead_activities(lead_id: str, current_user: User = Depends(get_current_user)):
    activities = await db.activities.find({"lead_id": lead_id}, {"_id": 0}).sort("timestamp", -1).to_list(1000)
    return [Activity(**activity) for activity in activities]

# Advanced Dashboard/Stats Routes
@api_router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: User = Depends(get_current_user)):
    # Count leads by status
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}, "total_value": {"$sum": "$value"}}}
    ]
    status_stats = await db.leads.aggregate(pipeline).to_list(None)
    
    # Conversion rates
    total_leads = await db.leads.count_documents({})
    closed_won = await db.leads.count_documents({"status": LeadStatus.CLOSED_WON})
    closed_lost = await db.leads.count_documents({"status": LeadStatus.CLOSED_LOST})
    
    conversion_rate = (closed_won / total_leads * 100) if total_leads > 0 else 0
    
    # Average deal size
    won_deals = await db.leads.find({"status": LeadStatus.CLOSED_WON}).to_list(None)
    avg_deal_size = sum(deal.get("value", 0) for deal in won_deals) / len(won_deals) if won_deals else 0
    
    # Recent activities
    recent_activities = await db.activities.find().sort("timestamp", -1).limit(10).to_list(10)
    
    # Monthly trends (last 6 months)
    from datetime import datetime, timedelta
    six_months_ago = datetime.utcnow() - timedelta(days=180)
    monthly_pipeline = [
        {"$match": {"created_at": {"$gte": six_months_ago}}},
        {"$group": {
            "_id": {
                "year": {"$year": "$created_at"},
                "month": {"$month": "$created_at"}
            },
            "leads_created": {"$sum": 1},
            "total_value": {"$sum": "$value"}
        }},
        {"$sort": {"_id.year": 1, "_id.month": 1}}
    ]
    monthly_trends = await db.leads.aggregate(monthly_pipeline).to_list(None)
    
    # Top performing sources
    source_pipeline = [
        {"$group": {"_id": "$source", "count": {"$sum": 1}, "total_value": {"$sum": "$value"}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]
    top_sources = await db.leads.aggregate(source_pipeline).to_list(None)
    
    return {
        "status_stats": {item["_id"]: {"count": item["count"], "value": item["total_value"]} for item in status_stats},
        "total_leads": total_leads,
        "conversion_rate": round(conversion_rate, 2),
        "avg_deal_size": round(avg_deal_size, 2),
        "recent_activities": [Activity(**activity) for activity in recent_activities],
        "monthly_trends": monthly_trends,
        "top_sources": top_sources
    }

@api_router.get("/reports/stats")
async def get_reports_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Enhanced stats endpoint with date filtering for reports"""
    from datetime import datetime
    
    # Build date filter
    date_filter = {}
    if start_date:
        date_filter["$gte"] = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    if end_date:
        date_filter["$lte"] = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    
    match_stage = {"created_at": date_filter} if date_filter else {}
    
    # Pipeline for status stats with date filter
    status_pipeline = [
        {"$match": match_stage},
        {"$group": {"_id": "$status", "count": {"$sum": 1}, "total_value": {"$sum": "$value"}}}
    ]
    status_stats = await db.leads.aggregate(status_pipeline).to_list(None)
    
    # Count total leads with date filter
    total_leads = await db.leads.count_documents(match_stage)
    
    # Conversion stats with date filter
    won_filter = {**match_stage, "status": LeadStatus.CLOSED_WON}
    lost_filter = {**match_stage, "status": LeadStatus.CLOSED_LOST}
    
    closed_won = await db.leads.count_documents(won_filter)
    closed_lost = await db.leads.count_documents(lost_filter)
    conversion_rate = (closed_won / total_leads * 100) if total_leads > 0 else 0
    
    # Average deal size with date filter
    won_deals = await db.leads.find(won_filter).to_list(None)
    avg_deal_size = sum(deal.get("value", 0) for deal in won_deals) / len(won_deals) if won_deals else 0
    
    # Daily trends within date range
    daily_pipeline = [
        {"$match": match_stage},
        {"$group": {
            "_id": {
                "year": {"$year": "$created_at"},
                "month": {"$month": "$created_at"},
                "day": {"$dayOfMonth": "$created_at"}
            },
            "leads_created": {"$sum": 1},
            "total_value": {"$sum": "$value"},
            "won_deals": {"$sum": {"$cond": [{"$eq": ["$status", "fechado_ganho"]}, 1, 0]}},
            "lost_deals": {"$sum": {"$cond": [{"$eq": ["$status", "fechado_perdido"]}, 1, 0]}}
        }},
        {"$sort": {"_id.year": 1, "_id.month": 1, "_id.day": 1}}
    ]
    daily_trends = await db.leads.aggregate(daily_pipeline).to_list(None)
    
    # Performance by user/assignee
    user_pipeline = [
        {"$match": match_stage},
        {"$group": {
            "_id": "$assigned_to",
            "leads_count": {"$sum": 1},
            "total_value": {"$sum": "$value"},
            "won_deals": {"$sum": {"$cond": [{"$eq": ["$status", "fechado_ganho"]}, 1, 0]}},
            "conversion_rate": {"$avg": {"$cond": [{"$eq": ["$status", "fechado_ganho"]}, 1, 0]}}
        }},
        {"$sort": {"total_value": -1}},
        {"$limit": 10}
    ]
    user_performance = await db.leads.aggregate(user_pipeline).to_list(None)
    
    # Lead sources performance
    source_pipeline = [
        {"$match": match_stage},
        {"$group": {
            "_id": "$source",
            "leads_count": {"$sum": 1},
            "total_value": {"$sum": "$value"},
            "won_deals": {"$sum": {"$cond": [{"$eq": ["$status", "fechado_ganho"]}, 1, 0]}},
            "avg_deal_size": {"$avg": "$value"}
        }},
        {"$sort": {"leads_count": -1}}
    ]
    source_performance = await db.leads.aggregate(source_pipeline).to_list(None)
    
    # Pipeline progress analysis
    pipeline_analysis = []
    for status in LeadStatus:
        status_leads = await db.leads.find({**match_stage, "status": status.value}).to_list(None)
        if status_leads:
            avg_time_in_status = 0  # Could calculate average time spent in each status
            pipeline_analysis.append({
                "status": status.value,
                "count": len(status_leads),
                "total_value": sum(lead.get("value", 0) for lead in status_leads),
                "avg_time_in_status": avg_time_in_status
            })
    
    return {
        "period": {
            "start_date": start_date,
            "end_date": end_date,
            "total_days": (datetime.fromisoformat(end_date.replace('Z', '+00:00')) - datetime.fromisoformat(start_date.replace('Z', '+00:00'))).days if start_date and end_date else None
        },
        "summary": {
            "total_leads": total_leads,
            "conversion_rate": round(conversion_rate, 2),
            "avg_deal_size": round(avg_deal_size, 2),
            "total_value": sum(item.get("total_value", 0) for item in status_stats),
            "closed_won": closed_won,
            "closed_lost": closed_lost
        },
        "status_stats": {item["_id"]: {"count": item["count"], "value": item.get("total_value", 0)} for item in status_stats},
        "daily_trends": daily_trends,
        "user_performance": user_performance,
        "source_performance": source_performance,
        "pipeline_analysis": pipeline_analysis
    }

# Theme Routes
@api_router.post("/themes", response_model=ThemeSettings)
async def create_theme(theme_data: ThemeCreate, current_user: User = Depends(get_current_user)):
    # Check if user already has an active theme
    existing_theme = await db.themes.find_one({"user_id": current_user.id, "is_active": True})
    
    # Deactivate existing theme if it exists
    if existing_theme:
        await db.themes.update_one(
            {"id": existing_theme["id"]},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
        )
    
    # Create new theme
    theme = ThemeSettings(
        user_id=current_user.id,
        **theme_data.dict(exclude_unset=True)
    )
    
    await db.themes.insert_one(theme.dict())
    return theme

@api_router.get("/themes/active", response_model=ThemeSettings)
async def get_active_theme(current_user: User = Depends(get_current_user)):
    theme = await db.themes.find_one({"user_id": current_user.id, "is_active": True})
    if not theme:
        # Return default theme
        default_theme = ThemeSettings(user_id=current_user.id)
        await db.themes.insert_one(default_theme.dict())
        return default_theme
    return ThemeSettings(**theme)

@api_router.get("/themes", response_model=List[ThemeSettings])
async def get_user_themes(current_user: User = Depends(get_current_user)):
    themes = await db.themes.find({"user_id": current_user.id}, {"_id": 0}).sort("created_at", -1).to_list(None)
    return [ThemeSettings(**theme) for theme in themes]

@api_router.put("/themes/{theme_id}", response_model=ThemeSettings)
async def update_theme(
    theme_id: str,
    theme_data: ThemeUpdate,
    current_user: User = Depends(get_current_user)
):
    theme = await db.themes.find_one({"id": theme_id, "user_id": current_user.id})
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
    
    update_data = theme_data.dict(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    
    await db.themes.update_one(
        {"id": theme_id},
        {"$set": update_data}
    )
    
    updated_theme = await db.themes.find_one({"id": theme_id})
    return ThemeSettings(**updated_theme)

@api_router.post("/themes/{theme_id}/activate")
async def activate_theme(theme_id: str, current_user: User = Depends(get_current_user)):
    theme = await db.themes.find_one({"id": theme_id, "user_id": current_user.id})
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
    
    # Deactivate all user themes
    await db.themes.update_many(
        {"user_id": current_user.id},
        {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
    )
    
    # Activate selected theme
    await db.themes.update_one(
        {"id": theme_id},
        {"$set": {"is_active": True, "updated_at": datetime.utcnow()}}
    )
    
    return {"message": "Theme activated successfully"}

@api_router.delete("/themes/{theme_id}")
async def delete_theme(theme_id: str, current_user: User = Depends(get_current_user)):
    theme = await db.themes.find_one({"id": theme_id, "user_id": current_user.id})
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
    
    if theme.get("is_active"):
        raise HTTPException(status_code=400, detail="Cannot delete active theme")
    
    await db.themes.delete_one({"id": theme_id})
    return {"message": "Theme deleted successfully"}

# Webhook Routes
@api_router.post("/webhooks", response_model=Webhook)
async def create_webhook(webhook_data: WebhookCreate, current_user: User = Depends(get_current_user)):
    webhook = Webhook(
        user_id=current_user.id,
        **webhook_data.dict()
    )
    
    await db.webhooks.insert_one(webhook.dict())
    return webhook

@api_router.get("/webhooks", response_model=List[Webhook])
async def get_webhooks(current_user: User = Depends(get_current_user)):
    webhooks = await db.webhooks.find({"user_id": current_user.id}, {"_id": 0}).sort("created_at", -1).to_list(None)
    return [Webhook(**webhook) for webhook in webhooks]

@api_router.get("/webhooks/{webhook_id}", response_model=Webhook)
async def get_webhook(webhook_id: str, current_user: User = Depends(get_current_user)):
    webhook = await db.webhooks.find_one({"id": webhook_id, "user_id": current_user.id})
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return Webhook(**webhook)

@api_router.put("/webhooks/{webhook_id}", response_model=Webhook)
async def update_webhook(
    webhook_id: str,
    webhook_data: WebhookUpdate,
    current_user: User = Depends(get_current_user)
):
    webhook = await db.webhooks.find_one({"id": webhook_id, "user_id": current_user.id})
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    update_data = webhook_data.dict(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    
    await db.webhooks.update_one(
        {"id": webhook_id},
        {"$set": update_data}
    )
    
    updated_webhook = await db.webhooks.find_one({"id": webhook_id})
    return Webhook(**updated_webhook)

@api_router.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str, current_user: User = Depends(get_current_user)):
    webhook = await db.webhooks.find_one({"id": webhook_id, "user_id": current_user.id})
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    await db.webhooks.delete_one({"id": webhook_id})
    return {"message": "Webhook deleted successfully"}

@api_router.post("/webhooks/{webhook_id}/test")
async def test_webhook(webhook_id: str, current_user: User = Depends(get_current_user)):
    webhook = await db.webhooks.find_one({"id": webhook_id, "user_id": current_user.id})
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    webhook_obj = Webhook(**webhook)
    
    # Send test payload
    test_payload = {
        "test": True,
        "message": "This is a test webhook from CRM System",
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": current_user.id
    }
    
    await send_webhook(webhook_obj, WebhookEvent.LEAD_CREATED, test_payload)
    
    return {"message": "Test webhook sent successfully"}

@api_router.get("/webhooks/{webhook_id}/logs", response_model=List[WebhookLog])
async def get_webhook_logs(
    webhook_id: str,
    current_user: User = Depends(get_current_user),
    limit: int = 50
):
    # Verify webhook ownership
    webhook = await db.webhooks.find_one({"id": webhook_id, "user_id": current_user.id})
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    logs = await db.webhook_logs.find(
        {"webhook_id": webhook_id}, 
        {"_id": 0}  # Exclude MongoDB _id field
    ).sort("triggered_at", -1) \
     .limit(limit) \
     .to_list(None)
    
    return [WebhookLog(**log) for log in logs]

# Advanced Reports Routes
@api_router.post("/reports/advanced", response_model=AdvancedStats)
async def get_advanced_reports(
    filters: ReportFilter,
    current_user: User = Depends(get_current_user)
):
    """Get advanced analytics and reports"""
    try:
        # Build MongoDB query based on filters
        match_query = {}
        if filters.start_date:
            match_query["created_at"] = {"$gte": filters.start_date}
        if filters.end_date:
            if "created_at" in match_query:
                match_query["created_at"]["$lte"] = filters.end_date
            else:
                match_query["created_at"] = {"$lte": filters.end_date}
        if filters.user_id:
            match_query["assigned_to"] = filters.user_id
        if filters.status:
            match_query["status"] = filters.status

        # Log for debugging
        logger.info(f"Report query: {match_query}")

        # Get all leads matching filters
        leads = await db.leads.find(match_query).to_list(None)
        logger.info(f"Found {len(leads)} leads for report")
        
        # Calculate basic metrics
        total_leads = len(leads)
        total_pipeline_value = sum(lead.get("value", 0) for lead in leads)
        avg_deal_size = total_pipeline_value / total_leads if total_leads > 0 else 0
        
        # Group by period for trends
        leads_by_period = {}
        period_format = {
            "day": "%Y-%m-%d",
            "week": "%Y-W%U", 
            "month": "%Y-%m",
            "quarter": "%Y-Q",
            "year": "%Y"
        }
        format_str = period_format.get(filters.period, "%Y-%m")
        
        for lead in leads:
            created_at = lead.get("created_at")
            if created_at:
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                period_key = created_at.strftime(format_str)
                leads_by_period[period_key] = leads_by_period.get(period_key, 0) + 1
        
        # Calculate conversion rates by status
        status_counts = {}
        for lead in leads:
            status = lead.get("status", "novo")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        conversion_rates = {}
        if total_leads > 0:
            for status, count in status_counts.items():
                conversion_rates[status] = (count / total_leads) * 100
        
        # Funnel data
        funnel_stages = ["novo", "qualificado", "proposta", "negociacao", "fechado_ganho", "fechado_perdido"]
        funnel_data = {}
        
        for i, stage in enumerate(funnel_stages):
            count = status_counts.get(stage, 0)
            conversion_rate = conversion_rates.get(stage, 0)
            funnel_data[stage] = {
                "count": count,
                "conversion_rate": conversion_rate,
                "stage_order": i
            }
        
        # Team performance (by assigned_to)
        team_performance = []
        assigned_counts = {}
        assigned_values = {}
        
        for lead in leads:
            assigned_to = lead.get("assigned_to", "Não atribuído")
            assigned_counts[assigned_to] = assigned_counts.get(assigned_to, 0) + 1
            assigned_values[assigned_to] = assigned_values.get(assigned_to, 0) + lead.get("value", 0)
        
        for user, count in assigned_counts.items():
            team_performance.append({
                "user": user,
                "leads_count": count,
                "total_value": assigned_values.get(user, 0),
                "avg_deal_size": assigned_values.get(user, 0) / count if count > 0 else 0
            })
        
        # Lead sources
        lead_sources = {}
        for lead in leads:
            source = lead.get("source", "Não informado")
            lead_sources[source] = lead_sources.get(source, 0) + 1
        
        # Average time by stage (simplified calculation)
        avg_time_by_stage = {}
        for stage in funnel_stages:
            # This is a simplified calculation - in reality you'd track stage transitions
            avg_time_by_stage[stage] = 7.0  # Default 7 days - this would be calculated from actual data
        
        # Period comparison (current vs previous)
        period_comparison = {
            "current_period": {
                "leads": total_leads,
                "value": total_pipeline_value,
                "conversion_rate": conversion_rates.get("fechado_ganho", 0)
            },
            "previous_period": {
                "leads": int(total_leads * 0.85),  # Mock data - would be actual previous period
                "value": total_pipeline_value * 0.9,
                "conversion_rate": conversion_rates.get("fechado_ganho", 0) * 0.95
            }
        }
        
        return AdvancedStats(
            total_leads=total_leads,
            leads_by_period=leads_by_period,
            conversion_rates=conversion_rates,
            avg_deal_size=avg_deal_size,
            total_pipeline_value=total_pipeline_value,
            funnel_data=funnel_data,
            period_comparison=period_comparison,
            team_performance=team_performance,
            lead_sources=lead_sources,
            avg_time_by_stage=avg_time_by_stage
        )
        
    except Exception as e:
        logger.error(f"Error generating advanced reports: {e}")
        raise HTTPException(status_code=500, detail="Error generating reports")

@api_router.post("/reports/export")
async def export_report(
    export_request: ExportRequest,
    current_user: User = Depends(get_current_user)
):
    """Export reports in various formats"""
    try:
        # Get the report data
        filters = export_request.filters
        advanced_stats = await get_advanced_reports(filters, current_user)
        
        if export_request.format == "csv":
            # Create CSV content
            import io
            import csv
            
            output = io.StringIO()
            
            if export_request.report_type == "leads":
                # Export leads data
                match_query = {}
                if filters.start_date:
                    match_query["created_at"] = {"$gte": filters.start_date}
                if filters.end_date:
                    if "created_at" in match_query:
                        match_query["created_at"]["$lte"] = filters.end_date
                    else:
                        match_query["created_at"] = {"$lte": filters.end_date}
                
                leads = await db.leads.find(match_query).to_list(None)
                
                if leads:
                    fieldnames = ["title", "company", "contact_name", "email", "phone", "status", "value", "source", "created_at"]
                    writer = csv.DictWriter(output, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for lead in leads:
                        writer.writerow({
                            "title": lead.get("title", ""),
                            "company": lead.get("company", ""),
                            "contact_name": lead.get("contact_name", ""),
                            "email": lead.get("email", ""),
                            "phone": lead.get("phone", ""),
                            "status": lead.get("status", ""),
                            "value": lead.get("value", 0),
                            "source": lead.get("source", ""),
                            "created_at": lead.get("created_at", "")
                        })
            
            elif export_request.report_type == "performance":
                # Export performance data
                writer = csv.writer(output)
                writer.writerow(["Metric", "Value"])
                writer.writerow(["Total Leads", advanced_stats.total_leads])
                writer.writerow(["Average Deal Size", f"R$ {advanced_stats.avg_deal_size:.2f}"])
                writer.writerow(["Total Pipeline Value", f"R$ {advanced_stats.total_pipeline_value:.2f}"])
                
                # Add conversion rates
                for status, rate in advanced_stats.conversion_rates.items():
                    writer.writerow([f"Conversion Rate - {status}", f"{rate:.2f}%"])
            
            csv_content = output.getvalue()
            output.close()
            
            # Return CSV file
            from fastapi.responses import StreamingResponse
            import io
            
            def iter_csv():
                yield csv_content
            
            return StreamingResponse(
                io.BytesIO(csv_content.encode()),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=report_{export_request.report_type}.csv"}
            )
        
        else:
            return {"message": f"Export format {export_request.format} not yet implemented"}
            
    except Exception as e:
        logger.error(f"Error exporting report: {e}")
        raise HTTPException(status_code=500, detail="Error exporting report")

# Notification Helper Functions
async def create_notification(
    user_id: str, 
    notification_type: NotificationType, 
    title: str, 
    message: str,
    priority: NotificationPriority = NotificationPriority.MEDIUM,
    lead_id: Optional[str] = None,
    action_url: Optional[str] = None,
    metadata: Dict[str, Any] = None
):
    """Helper function to create notifications"""
    try:
        # Check user notification settings
        settings = await db.notification_settings.find_one({"user_id": user_id})
        if not settings:
            # Create default settings
            default_settings = NotificationSettings(user_id=user_id)
            await db.notification_settings.insert_one(default_settings.dict())
            settings = default_settings.dict()
        
        # Check if this type of notification is enabled
        notification_enabled = True
        if notification_type == NotificationType.LEAD_CREATED:
            notification_enabled = settings.get("lead_created", True)
        elif notification_type == NotificationType.LEAD_STATUS_CHANGED:
            notification_enabled = settings.get("lead_status_changed", True)
        elif notification_type == NotificationType.LEAD_ASSIGNED:
            notification_enabled = settings.get("lead_assigned", True)
        elif notification_type == NotificationType.FOLLOW_UP_DUE:
            notification_enabled = settings.get("follow_up_due", True)
        elif notification_type == NotificationType.HIGH_VALUE_LEAD:
            notification_enabled = settings.get("high_value_leads", True)
        elif notification_type in [NotificationType.DEAL_WON, NotificationType.DEAL_LOST]:
            notification_enabled = settings.get("deal_closed", True)
        
        if not notification_enabled:
            return None
        
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            priority=priority,
            lead_id=lead_id,
            action_url=action_url,
            metadata=metadata or {}
        )
        
        await db.notifications.insert_one(notification.dict())
        logger.info(f"Notification created for user {user_id}: {title}")
        return notification
        
    except Exception as e:
        logger.error(f"Error creating notification: {e}")
        return None

async def notify_lead_event(lead: dict, event_type: str, user_id: str, old_status: str = None):
    """Create notifications for lead events"""
    try:
        lead_title = lead.get("title", "Lead sem título")
        lead_value = lead.get("value", 0)
        
        if event_type == "created":
            await create_notification(
                user_id=user_id,
                notification_type=NotificationType.LEAD_CREATED,
                title="Novo Lead Criado",
                message=f"Lead '{lead_title}' foi criado com valor de R$ {lead_value:.2f}",
                priority=NotificationPriority.MEDIUM,
                lead_id=lead.get("id"),
                action_url=f"/kanban#{lead.get('id')}"
            )
            
            # Check for high value lead  
            if lead_value > 10000:
                await create_notification(
                    user_id=user_id,
                    notification_type=NotificationType.HIGH_VALUE_LEAD,
                    title="Lead de Alto Valor!",
                    message=f"Lead '{lead_title}' tem valor alto: R$ {lead_value:.2f}",
                    priority=NotificationPriority.HIGH,
                    lead_id=lead.get("id"),
                    action_url=f"/kanban#{lead.get('id')}"
                )
        
        elif event_type == "status_changed":
            new_status = lead.get("status")
            await create_notification(
                user_id=user_id,
                notification_type=NotificationType.LEAD_STATUS_CHANGED,
                title="Status do Lead Alterado",
                message=f"Lead '{lead_title}' mudou de '{old_status}' para '{new_status}'",
                priority=NotificationPriority.MEDIUM,
                lead_id=lead.get("id"),
                action_url=f"/kanban#{lead.get('id')}"
            )
            
            # Special notifications for closed deals
            if new_status == "fechado_ganho":
                await create_notification(
                    user_id=user_id,
                    notification_type=NotificationType.DEAL_WON,
                    title="🎉 Negócio Fechado!",
                    message=f"Parabéns! Lead '{lead_title}' foi fechado com sucesso: R$ {lead_value:.2f}",
                    priority=NotificationPriority.HIGH,
                    lead_id=lead.get("id"),
                    action_url=f"/kanban#{lead.get('id')}"
                )
            elif new_status == "fechado_perdido":
                await create_notification(
                    user_id=user_id,
                    notification_type=NotificationType.DEAL_LOST,
                    title="Negócio Perdido",
                    message=f"Lead '{lead_title}' foi marcado como perdido",
                    priority=NotificationPriority.MEDIUM,
                    lead_id=lead.get("id"),
                    action_url=f"/kanban#{lead.get('id')}"
                )
        
        elif event_type == "assigned":
            assigned_to = lead.get("assigned_to", "")
            if assigned_to and assigned_to != "Não atribuído":
                await create_notification(
                    user_id=assigned_to,
                    notification_type=NotificationType.LEAD_ASSIGNED,
                    title="Lead Atribuído a Você",
                    message=f"Lead '{lead_title}' foi atribuído a você",
                    priority=NotificationPriority.MEDIUM,
                    lead_id=lead.get("id"),
                    action_url=f"/kanban#{lead.get('id')}"
                )
        
    except Exception as e:
        logger.error(f"Error creating lead notification: {e}")

# Notification Routes
@api_router.get("/notifications", response_model=List[Notification])
async def get_notifications(
    skip: int = 0,
    limit: int = 50,
    unread_only: bool = False,
    current_user: User = Depends(get_current_user)
):
    """Get user notifications"""
    try:
        query = {"user_id": current_user.id}
        if unread_only:
            query["is_read"] = False
        
        notifications = await db.notifications.find(
            query,
            {"_id": 0}
        ).sort("created_at", -1).skip(skip).limit(limit).to_list(None)
        
        return [Notification(**notification) for notification in notifications]
        
    except Exception as e:
        logger.error(f"Error fetching notifications: {e}")
        raise HTTPException(status_code=500, detail="Error fetching notifications")

@api_router.get("/notifications/count")
async def get_notification_count(current_user: User = Depends(get_current_user)):
    """Get notification counts"""
    try:
        total_count = await db.notifications.count_documents({"user_id": current_user.id})
        unread_count = await db.notifications.count_documents({"user_id": current_user.id, "is_read": False})
        
        return {
            "total": total_count,
            "unread": unread_count
        }
        
    except Exception as e:
        logger.error(f"Error getting notification count: {e}")
        raise HTTPException(status_code=500, detail="Error getting notification count")

@api_router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_user)
):
    """Mark notification as read"""
    try:
        notification = await db.notifications.find_one({
            "id": notification_id,
            "user_id": current_user.id
        })
        
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        await db.notifications.update_one(
            {"id": notification_id},
            {
                "$set": {
                    "is_read": True,
                    "read_at": datetime.utcnow()
                }
            }
        )
        
        return {"message": "Notification marked as read"}
        
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        raise HTTPException(status_code=500, detail="Error updating notification")

@api_router.put("/notifications/mark-all-read")
async def mark_all_notifications_read(current_user: User = Depends(get_current_user)):
    """Mark all notifications as read"""
    try:
        await db.notifications.update_many(
            {"user_id": current_user.id, "is_read": False},
            {
                "$set": {
                    "is_read": True,
                    "read_at": datetime.utcnow()
                }
            }
        )
        
        return {"message": "All notifications marked as read"}
        
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {e}")
        raise HTTPException(status_code=500, detail="Error updating notifications")

@api_router.delete("/notifications/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a notification"""
    try:
        result = await db.notifications.delete_one({
            "id": notification_id,
            "user_id": current_user.id
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        return {"message": "Notification deleted"}
        
    except Exception as e:
        logger.error(f"Error deleting notification: {e}")
        raise HTTPException(status_code=500, detail="Error deleting notification")

@api_router.get("/notifications/settings", response_model=NotificationSettings)
async def get_notification_settings(current_user: User = Depends(get_current_user)):
    """Get user notification settings"""
    try:
        settings = await db.notification_settings.find_one(
            {"user_id": current_user.id},
            {"_id": 0}
        )
        
        if not settings:
            # Create default settings
            default_settings = NotificationSettings(user_id=current_user.id)
            await db.notification_settings.insert_one(default_settings.dict())
            return default_settings
        
        return NotificationSettings(**settings)
        
    except Exception as e:
        logger.error(f"Error fetching notification settings: {e}")
        raise HTTPException(status_code=500, detail="Error fetching settings")

@api_router.put("/notifications/settings")
async def update_notification_settings(
    settings_update: dict,
    current_user: User = Depends(get_current_user)
):
    """Update user notification settings"""
    try:
        settings_update["updated_at"] = datetime.utcnow()
        
        await db.notification_settings.update_one(
            {"user_id": current_user.id},
            {"$set": settings_update},
            upsert=True
        )
        
        return {"message": "Notification settings updated"}
        
    except Exception as e:
        logger.error(f"Error updating notification settings: {e}")
        raise HTTPException(status_code=500, detail="Error updating settings")

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

@app.on_event("startup")
async def create_initial_users():
    """Create initial admin and support users if they don't exist"""
    try:
        # Check if admin user exists
        admin_user = await db.users.find_one({"email": "admin@descomplica.com"})
        if not admin_user:
            # Create admin user
            admin_password_hash = bcrypt.hashpw("Rafa040388?".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            admin_data = {
                "id": str(uuid.uuid4()),
                "email": "admin@descomplica.com",
                "name": "Administratora",
                "password_hash": admin_password_hash,
                "role": UserRole.ADMIN,
                "created_at": datetime.utcnow(),
                "is_active": True,
                "google_tokens": None
            }
            await db.users.insert_one(admin_data)
            logger.info("Admin user created successfully")
        
        # Remove old admin user if it exists (cleanup)
        old_admin_user = await db.users.find_one({"email": "admin"})
        if old_admin_user:
            await db.users.delete_one({"email": "admin"})
            logger.info("Old admin user removed")
        
        # Remove support user if it exists (cleanup) 
        support_user = await db.users.find_one({"email": "suporte"})
        if support_user:
            await db.users.delete_one({"email": "suporte"})
            logger.info("Support user removed")
            
    except Exception as e:
        logger.error(f"Error creating initial users: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()