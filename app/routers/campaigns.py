import uuid
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
        
    try:
        # Validate amount
        if amount <= 0:
            return {"success": False, "message": "Donation amount must be greater than zero"}
        
        # Get campaign
        campaign = await db.campaigns.find_one({"campaign_id": campaign_id})
        if not campaign:
            return {"success": False, "message": "Campaign not found"}
        
        if campaign["status"] != "active":
            return {"success": False, "message": "This campaign is no longer active"}
        
        # Check for duplicate donations (transactions) in the last 30 seconds
        # time_threshold = (datetime.now() - timedelta(seconds=30)).isoformat()
        # recent_transaction = await db.transactions.find_one({
        #     "transaction_type": "donation",
        #     "buyer_user_id": user["user_id"],
        #     "campaign_id": campaign_id,
        #     "amount": amount,
        #     "transaction_date": {"$gt": time_threshold}
        # })
        
        # if recent_transaction:
        #     logger.info(f"Prevented duplicate donation from user {user['user_id']} to campaign {campaign_id}")
        #     return {
        #         "success": True,
        #         "message": "Your donation was already processed",
        #         "new_amount": campaign.get("current_amount", 0),
        #         "goal_amount": campaign.get("goal_amount")
        #     }
            
        # Create transaction record with current timestamp
        current_time = datetime.now().isoformat()
        # transaction_id = await get_next_id(db, "transactions", "transaction_id")
        transaction_id = uuid.uuid4().int()
        
        transaction = {
            "transaction_id": transaction_id,
            "transaction_type": "donation",
            "amount": amount,
            "transaction_date": current_time,
            "status": "pending",  # Changed from "completed" to "pending"
            "status_updated_at": current_time,
            "cancellation_reason": None,
            "buyer_user_id": user["user_id"],
            "seller_user_id": None,  # No seller for donations
            "item_id": None,  # No item for donations
            "campaign_id": campaign_id,
            "message": message
        }
        
        # Use transaction ID as a unique identifier
        donation_id = f"{user['user_id']}-{campaign_id}-{transaction_id}"
        transaction["donation_id"] = donation_id
        
        await db.transactions.insert_one(transaction)
        
        # Don't update campaign amount yet - wait for admin approval
        
        # Create notification for campaign creator
        # creator_notification = {
        #     "message": f"New donation of ${amount:.2f} for campaign '{campaign['name']}' is waiting for admin approval.",
        #     "created_at": current_time,
        #     "is_read": False,
        #     "is_seen": False,
        #     "noti_id": await get_next_id(db, "notifications", "noti_id"),
        #     "user_id": campaign["created_by"],
        #     "related_item_id": None,
        #     "related_transaction_id": transaction_id,
        #     "donation_id": donation_id
        # }
        # await db.notifications.insert_one(creator_notification)
        
        # Create notification for donor
        donor_notification = {
            "message": f"Your donation of ${amount:.2f} to '{campaign['name']}' is pending admin approval.",
            "created_at": current_time,
            "is_read": False,
            "is_seen": False,
            "noti_id": await get_next_id(db, "notifications", "noti_id"),
            "user_id": user["user_id"],
            "related_item_id": None,
            "related_transaction_id": transaction_id,
            "donation_id": donation_id
        }
        await db.notifications.insert_one(donor_notification)
        
        # Create notification for admins
        admin_users = await db.users.find({"role": "admin"}).to_list(length=100)
        for admin in admin_users:
            admin_notification = {
                "message": f"New donation of ${amount:.2f} by {user['name']} for campaign '{campaign['name']}' needs approval.",
                "created_at": current_time,
                "is_read": False,
                "is_seen": False,
                "noti_id": await get_next_id(db, "notifications", "noti_id"),
                "user_id": admin["user_id"],
                "related_item_id": None,
                "related_transaction_id": transaction_id,
                "donation_id": donation_id,
                "priority": "high"  # Add priority to highlight this notification
            }
            await db.notifications.insert_one(admin_notification)
        
        return {
            "success": True, 
            "message": "Donation submitted successfully. Waiting for admin approval.",
            "transaction_id": transaction_id
        }
        
    except Exception as e:
        logger.error(f"Error processing donation: {str(e)}")
        return {"success": False, "message": f"An error occurred while processing your donation"}

# Helper function to get next ID - if not already defined elsewhere
# async def get_next_id(db, collection_name, id_field):
#     last_doc = await db[collection_name].find_one(sort=[(id_field, -1)])
#     return 1 if not last_doc else last_doc[id_field] + 1
