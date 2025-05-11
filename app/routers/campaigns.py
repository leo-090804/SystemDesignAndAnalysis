import uuid
import asyncio # Import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request, Query, Path, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import datetime, timedelta
import logging
from app.database.mongodb import Database
from app.services.auth import get_current_user

router = APIRouter(prefix="/campaigns", tags=["campaigns"])
templates = Jinja2Templates(directory="templates")

# Middleware to check user is logged in
async def user_required(request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    if not user.get("is_active"):
        raise HTTPException(status_code=403, detail="Account is locked")
    return user

logger = logging.getLogger(__name__)

# Dictionary to hold locks for donation processing
# Key: f"{user_id}-{campaign_id}-{amount}" -> Value: asyncio.Lock()
donation_locks = {}
# Lock to protect access to the donation_locks dictionary itself
locks_dict_lock = asyncio.Lock()

@router.get("/", response_class=HTMLResponse)
async def list_campaigns(
    request: Request,
    user: dict = Depends(user_required),
    campaign_type: Optional[str] = None,
    page: int = Query(1, ge=1)
):
    # Admins should use the admin campaigns interface
    if user["role"] == "admin":
        return RedirectResponse(url="/admin/campaigns")
        
    db = Database.db
    limit = 6
    skip = (page - 1) * limit
    
    # Build query
    query = {"status": "active"}
    if campaign_type:
        query["campaign_type"] = campaign_type
    
    # Ensure campaigns collection exists
    if "campaigns" not in await db.list_collection_names():
        campaigns = []
        total_campaigns = 0
    else:
        # Get campaigns
        campaigns = await db.campaigns.find(query).skip(skip).limit(limit).to_list(length=limit)
        total_campaigns = await db.campaigns.count_documents(query)
    
    total_pages = (total_campaigns + limit - 1) // limit if total_campaigns > 0 else 1
    
    return templates.TemplateResponse(
        "campaigns/list.html",
        {"request": request, "user": user, "campaigns": campaigns, 
         "campaign_type": campaign_type, "page": page, "total_pages": total_pages}
    )

@router.get("/{campaign_id}", response_class=HTMLResponse)
async def view_campaign(
    request: Request,
    campaign_id: int = Path(...),
    user: dict = Depends(user_required)
):
    # Admins should use the admin campaigns interface
    if user["role"] == "admin":
        return RedirectResponse(url=f"/admin/campaigns/{campaign_id}")
        
    db = Database.db
    
    # Get campaign
    campaign = await db.campaigns.find_one({"campaign_id": campaign_id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Only allow viewing active campaigns
    if campaign["status"] != "active" and user["role"] != "admin":
        raise HTTPException(status_code=403, detail="This campaign is no longer active")
    
    # Get campaign creator
    creator = await db.users.find_one({"user_id": campaign["created_by"]})
    
    # Get items participating in this campaign
    campaign_items = await db.items.find(
        {"campaign_id": campaign_id, "status": "active"}
    ).limit(12).to_list(length=12)
    
    return templates.TemplateResponse(
        "campaigns/view.html",
        {"request": request, "user": user, "campaign": campaign, 
         "creator": creator, "campaign_items": campaign_items}
    )

@router.post("/{campaign_id}/donate")
async def make_donation(
    campaign_id: int = Path(...),
    user: dict = Depends(user_required),
    amount: float = Form(...),
    message: Optional[str] = Form(None)
):
    if user["role"] == "admin":
        raise HTTPException(status_code=403, detail="Admins cannot make donations")
    
    db = Database.db
        
    # Define a unique key for this potential donation attempt
    donation_key = f"{user['user_id']}-{campaign_id}-{amount}"

    # Get or create the lock for this specific donation key atomically
    async with locks_dict_lock:
        if donation_key not in donation_locks:
            donation_locks[donation_key] = asyncio.Lock()
        specific_donation_lock = donation_locks[donation_key]

    # Acquire the specific lock for this donation attempt
    async with specific_donation_lock:
        try:
            # Validate amount (can be done before or inside lock)
            if amount <= 0:
                return {"success": False, "message": "Số tiền quyên góp phải lớn hơn 0"}
            
            # Get campaign (can be done before or inside lock)
            campaign = await db.campaigns.find_one({"campaign_id": campaign_id})
            if not campaign:
                return {"success": False, "message": "Không tìm thấy chiến dịch"}
            
            if campaign["status"] != "active":
                return {"success": False, "message": "Chiến dịch này không còn hoạt động"}

            # --- Critical Section Start ---
            # Re-check for duplicate submissions INSIDE the lock
            thirty_seconds_ago = (datetime.now() - timedelta(seconds=30)).isoformat()
            existing_transaction = await db.transactions.find_one({
                "transaction_type": "donation",
                "buyer_user_id": user["user_id"],
                "campaign_id": campaign_id,
                "amount": amount,
                "transaction_date": {"$gt": thirty_seconds_ago}
            })
            
            if existing_transaction:
                # Duplicate found inside the lock, return existing one
                logger.info(f"Prevented duplicate donation (inside lock) from user {user['user_id']} to campaign {campaign_id}")
                return {
                    "success": True,
                    "message": "Khoản quyên góp của bạn đang được xử lý. Vui lòng chờ quản trị viên duyệt.",
                    "transaction_id": existing_transaction["transaction_id"]
                }
                
            # No duplicate found, proceed to create the transaction
            current_time = datetime.now().isoformat()
            transaction_id = int(str(uuid.uuid4().int)[:9])
            
            transaction = {
                "transaction_id": transaction_id,
                "transaction_type": "donation",
                "amount": amount,
                "transaction_date": current_time,
                "status": "pending",
                "status_updated_at": current_time,
                "cancellation_reason": None,
                "buyer_user_id": user["user_id"],
                "seller_user_id": None,
                "item_id": None,
                "campaign_id": campaign_id,
                "message": message
            }
            
            await db.transactions.insert_one(transaction)
            # --- Critical Section End ---

            # Notifications can happen outside the critical section if desired
            # Create notification for donor
            donor_notification = {
                "message": f"Khoản quyên góp {amount:.2f} VNĐ cho chiến dịch '{campaign['name']}' của bạn đang chờ quản trị viên duyệt.",
                "created_at": current_time,
                "is_read": False,
                "is_seen": False,
                "noti_id": int(str(uuid.uuid4().int)[:9]),
                "user_id": user["user_id"],
                "related_item_id": None,
                "related_transaction_id": transaction_id,
            }
            await db.notifications.insert_one(donor_notification)
            
            # Create notification for admins
            admin_users = await db.users.find({"role": "admin"}).to_list(length=100)
            for admin in admin_users:
                admin_notification = {
                    "message": f"Có khoản quyên góp mới {amount:.2f} VNĐ từ {user['name']} cho chiến dịch '{campaign['name']}' cần được duyệt.",
                    "created_at": current_time,
                    "is_read": False,
                    "is_seen": False,
                    "noti_id": int(str(uuid.uuid4().int)[:9]),
                    "user_id": admin["user_id"],
                    "related_item_id": None,
                    "related_transaction_id": transaction_id,
                    "priority": "high"
                }
                await db.notifications.insert_one(admin_notification)
            
            return {
                "success": True,
                "message": "Gửi quyên góp thành công. Đang chờ quản trị viên duyệt.",
                "transaction_id": transaction_id
            }
            
        except Exception as e:
            logger.error(f"Error processing donation inside lock: {str(e)}")
            # The lock is automatically released by 'async with' even if an error occurs
            return {"success": False, "message": "Đã xảy ra lỗi khi xử lý quyên góp của bạn"}
        # Lock is released automatically here

# Helper function to get next ID - if not already defined elsewhere
# async def get_next_id(db, collection_name, id_field):
#     last_doc = await db[collection_name].find_one(sort=[(id_field, -1)])
#     return 1 if not last_doc else last_doc[id_field] + 1
