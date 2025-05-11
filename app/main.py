import uuid
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jose import JWTError, jwt
from app.database.mongodb import Database
from app.routers import auth, admin, images, items, campaigns, profile, notifications, admin_transactions, transactions
from app.services.auth import SECRET_KEY, ALGORITHM, get_password_hash, get_current_user
from datetime import datetime
import logging
import asyncio
from app.tasks.transaction_checker import run_transaction_checker

app = FastAPI(title="School Exchange Platform")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# Include routers
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(items.router)
app.include_router(campaigns.router)
app.include_router(profile.router)
app.include_router(notifications.router)
app.include_router(admin_transactions.router)
app.include_router(transactions.router)
app.include_router(images.router)

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_admin_exists():
    """Check if any admin account exists in the database."""
    admin = await Database.db.users.find_one({"role": "admin"})
    return admin is not None

async def create_default_admin():
    """Create a default admin account if no admin exists."""
    # Default admin credentials
    admin_username = "admin"
    admin_password = "admin123"  # Should be changed immediately after first login
    admin_name = "System Administrator"
    
    # Get next user ID
    last_user = await Database.db.users.find_one(sort=[("user_id", -1)])
    # next_user_id = 1 if not last_user else last_user["user_id"] + 1
    next_user_id = int(str(uuid.uuid4().int)[:9])
    
    # Create admin user document
    admin_user = {
        "username": admin_username,
        "password_hash": get_password_hash(admin_password),
        "role": "admin",
        "name": admin_name,
        "grade": None,
        "organization": "System Administration",
        "is_active": 1,
        "created_at": datetime.now().isoformat(),
        "user_id": next_user_id
    }
    
    # Insert into database
    result = await Database.db.users.insert_one(admin_user)
    if result.inserted_id:
        logger.info(f"Default admin user created with username: {admin_username}")
        logger.warning("Please change the default admin password after first login!")
    else:
        logger.error("Failed to create default admin user")

@app.on_event("startup")
async def startup_event():
    # Connect to database
    await Database.connect_to_database()
    
    # Check if admin exists, if not create one
    if not await check_admin_exists():
        logger.info("No admin account found. Creating default admin account...")
        await create_default_admin()
    
    # Start the transaction checker as a background task
    asyncio.create_task(run_transaction_checker())

@app.on_event("shutdown")
async def shutdown_db_client():
    await Database.close_database_connection()

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    try:
        user = await get_current_user(request)
        if user:
            # Redirect based on role
            if user["role"] == "admin":
                return RedirectResponse(url="/admin/dashboard")
            else:
                return RedirectResponse(url="/dashboard")
    except:
        pass
    
    return RedirectResponse(url="/login")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    try:
        token = request.cookies.get("access_token")
        if not token:
            return RedirectResponse(url="/login")
        
        token_type, access_token = token.split()
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        
        if username is None:
            return RedirectResponse(url="/login")
        
        # Get user from database
        db = Database.db
        user = await db.users.find_one({"username": username})
        
        if not user:
            return RedirectResponse(url="/login")
        
        # --- Bổ sung số liệu báo cáo cá nhân ---
        user_id = user["user_id"]
        # Sản phẩm
        pending_items = await db.items.count_documents({"user_id": user_id, "status": "pending"})
        approved_items = await db.items.count_documents({"user_id": user_id, "status": "active"})
        rejected_items = await db.items.count_documents({"user_id": user_id, "status": "rejected"})
        sold_items = await db.items.count_documents({"user_id": user_id, "status": "sold"})
        # Giao dịch
        purchase_transactions = await db.transactions.count_documents({"buyer_user_id": user_id, "transaction_type": "purchase"})
        exchange_transactions = await db.transactions.count_documents({"buyer_user_id": user_id, "transaction_type": "exchange"})
        donation_transactions = await db.transactions.count_documents({"buyer_user_id": user_id, "transaction_type": "donation"})
        # Số chiến dịch tham gia (unique campaign_id từ các giao dịch quyên góp)
        user_donations = await db.transactions.find({"buyer_user_id": user_id, "transaction_type": "donation"}).to_list(length=100)
        campaign_ids = set(d["campaign_id"] for d in user_donations if "campaign_id" in d)
        num_campaigns = len(campaign_ids)
        # --- Recent Activity ---
        recent_activities = []
        # Lấy 3 sản phẩm gần nhất
        recent_items = await db.items.find({"user_id": user_id}).sort("created_at", -1).limit(3).to_list(length=3)
        for item in recent_items:
            recent_activities.append({
                "type": "item",
                "name": item.get("name", "Sản phẩm"),
                "status": item.get("status", ""),
                "time": item.get("created_at", "")
            })
        # Lấy 2 giao dịch gần nhất
        recent_transactions = await db.transactions.find({"buyer_user_id": user_id}).sort("transaction_date", -1).limit(2).to_list(length=2)
        for tran in recent_transactions:
            recent_activities.append({
                "type": "transaction",
                "name": tran.get("transaction_type", "Giao dịch"),
                "status": tran.get("status", ""),
                "time": tran.get("transaction_date", "")
            })
        # Sắp xếp lại theo thời gian mới nhất
        recent_activities.sort(key=lambda x: x["time"], reverse=True)
        recent_activities = recent_activities[:5]
        # ---
        return templates.TemplateResponse(
            "dashboard.html", 
            {
                "request": request,
                "user": user,
                "pending_items": pending_items,
                "approved_items": approved_items,
                "rejected_items": rejected_items,
                "sold_items": sold_items,
                "purchase_transactions": purchase_transactions,
                "exchange_transactions": exchange_transactions,
                "donation_transactions": donation_transactions,
                "num_campaigns": num_campaigns,
                "recent_activities": recent_activities
            }
        )
    
    except JWTError:
        return RedirectResponse(url="/login")
