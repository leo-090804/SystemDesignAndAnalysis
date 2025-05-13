from app.models import campaign
from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query, Path
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from app.database.mongodb import Database
from app.services.auth import get_current_user
from datetime import datetime
import logging
import uuid
import io
import openpyxl

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)


# Middleware to check admin rights
async def admin_required(request: Request):
    user = await get_current_user(request)
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user


@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, admin: dict = Depends(admin_required)):
    # Get counts for dashboard
    db = Database.db

    # User statistics
    total_users = await db.users.count_documents({"role": {"$ne": "admin"}})
    active_users = await db.users.count_documents({"role": {"$ne": "admin"}, "is_active": 1})
    locked_users = await db.users.count_documents({"role": {"$ne": "admin"}, "is_active": 0})

    # User status breakdown for charts
    user_status = {"active": active_users, "locked": locked_users}

    # Item statistics
    total_items = await db.items.count_documents({})
    active_items = await db.items.count_documents({"status": "active"})
    pending_items_count = await db.items.count_documents({"status": "pending"})
    rejected_items = await db.items.count_documents({"status": "rejected"})
    sold_items = await db.items.count_documents({"status": "sold"})
    pending_sale_items = await db.items.count_documents({"status": "pending_sale"})
    
    # Fix: Use consistent naming for donation_pending status
    donation_pending_items = await db.items.count_documents({"status": "donation_pending"})

    # Item status breakdown for charts
    item_status = {
        "active": active_items,
        "pending": pending_items_count,
        "rejected": rejected_items,
        "sold": sold_items,
        "pending_sale": pending_sale_items,
        "donation_pending": donation_pending_items  # Use the correct variable
    }

    # Transaction statistics - Make sure these queries are running correctly
    total_transactions = await db.transactions.count_documents({})
    pending_transactions_count = await db.transactions.count_documents({"status": "pending"})
    completed_transactions = await db.transactions.count_documents({"status": "completed"})
    cancelled_transactions = await db.transactions.count_documents({"status": "cancelled"})

    # Transaction status breakdown for chart
    transaction_status = {
        "pending": pending_transactions_count,
        "completed": completed_transactions,
        "cancelled": cancelled_transactions
    }

    # Transaction types
    purchase_transactions = await db.transactions.count_documents({"transaction_type": "purchase"})
    donation_transactions = await db.transactions.count_documents({"transaction_type": "donation"})

    # Transaction type breakdown for chart
    transaction_types = {"purchase": purchase_transactions, "donation": donation_transactions}

    # Campaign statistics
    total_campaigns = await db.campaigns.count_documents({})
    active_campaigns = await db.campaigns.count_documents({"status": "active"})
    completed_campaigns = await db.campaigns.count_documents({"status": "completed"})
    cancelled_campaigns = await db.campaigns.count_documents({"status": "cancelled"})
    
    # Campagin status breakdown for chart
    campaign_status = {
        "active": active_campaigns,
        "completed": completed_campaigns,
        "cancelled": cancelled_campaigns,
    }
    
    # Campaign types
    fundraising_campaigns = await db.campaigns.count_documents({"campaign_type": "fundraising"})
    donation_campaigns = await db.campaigns.count_documents({"campaign_type": "donation"})
    exchange_campaigns = await db.campaigns.count_documents({"campaign_type": "exchange"})

    # Campagin type breakdown for chart
    campaign_types = {
        "fundraising": fundraising_campaigns,
        "donation": donation_campaigns,
        "exchange": exchange_campaigns,
    }

    # If all values are zero, add dummy values to show chart structure
    # if sum(transaction_status.values()) == 0:
    #     transaction_status = {"pending": 1, "completed": 1, "cancelled": 1}

    # if sum(campaign_types.values()) == 0:
    #     campaign_types = {"fundraising": 1, "donation": 1, "exchange": 1}

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "user": admin,
            "total_users": total_users,
            "pending_items_count": pending_items_count,
            "active_campaigns": active_campaigns,
            "pending_transactions_count": pending_transactions_count,
            "item_status": item_status,
            "user_status": user_status,
            "total_items": total_items,
            "transaction_status": transaction_status,
            "transaction_types": transaction_types,
            "campaign_status": campaign_status,
            "campaign_types": campaign_types,
            "total_transactions": total_transactions,
            "total_campaigns": total_campaigns,
        },
    )


# User Management
@router.get("/users", response_class=HTMLResponse)
async def list_users(
    request: Request,
    admin: dict = Depends(admin_required),
    role: Optional[str] = None,
    status: Optional[str] = None,  # Change from Optional[int] to Optional[str]
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
):
    db = Database.db
    limit = 10
    skip = (page - 1) * limit

    # Build query - exclude admin users from being shown in the list
    query = {"role": {"$ne": "admin"}}
    if role:
        query["role"] = role
    if status is not None and status != "all":
        try:
            status_int = int(status)
            query["is_active"] = status_int
        except ValueError:
            # If status is not a valid integer, ignore it
            pass
    if search:
        query["$or"] = [
            {"username": {"$regex": search, "$options": "i"}},
            {"name": {"$regex": search, "$options": "i"}},
        ]

    # Get users
    users = await db.users.find(query).skip(skip).limit(limit).to_list(length=limit)
    total_users = await db.users.count_documents(query)
    total_pages = (total_users + limit - 1) // limit

    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "user": admin,
            "users": users,
            "page": page,
            "total_pages": total_pages,
            "search": search,
            "role": role,
            "status": status,
        },
    )


@router.get("/users/{user_id}/edit", response_class=HTMLResponse)
async def edit_user_form(request: Request, user_id: int = Path(...), admin: dict = Depends(admin_required)):
    db = Database.db
    user_to_edit = await db.users.find_one({"user_id": user_id})

    if not user_to_edit:
        return templates.TemplateResponse(
            "admin/error.html", {"request": request, "user": admin, "message": "User not found"}
        )

    return templates.TemplateResponse(
        "admin/edit_user.html", {"request": request, "user": admin, "edit_user": user_to_edit}
    )


@router.post("/users/{user_id}/edit")
async def update_user(
    request: Request,
    user_id: int = Path(...),
    admin: dict = Depends(admin_required),
    name: str = Form(...),
    role: str = Form(...),
    grade: Optional[str] = Form(None),
    organization: Optional[str] = Form(None),
    is_active: int = Form(...),
):
    db = Database.db

    # Prepare update data
    update_data = {"name": name, "role": role, "grade": grade, "organization": organization, "is_active": is_active}

    result = await db.users.update_one({"user_id": user_id}, {"$set": update_data})

    if result.modified_count:
        return RedirectResponse(url="/admin/users", status_code=303)
    else:
        return templates.TemplateResponse(
            "admin/error.html", {"request": request, "user": admin, "message": "User update failed"}
        )


@router.post("/users/{user_id}/toggle")
async def toggle_user_status(user_id: int = Path(...), admin: dict = Depends(admin_required)):
    db = Database.db
    user_to_update = await db.users.find_one({"user_id": user_id})

    if not user_to_update:
        raise HTTPException(status_code=404, detail="User not found")

    # Toggle active status
    new_status = 0 if user_to_update.get("is_active", 1) else 1

    result = await db.users.update_one({"user_id": user_id}, {"$set": {"is_active": new_status}})

    if result.modified_count:
        return {"success": True, "is_active": new_status}
    else:
        raise HTTPException(status_code=500, detail="Failed to update user status")


@router.post("/users/{user_id}/delete")
async def delete_user(user_id: int = Path(...), admin: dict = Depends(admin_required)):
    db = Database.db

    # Check if user exists
    user_to_delete = await db.users.find_one({"user_id": user_id})
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="User not found")

    # Không cho phép admin xóa chính mình (so sánh kiểu int)
    if int(user_to_delete["user_id"]) == int(admin["user_id"]):
        logging.warning(f"Admin {admin['user_id']} attempted to delete their own account.")
        return {"success": False, "message": "You cannot delete your own account while logged in."}

    # Log lại user_id admin và user bị xóa
    logging.info(f"Admin {admin['user_id']} is deleting user {user_to_delete['user_id']} (role: {user_to_delete.get('role')})")

    # Check if user has items or transactions
    items = await db.items.find_one({"user_id": user_id})
    transactions = await db.transactions.find_one({"$or": [{"buyer_user_id": user_id}, {"seller_user_id": user_id}]})

    # If user has items or transactions, we should not delete them
    # Instead, deactivate the account
    if items or transactions:
        result = await db.users.update_one({"user_id": user_id}, {"$set": {"is_active": 0}})
        if result.modified_count:
            return {"success": True, "action": "deactivated"}
        else:
            raise HTTPException(status_code=500, detail="Failed to deactivate user")

    # If user has no items or transactions, we can safely delete them
    result = await db.users.delete_one({"user_id": user_id})
    if result.deleted_count:
        return {"success": True, "action": "deleted"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete user")


# Item Approval
@router.get("/items/pending", response_class=HTMLResponse)
async def pending_items(request: Request, admin: dict = Depends(admin_required), page: int = Query(1, ge=1)):
    db = Database.db
    limit = 10
    skip = (page - 1) * limit

    # Get pending items
    items = await db.items.find({"status": "pending"}).skip(skip).limit(limit).to_list(length=limit)
    total_items = await db.items.count_documents({"status": "pending"})
    total_pages = (total_items + limit - 1) // limit

    # Get user data for each item
    for item in items:
        user = await db.users.find_one({"user_id": item["user_id"]})
        item["user_name"] = user.get("name", "Unknown User") if user else "Unknown User"
        
        campaign = await db.campaigns.find_one({"campaign_id": item.get("campaign_id")})
        item['campaign_type'] = campaign.get("campaign_type", "Unknown") if campaign else "Unknown"

    return templates.TemplateResponse(
        "admin/pending_items.html",
        {"request": request, "user": admin, "items": items, "page": page, "total_pages": total_pages},
    )


@router.get("/items/{item_id}", response_class=HTMLResponse)
async def view_item(request: Request, item_id: int = Path(...), admin: dict = Depends(admin_required)):
    db = Database.db
    item = await db.items.find_one({"item_id": item_id})

    if not item:
        return templates.TemplateResponse(
            "admin/error.html", {"request": request, "user": admin, "message": "Item not found"}
        )

    # Get item owner information
    owner = await db.users.find_one({"user_id": item["user_id"]})
    category = await db.categories.find_one({"cate_id": item["cate_id"]})

    # Lấy danh sách transaction trao đổi
    exchange_proposals = await db.transactions.find({
        "transaction_type": "exchange_proposal",
        "item_id": item_id
    }).sort("transaction_date", -1).to_list(length=20)

    return templates.TemplateResponse(
        "admin/view_item.html", {"request": request, "user": admin, "item": item, "owner": owner, "category": category, "exchange_proposals": exchange_proposals}
    )


@router.post("/items/{item_id}/approve")
async def approve_item(item_id: int = Path(...), admin: dict = Depends(admin_required)):
    db = Database.db

    # Update item status to approved
    result = await db.items.update_one(
        {"item_id": item_id}, {"$set": {"status": "active", "approved_at": datetime.now().isoformat()}}
    )

    if result.modified_count:
        # Get item and owner details for notification
        item = await db.items.find_one({"item_id": item_id})
        if item:
            # Create notification for item owner
            notification = {
                "message": f"Your item '{item['name']}' has been approved.",
                "created_at": datetime.now().isoformat(),
                "is_read": False,
                # "noti_id": await get_next_id(db, "notifications", "noti_id"),
                "noti_id": int(str(uuid.uuid4().int)[:9]),
                "user_id": item["user_id"],
                "related_item_id": item_id,
                "related_transaction_id": None,
            }
            await db.notifications.insert_one(notification)

        return {"success": True}
    else:
        raise HTTPException(status_code=500, detail="Failed to approve item")


@router.post("/items/{item_id}/reject")
async def reject_item(item_id: int = Path(...), admin: dict = Depends(admin_required), reason: str = Form(...)):
    db = Database.db

    # Update item status to rejected
    result = await db.items.update_one(
        {"item_id": item_id}, {"$set": {"status": "rejected", "rejection_reason": reason, "rejected_at": datetime.now().isoformat()}}
    )

    if result.modified_count:
        # Get item and create notification
        item = await db.items.find_one({"item_id": item_id})
        if item:
            notification = {
                "message": f"Your item '{item['name']}' has been rejected. Reason: {reason}",
                "created_at": datetime.now().isoformat(),
                "is_read": False,
                # "noti_id": await get_next_id(db, "notifications", "noti_id")
                "noti_id": int(str(uuid.uuid4().int)[:9]),
                "user_id": item["user_id"],
                "related_item_id": item_id,
                "related_transaction_id": None,
            }
            await db.notifications.insert_one(notification)

        return {"success": True}
    else:
        raise HTTPException(status_code=500, detail="Failed to reject item")


# @router.get("/items/{item_id}/image")
# async def get_item_image(item_id: int, admin: dict = Depends(admin_required)):
#     """Serve item images directly from MongoDB"""
#     db = Database.db
    
#     # Find the item
#     item = await db.items.find_one({"item_id": item_id})
    
#     if not item or "image_data" not in item:
#         raise HTTPException(status_code=404, detail="Image not found")
    
#     # Return the image with appropriate content type
#     return Response(
#         content=item["image_data"], 
#         media_type=item.get("image_content_type", "image/jpeg")
#     )

# Campaign Management
@router.get("/campaigns", response_class=HTMLResponse)
async def list_campaigns(
    request: Request, admin: dict = Depends(admin_required), status: Optional[str] = None, page: int = Query(1, ge=1)
):
    db = Database.db
    limit = 10
    skip = (page - 1) * limit

    # Build query
    query = {}
    if status:
        query["status"] = status

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
        "admin/campaigns.html",
        {
            "request": request,
            "user": admin,
            "campaigns": campaigns,
            "page": page,
            "total_pages": total_pages,
            "status": status,
        },
    )


@router.get("/campaigns/create", response_class=HTMLResponse)
async def create_campaign_form(request: Request, admin: dict = Depends(admin_required)):
    db = Database.db

    # Get all users (not just active ones) to make sure we get some data
    users = await db.users.find({"is_active": 1}).sort("name", 1).to_list(length=100)
    users = [user for user in users if user.get("role") != "admin"]  # Exclude admin users from the dropdown

    # Log the number of users found for debugging
    logger.info(f"Found {len(users)} users for campaign organizer dropdown")

    # If no users found, check if users collection exists and has data
    if not users:
        collections = await db.list_collection_names()
        logger.info(f"Database collections: {collections}")
        if "users" in collections:
            total_users = await db.users.count_documents({})
            logger.info(f"Total users in database: {total_users}")

    return templates.TemplateResponse("admin/create_campaign.html", {"request": request, "user": admin, "users": users})


@router.post("/campaigns/create", response_class=HTMLResponse)
async def create_campaign(
    request: Request,
    admin: dict = Depends(admin_required),
    name: str = Form(...),
    description: str = Form(...),
    organizer_id: int = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    campaign_type: str = Form(...),
    goal_amount: Optional[float] = Form(None),
    goal_item: Optional[str] = Form(None),
):
    db = Database.db
    try:
        organizer = await db.users.find_one({"user_id": int(organizer_id)})
        # Xử lý goal_item rỗng hoặc không hợp lệ
        if goal_item in (None, ""): 
            goal_item = None
        else:
            try:
                goal_item = int(goal_item)
            except Exception:
                goal_item = None
        campaign = {
            "name": name,
            "description": description,
            "start_date": start_date,
            "end_date": end_date,
            "campaign_type": campaign_type,
            "current_amount": 0.0,
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "created_by": "System Administrator",
            "organizer_id": organizer["user_id"],
            "campaign_id": int(str(uuid.uuid4().int)[:9]),
        }
        if campaign_type == "fundraising":
            campaign["goal_amount"] = goal_amount
        elif campaign_type == "donation":
            campaign["goal_item"] = goal_item
        result = await db.campaigns.insert_one(campaign)
        if result.inserted_id:
            return RedirectResponse(url="/admin/campaigns", status_code=303)
        else:
            return templates.TemplateResponse(
                "admin/error.html", {"request": request, "user": admin, "message": "Failed to create campaign"}
            )
    except Exception as e:
        print(f"Error creating campaign: {str(e)}")
        return templates.TemplateResponse(
            "admin/error.html", {"request": request, "user": admin, "message": f"Error creating campaign: {str(e)}"}
        )


@router.get("/campaigns/{campaign_id}", response_class=HTMLResponse)
async def view_campaign(request: Request, campaign_id: int = Path(...), admin: dict = Depends(admin_required)):
    db = Database.db

    try:
        # Get campaign
        campaign = await db.campaigns.find_one({"campaign_id": campaign_id})
        if not campaign:
            return templates.TemplateResponse(
                "admin/error.html", {"request": request, "user": admin, "message": "Campaign not found"}
            )

        # Get organizer info (safely)
        organizer = None
        organizer_name = "Unknown"
        if "organizer_id" in campaign:
            organizer = await db.users.find_one({"user_id": campaign["organizer_id"]})
            print(f"Organizer: {organizer}")
            if organizer:
                organizer_name = organizer.get("name", "Unknown")
        # elif "organizer_name" in campaign:
        #     organizer_name = campaign["organizer_name"]

        # Get items associated with this campaign (safely)
        campaign_items = []
        try:
            # Initially search for items with this campaign ID
            campaign_items = await db.items.find({"campaign_id": campaign_id}).to_list(length=50)

            # For each item, fetch the user info and add it to the item
            for item in campaign_items:
                if "user_id" in item:
                    user = await db.users.find_one({"user_id": item["user_id"]})
                    if user:
                        item["user_name"] = user.get("name", "Unknown")
                    else:
                        item["user_name"] = "Unknown"
                
                campaign_type = await db.campaigns.find_one({"campaign_id": item.get("campaign_id")})
                if campaign_type:
                    item['campaign_type'] = campaign_type.get("campaign_type", "Unknown")
                
        except Exception as e:
            print(f"Error fetching campaign items: {str(e)}")

        # Calculate total value safely
        total_value = sum(item.get("price", 0) for item in campaign_items)

        # Handle missing fields
        # if "organizer" not in campaign:
        #     campaign["organizer"] = "Unknown"

        return templates.TemplateResponse(
            "admin/view_campaign.html",
            {
                "request": request,
                "user": admin,
                "campaign": campaign,
                "created_by": campaign.get("created_by", "System Adminístrator"),
                "organizer": organizer_name,
                "campaign_items": campaign_items,
                "total_value": total_value,
                "now": datetime.now,
            },
        )
    except Exception as e:
        print(f"Error viewing campaign: {str(e)}")
        return templates.TemplateResponse(
            "admin/error.html", {"request": request, "user": admin, "message": f"Error viewing campaign: {str(e)}"}
        )


@router.post("/campaigns/{campaign_id}/edit")
async def edit_campaign(
    request: Request,
    campaign_id: int = Path(...),
    admin: dict = Depends(admin_required),
    name: str = Form(...),
    description: str = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    goal_amount: Optional[float] = Form(None),
    goal_item: Optional[int] = Form(None),
    status: str = Form(...),
):
    db = Database.db
    try:
        update_data = {
            "name": name,
            "description": description,
            "start_date": start_date,
            "end_date": end_date,
            "status": status,
        }
        campaign = await db.campaigns.find_one({"campaign_id": campaign_id})
        if campaign and campaign.get("campaign_type") == "fundraising":
            update_data["goal_amount"] = goal_amount
            update_data["goal_item"] = None
        elif campaign and campaign.get("campaign_type") == "donation":
            update_data["goal_item"] = goal_item
            update_data["goal_amount"] = None
        result = await db.campaigns.update_one({"campaign_id": campaign_id}, {"$set": update_data})
        if result.modified_count:
            return RedirectResponse(url=f"/admin/campaigns/{campaign_id}", status_code=303)
        else:
            return templates.TemplateResponse(
                "admin/error.html",
                {"request": request, "user": admin, "message": "Failed to update campaign. Campaign may not exist."},
            )
    except Exception as e:
        print(f"Error updating campaign: {str(e)}")
        return templates.TemplateResponse(
            "admin/error.html", {"request": request, "user": admin, "message": f"Error updating campaign: {str(e)}"}
        )


# Helper function to get next ID for a collection
# async def get_next_id(db, collection_name, id_field):
#     last_doc = await db[collection_name].find_one(sort=[(id_field, -1)])
#     return 1 if not last_doc else last_doc[id_field] + 1


@router.get("/api/admin/pending-items-count")
async def get_pending_items_count(admin: dict = Depends(admin_required)):
    """API endpoint to get the count of pending items."""
    db = Database.db
    count = await db.items.count_documents({"status": "pending"})
    return {"count": count}


@router.get("/api/admin/pending-transactions-count")
async def get_pending_transactions_count(admin: dict = Depends(admin_required)):
    """API endpoint to get the count of pending transactions."""
    db = Database.db
    count = await db.transactions.count_documents({"status": "pending"})
    return {"count": count}


@router.get("/items", response_class=HTMLResponse)
async def list_items(
    request: Request,
    admin: dict = Depends(admin_required),
    status: Optional[str] = None,
    category: Optional[str] = None,  # Changed from Optional[int] to Optional[str]
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
):
    db = Database.db
    limit = 10
    skip = (page - 1) * limit

    # Build query with optional filters
    query = {}
    if status:
        query["status"] = status

    # Handle category parameter - convert to int only if not empty
    category_int = None
    if category:
        try:
            category_int = int(category)
            query["cate_id"] = category_int
        except ValueError:
            # If category can't be converted to int, ignore it
            pass

    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
        ]

    # Get items with pagination
    items = await db.items.find(query).sort([("item_id", -1)]).skip(skip).limit(limit).to_list(length=limit)
    total_items = await db.items.count_documents(query)
    total_pages = (total_items + limit - 1) // limit if total_items > 0 else 1

    # Get categories for filter dropdown
    categories = await db.categories.find({}).to_list(length=100)

    # Get user data for each item
    for item in items:
        user = await db.users.find_one({"user_id": item["user_id"]})
        item["user_name"] = user.get("name", "Unknown User") if user else "Unknown User"

        category_info = await db.categories.find_one({"cate_id": item.get("cate_id")})
        item["category_name"] = category_info.get("name", "Uncategorized") if category_info else "Uncategorized"
        
        campaign = await db.campaigns.find_one({"campaign_id": item.get("campaign_id")})
        item["campaign_type"] = campaign.get("campaign_type") if campaign else "No Campaign"

    return templates.TemplateResponse(
        "admin/items.html",
        {
            "request": request,
            "user": admin,
            "items": items,
            "page": page,
            "total_pages": total_pages,
            "status": status,
            "category": category,
            "search": search,
            "categories": categories,
        },
    )


@router.get("/users/{user_id}/profile", response_class=HTMLResponse)
async def view_user_profile(request: Request, user_id: int = Path(...), admin: dict = Depends(admin_required)):
    db = Database.db
    user_to_view = await db.users.find_one({"user_id": user_id})

    if not user_to_view:
        return templates.TemplateResponse(
            "admin/error.html", {"request": request, "user": admin, "message": "User not found"}
        )

    # Get user's items
    user_items = await db.items.find({"user_id": user_id}).sort("created_at", -1).to_list(length=100)
    for item in user_items:
        campaign = await db.campaigns.find_one({"campaign_id": item.get("campaign_id")})
        item["campaign_type"] = campaign.get("campaign_type") if campaign else "No Campaign"
        
    # Get categories for items
    categories = {}
    category_docs = await db.categories.find({}).to_list(length=100)
    for cat in category_docs:
        categories[cat["cate_id"]] = cat["name"]

    # Get user's transactions (both as buyer and seller)
    user_transactions = (
        await db.transactions.find({"$or": [{"buyer_user_id": user_id}, {"seller_user_id": user_id}]})
        .sort("transaction_date", -1)
        .to_list(length=100)
    )

    # Get campaigns the user has participated in
    user_donations = await db.transactions.find({"buyer_user_id": user_id, "transaction_type": "donation"}).to_list(
        length=100
    )

    # Get unique campaign IDs from donations
    campaign_ids = list(set(donation["campaign_id"] for donation in user_donations if "campaign_id" in donation))

    # Get campaign details
    participated_campaigns = []
    if campaign_ids:
        participated_campaigns = await db.campaigns.find({"campaign_id": {"$in": campaign_ids}}).to_list(length=100)

    # Get campaigns created by the user
    created_campaigns = await db.campaigns.find({"created_by": user_id}).to_list(length=100)

    return templates.TemplateResponse(
        "admin/user_profile.html",
        {
            "request": request,
            "user": admin,
            "profile_user": user_to_view,
            "user_items": user_items,
            "categories": categories,
            "transactions": user_transactions,
            "participated_campaigns": participated_campaigns,
            "created_campaigns": created_campaigns,
        },
    )


@router.get("/report", response_class=HTMLResponse)
async def admin_report(request: Request, admin: dict = Depends(admin_required), month: Optional[int] = None, year: Optional[int] = None):
    db = Database.db

    # Xây dựng filter cho ngày tháng
    item_date_filter = {}
    if month and year:
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        item_date_filter = {
            "created_at": {
                "$gte": start_date.isoformat(),
                "$lt": end_date.isoformat()
            }
        }

    # Tính toán các thống kê
    total_users = await db.users.count_documents({})
    total_items = await db.items.count_documents(item_date_filter)
    active_items = await db.items.count_documents({"status": "active", **item_date_filter})
    pending_items = await db.items.count_documents({"status": "pending", **item_date_filter})
    rejected_items = await db.items.count_documents({"status": "rejected", **item_date_filter})
    sold_items = await db.items.count_documents({"status": "sold", **item_date_filter})

    # Tính tổng phí giao dịch
    total_fee = 0
    exchange_items = await db.items.find({
        "transaction_type": {"$in": ["exchange", "exchange_sale"]},
        "transaction_fee": {"$exists": True},
        **item_date_filter
    }).to_list(length=None)
    for item in exchange_items:
        total_fee += item.get("transaction_fee", 0)

    # Lấy danh sách năm có dữ liệu
    years = []
    async for item in db.items.find({}, {"created_at": 1}):
        year = datetime.fromisoformat(item["created_at"]).year
        if year not in years:
            years.append(year)
    years.sort(reverse=True)

    # Thống kê theo danh mục
    categories = await db.categories.find().to_list(length=None)
    category_stats = {}
    for cat in categories:
        count = await db.items.count_documents({"cate_id": cat["cate_id"], **item_date_filter})
        category_stats[cat["name"]] = count
    # Loại hoạt động (map lại cho đúng giá trị thực tế)
    activity_type_map = {
        "sale": "Bán",
        "exchange": "Trao đổi",
        "exchange_sale": "Bán/Trao đổi",
        "for_campaign": "Gây quỹ/Quyên góp"
    }
    activity_stats = {v: 0 for v in activity_type_map.values()}
    for k, v in activity_type_map.items():
        count = await db.items.count_documents({"transaction_type": k, **item_date_filter})
        activity_stats[v] = count
    # Tỷ lệ duyệt bài
    total_posts = await db.items.count_documents(item_date_filter)
    approved_posts = await db.items.count_documents({"status": "active", **item_date_filter})
    approval_rate = round(approved_posts / total_posts * 100, 2) if total_posts else 0
    # Top người đăng tích cực
    top_users = await db.items.aggregate([
        {"$match": item_date_filter},
        {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]).to_list(length=5)
    user_names = {}
    for u in top_users:
        user = await db.users.find_one({"user_id": u["_id"]})
        user_names[u["_id"]] = user["name"] if user else str(u["_id"])
    # 2. Thống kê giao dịch
    if item_date_filter:
        completed_transactions = await db.transactions.count_documents({**item_date_filter, "status": "completed"})
        completed_value = 0
        async for t in db.transactions.find({**item_date_filter, "status": "completed"}):
            completed_value += t.get("amount", 0)
        # Giao dịch theo danh mục (fix: lấy cate_id từ items)
        category_trans_stats = {cat["name"]: 0 for cat in categories}
        async for t in db.transactions.find({**item_date_filter, "status": "completed"}):
            item = await db.items.find_one({"item_id": t["item_id"]})
            if item:
                for cat in categories:
                    if item.get("cate_id") == cat["cate_id"]:
                        category_trans_stats[cat["name"]] += 1
                        break
        # Thời gian giao dịch trung bình
        total_time = 0
        count_time = 0
        async for t in db.transactions.find({**item_date_filter, "status": "completed"}):
            item = await db.items.find_one({"item_id": t["item_id"]})
            if item and item.get("approved_at"):
                try:
                    t1 = datetime.fromisoformat(item["approved_at"])
                    t2 = datetime.fromisoformat(t["transaction_date"])
                    total_time += (t2 - t1).total_seconds()
                    count_time += 1
                except:
                    pass
        avg_time = round(total_time / count_time / 3600, 2) if count_time else 0  # giờ
    else:
        completed_transactions = await db.transactions.count_documents({"status": "completed"})
        completed_value = 0
        async for t in db.transactions.find({"status": "completed"}):
            completed_value += t.get("amount", 0)
        category_trans_stats = {cat["name"]: 0 for cat in categories}
        async for t in db.transactions.find({"status": "completed"}):
            item = await db.items.find_one({"item_id": t["item_id"]})
            if item:
                for cat in categories:
                    if item.get("cate_id") == cat["cate_id"]:
                        category_trans_stats[cat["name"]] += 1
                        break
        total_time = 0
        count_time = 0
        async for t in db.transactions.find({"status": "completed"}):
            item = await db.items.find_one({"item_id": t["item_id"]})
            if item and item.get("approved_at"):
                try:
                    t1 = datetime.fromisoformat(item["approved_at"])
                    t2 = datetime.fromisoformat(t["transaction_date"])
                    total_time += (t2 - t1).total_seconds()
                    count_time += 1
                except:
                    pass
        avg_time = round(total_time / count_time / 3600, 2) if count_time else 0
    # 3. Thống kê hoạt động gây quỹ/quyên góp
    total_campaigns = await db.campaigns.count_documents(item_date_filter)
    # Số lượng chiến dịch theo loại
    campaign_types = ["fundraising", "donation"]
    campaign_type_stats = {}
    for ctype in campaign_types:
        campaign_type_stats[ctype] = await db.campaigns.count_documents({"campaign_type": ctype, **item_date_filter})
    # Tham gia chiến dịch
    campaign_participation = await db.transactions.aggregate([
        {"$match": {"transaction_type": "donation", **item_date_filter}},
        {"$group": {"_id": "$campaign_id", "members": {"$addToSet": "$buyer_user_id"}}}
    ]).to_list(length=100)
    campaign_member_stats = {c["_id"]: len(c["members"]) for c in campaign_participation}
    # Kết quả chiến dịch (tổng tiền/quy mô đạt được)
    campaign_results = await db.transactions.aggregate([
        {"$match": {"transaction_type": "donation", **item_date_filter}},
        {"$group": {"_id": "$campaign_id", "total": {"$sum": "$amount"}}}
    ]).to_list(length=100)
    campaign_result_stats = {c["_id"]: c["total"] for c in campaign_results}
    # Hiệu quả chiến dịch (tỷ lệ hoàn thành mục tiêu)
    campaign_goal_stats = {}
    async for camp in db.campaigns.find(item_date_filter):
        cid = camp["campaign_id"]
        if camp.get("goal_amount"):
            achieved = campaign_result_stats.get(cid, 0)
            goal = camp["goal_amount"]
            campaign_goal_stats[cid] = round(achieved / goal * 100, 2) if goal else 0
    # 5. Báo cáo quỹ chung
    fundraising_total = 0
    if item_date_filter:
        total_fund = 0
        campaign_fees = 0
        sale_fees = 0
        async for t in db.transactions.find({**item_date_filter, "status": "completed"}):
            fee = t.get("fee", 0)
            total_fund += fee
            if t.get("transaction_type") == "donation":
                campaign_fees += fee
            elif t.get("transaction_type") == "purchase":
                sale_fees += fee
        # Tính tổng số tiền giao dịch trong các campaign fundraising
        async for t in db.transactions.find({**item_date_filter, "status": "completed", "transaction_type": "donation"}):
            campaign = await db.campaigns.find_one({"campaign_id": t.get("campaign_id")})
            if campaign and campaign.get("campaign_type") == "fundraising":
                fundraising_total += t.get("amount", 0)
        total_fund = total_fee + fundraising_total
    else:
        total_fund = 0
        campaign_fees = 0
        sale_fees = 0
        async for t in db.transactions.find({"status": "completed"}):
            fee = t.get("fee", 0)
            total_fund += fee
            if t.get("transaction_type") == "donation":
                campaign_fees += fee
            elif t.get("transaction_type") == "purchase":
                sale_fees += fee
        # Tính tổng số tiền giao dịch trong các campaign fundraising
        async for t in db.transactions.find({"status": "completed", "transaction_type": "donation"}):
            campaign = await db.campaigns.find_one({"campaign_id": t.get("campaign_id")})
            if campaign and campaign.get("campaign_type") == "fundraising":
                fundraising_total += t.get("amount", 0)
        total_fund = total_fee + fundraising_total
    # Lấy tên chiến dịch cho các campaign_id xuất hiện trong các bảng
    campaign_ids = set(list(campaign_member_stats.keys()) + list(campaign_result_stats.keys()) + list(campaign_goal_stats.keys()))
    campaign_names = {}
    if campaign_ids:
        async for camp in db.campaigns.find({"campaign_id": {"$in": list(campaign_ids)}}):
            campaign_names[camp["campaign_id"]] = camp.get("name", str(camp["campaign_id"]))
    # 4. Đánh giá thành viên
    # Xếp hạng thành viên
    user_rank = await db.items.aggregate([
        {"$match": item_date_filter},
        {"$group": {"_id": "$user_id", "posts": {"$sum": 1}}},
        {"$sort": {"posts": -1}},
        {"$limit": 5}
    ]).to_list(length=5)
    # Thành viên vi phạm (bị từ chối nhiều lần)
    user_violation = await db.items.aggregate([
        {"$match": {"status": "rejected", **item_date_filter}},
        {"$group": {"_id": "$user_id", "rejected": {"$sum": 1}}},
        {"$sort": {"rejected": -1}},
        {"$limit": 5}
    ]).to_list(length=5)
    # Lấy tên thành viên cho các user_id xuất hiện trong các bảng
    member_ids = set([u["_id"] for u in top_users] + [u["_id"] for u in user_violation])
    for u in top_users:
        member_ids.add(u["_id"])
    member_names = {}
    if member_ids:
        async for mem in db.users.find({"user_id": {"$in": list(member_ids)}}):
            member_names[mem["user_id"]] = mem.get("name", str(mem["user_id"]))
    # Trả về template
    return templates.TemplateResponse(
        "admin/report.html",
        {
            "request": request,
            "user": admin,
            "month": month,
            "year": year,
            "years": years,
            "category_stats": category_stats,
            "activity_stats": activity_stats,
            "approval_rate": approval_rate,
            "top_users": top_users,
            "user_names": user_names,
            "completed_transactions": completed_transactions,
            "completed_value": completed_value,
            "category_trans_stats": category_trans_stats,
            "avg_time": avg_time,
            "total_campaigns": total_campaigns,
            "campaign_type_stats": campaign_type_stats,
            "campaign_member_stats": campaign_member_stats,
            "campaign_result_stats": campaign_result_stats,
            "campaign_goal_stats": campaign_goal_stats,
            "user_rank": user_rank,
            "user_violation": user_violation,
            "total_fund": total_fund,
            "total_fee": total_fee,
            "campaign_fees": campaign_fees,
            "sale_fees": sale_fees,
            "campaign_names": campaign_names,
            "member_names": member_names,
            "fundraising_total": fundraising_total,
        },
    )


@router.get("/report/export")
async def export_report(admin: dict = Depends(admin_required), month: Optional[int] = None, year: Optional[int] = None):
    db = Database.db
    item_date_filter = {}
    if month and year:
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        item_date_filter = {
            "created_at": {
                "$gte": start_date.isoformat(),
                "$lt": end_date.isoformat()
            }
        }
    # 1. Post Statistics
    categories = await db.categories.find().to_list(length=None)
    category_stats = {}
    for cat in categories:
        count = await db.items.count_documents({"cate_id": cat["cate_id"], **item_date_filter})
        category_stats[cat["name"]] = count
    activity_type_map = {
        "sale": "Bán",
        "exchange": "Trao đổi",
        "exchange_sale": "Bán/Trao đổi",
        "for_campaign": "Gây quỹ/Quyên góp"
    }
    activity_stats = {v: 0 for v in activity_type_map.values()}
    for k, v in activity_type_map.items():
        count = await db.items.count_documents({"transaction_type": k, **item_date_filter})
        activity_stats[v] = count
    total_posts = await db.items.count_documents(item_date_filter)
    approved_posts = await db.items.count_documents({"status": "active", **item_date_filter})
    approval_rate = round(approved_posts / total_posts * 100, 2) if total_posts else 0
    top_users = await db.items.aggregate([
        {"$match": item_date_filter},
        {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]).to_list(length=5)
    user_names = {}
    for u in top_users:
        user = await db.users.find_one({"user_id": u["_id"]})
        user_names[u["_id"]] = user["name"] if user else str(u["_id"])
    # 2. Transaction Statistics
    completed_transactions = await db.transactions.count_documents({**item_date_filter, "status": "completed"})
    completed_value = 0
    async for t in db.transactions.find({**item_date_filter, "status": "completed"}):
        completed_value += t.get("amount", 0)
    category_trans_stats = {cat["name"]: 0 for cat in categories}
    async for t in db.transactions.find({**item_date_filter, "status": "completed"}):
        item = await db.items.find_one({"item_id": t["item_id"]})
        if item:
            for cat in categories:
                if item.get("cate_id") == cat["cate_id"]:
                    category_trans_stats[cat["name"]] += 1
                    break
    total_time = 0
    count_time = 0
    async for t in db.transactions.find({**item_date_filter, "status": "completed"}):
        item = await db.items.find_one({"item_id": t["item_id"]})
        if item and item.get("approved_at"):
            try:
                t1 = datetime.fromisoformat(item["approved_at"])
                t2 = datetime.fromisoformat(t["transaction_date"])
                total_time += (t2 - t1).total_seconds()
                count_time += 1
            except:
                pass
    avg_time = round(total_time / count_time / 3600, 2) if count_time else 0
    # 3. Fundraising/Donation Statistics
    total_campaigns = await db.campaigns.count_documents(item_date_filter)
    campaign_types = ["fundraising", "donation"]
    campaign_type_stats = {}
    for ctype in campaign_types:
        campaign_type_stats[ctype] = await db.campaigns.count_documents({"campaign_type": ctype, **item_date_filter})
    campaign_participation = await db.transactions.aggregate([
        {"$match": {"transaction_type": "donation", **item_date_filter}},
        {"$group": {"_id": "$campaign_id", "members": {"$addToSet": "$buyer_user_id"}}}
    ]).to_list(length=100)
    campaign_member_stats = {c["_id"]: len(c["members"]) for c in campaign_participation}
    campaign_results = await db.transactions.aggregate([
        {"$match": {"transaction_type": "donation", **item_date_filter}},
        {"$group": {"_id": "$campaign_id", "total": {"$sum": "$amount"}}}
    ]).to_list(length=100)
    campaign_result_stats = {c["_id"]: c["total"] for c in campaign_results}
    campaign_goal_stats = {}
    async for camp in db.campaigns.find(item_date_filter):
        cid = camp["campaign_id"]
        if camp.get("goal_amount"):
            achieved = campaign_result_stats.get(cid, 0)
            goal = camp["goal_amount"]
            campaign_goal_stats[cid] = round(achieved / goal * 100, 2) if goal else 0
    campaign_names = {}
    campaign_ids = set(list(campaign_member_stats.keys()) + list(campaign_result_stats.keys()) + list(campaign_goal_stats.keys()))
    if campaign_ids:
        async for camp in db.campaigns.find({"campaign_id": {"$in": list(campaign_ids)}}):
            campaign_names[camp["campaign_id"]] = camp.get("name", str(camp["campaign_id"]))
    # 4. Member Evaluation
    user_rank = await db.items.aggregate([
        {"$match": item_date_filter},
        {"$group": {"_id": "$user_id", "posts": {"$sum": 1}}},
        {"$sort": {"posts": -1}},
        {"$limit": 5}
    ]).to_list(length=5)
    user_violation = await db.items.aggregate([
        {"$match": {"status": "rejected", **item_date_filter}},
        {"$group": {"_id": "$user_id", "rejected": {"$sum": 1}}},
        {"$sort": {"rejected": -1}},
        {"$limit": 5}
    ]).to_list(length=5)
    member_ids = set([u["_id"] for u in user_rank] + [u["_id"] for u in user_violation])
    member_names = {}
    if member_ids:
        async for mem in db.users.find({"user_id": {"$in": list(member_ids)}}):
            member_names[mem["user_id"]] = mem.get("name", str(mem["user_id"]))
    # 5. Common Fund
    total_fee = 0
    exchange_items = await db.items.find({
        "transaction_type": {"$in": ["exchange", "exchange_sale"]},
        "transaction_fee": {"$exists": True},
        **item_date_filter
    }).to_list(length=None)
    for item in exchange_items:
        total_fee += item.get("transaction_fee", 0)
    fundraising_total = 0
    async for t in db.transactions.find({**item_date_filter, "status": "completed", "transaction_type": "donation"}):
        campaign = await db.campaigns.find_one({"campaign_id": t.get("campaign_id")})
        if campaign and campaign.get("campaign_type") == "fundraising":
            fundraising_total += t.get("amount", 0)
    total_fund = total_fee + fundraising_total
    # Tạo workbook Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Report"
    # 1. Post Statistics
    ws.append(["1. Post Statistics"])
    ws.append(["Post Categories:"])
    ws.append(["Category", "Count"])
    for cat, count in category_stats.items():
        ws.append([cat, count])
    ws.append([])
    ws.append(["Activity Types:"])
    ws.append(["Type", "Count"])
    for act, count in activity_stats.items():
        ws.append([act, count])
    ws.append([])
    ws.append(["Approval Rate:", f"{approval_rate}%"])
    ws.append([])
    ws.append(["Top Active Members:"])
    ws.append(["Member", "Posts"])
    for u in top_users:
        ws.append([user_names.get(u["_id"], u["_id"]), u["count"]])
    ws.append([])
    # 2. Transaction Statistics
    ws.append(["2. Transaction Statistics"])
    ws.append(["Completed Transactions:", completed_transactions])
    ws.append(["Total Transaction Value:", f"{completed_value:,} VNĐ"])
    ws.append([])
    ws.append(["Transactions by Category:"])
    ws.append(["Category", "Count"])
    for cat, count in category_trans_stats.items():
        ws.append([cat, count])
    ws.append([])
    ws.append(["Average Transaction Time:", f"{avg_time} hours"])
    ws.append([])
    # 3. Fundraising/Donation Statistics
    ws.append(["3. Fundraising/Donation Statistics"])
    ws.append(["Total Campaigns:", total_campaigns])
    ws.append([])
    ws.append(["Campaigns by Type:"])
    ws.append(["Type", "Count"])
    for ctype, count in campaign_type_stats.items():
        ws.append([ctype, count])
    ws.append([])
    ws.append(["Campaign Participation (Member Count):"])
    ws.append(["Campaign ID", "Campaign Name", "Members"])
    if campaign_member_stats:
        for cid, mem in campaign_member_stats.items():
            ws.append([cid, campaign_names.get(cid, ''), mem])
    else:
        ws.append(["", "", ""])
    ws.append([])
    ws.append(["Campaign Results (Total Value):"])
    ws.append(["Campaign ID", "Campaign Name", "Total Value (VNĐ)"])
    if campaign_result_stats:
        for cid, val in campaign_result_stats.items():
            ws.append([cid, campaign_names.get(cid, ''), val])
    else:
        ws.append(["", "", ""])
    ws.append([])
    ws.append(["Campaign Effectiveness (Goal Completion Rate):"])
    ws.append(["Campaign ID", "Campaign Name", "Rate (%)"])
    if campaign_goal_stats:
        for cid, rate in campaign_goal_stats.items():
            ws.append([cid, campaign_names.get(cid, ''), rate])
    else:
        ws.append(["", "", ""])
    ws.append([])
    # 4. Member Evaluation
    ws.append(["4. Member Evaluation"])
    ws.append(["Member Rankings (Top Posters):"])
    ws.append(["Member", "Member Name", "Posts"])
    if user_rank:
        for u in user_rank:
            ws.append([u["_id"], member_names.get(u["_id"], ''), u["posts"]])
    else:
        ws.append(["", "", ""])
    ws.append([])
    ws.append(["Members with Violations (Most Rejections):"])
    ws.append(["Member", "Member Name", "Rejections"])
    if user_violation:
        for u in user_violation:
            ws.append([u["_id"], member_names.get(u["_id"], ''), u["rejected"]])
    else:
        ws.append(["", "", ""])
    ws.append([])
    # 5. Common Fund Report
    ws.append(["5. Common Fund Report"])
    ws.append(["Fund from Exchange Transaction Fees:", f"{total_fee:,} VNĐ"])
    ws.append(["Fund from Fundraising Campaigns:", f"{fundraising_total:,} VNĐ"])
    ws.append(["Total Fund:", f"{total_fund:,} VNĐ"])
    # Xuất file
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    filename = f"report_{month or 'all'}_{year or 'all'}.xlsx"
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename={filename}"})


@router.get("/users/{user_id}/report")
async def user_personal_report(user_id: int, admin: dict = Depends(admin_required)):
    db = Database.db
    user = await db.users.find_one({"user_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # 1. Sản phẩm đã đăng
    total_items = await db.items.count_documents({"user_id": user_id})
    pending_items = await db.items.count_documents({"user_id": user_id, "status": "pending"})
    approved_items = await db.items.count_documents({"user_id": user_id, "status": "active"})
    rejected_items = await db.items.count_documents({"user_id": user_id, "status": "rejected"})
    sold_items = await db.items.count_documents({"user_id": user_id, "status": {"$in": ["sold", "exchanged"]}})
    # Lý do từ chối
    rejected_list = await db.items.find({"user_id": user_id, "status": "rejected"}).to_list(length=20)
    # 2. Giao dịch đã thực hiện
    buy_count = await db.transactions.count_documents({"buyer_user_id": user_id, "transaction_type": "purchase"})
    exchange_count = await db.transactions.count_documents({"buyer_user_id": user_id, "transaction_type": "exchange"})
    donation_count = await db.transactions.count_documents({"buyer_user_id": user_id, "transaction_type": "donation"})
    # Tổng tiền đã chi (mua + trao đổi)
    total_spent = 0
    async for t in db.transactions.find({"buyer_user_id": user_id, "transaction_type": {"$in": ["purchase", "exchange"]}}):
        total_spent += t.get("amount", 0)
    # Tổng phí đóng góp từ trao đổi
    total_fee = 0
    async for t in db.transactions.find({"buyer_user_id": user_id, "transaction_type": "exchange"}):
        total_fee += t.get("fee", 0)
    # 3. Hoạt động đã tham gia (quyên góp/gây quỹ)
    user_donations = await db.transactions.find({"buyer_user_id": user_id, "transaction_type": "donation"}).to_list(length=100)
    campaign_ids = list(set(donation["campaign_id"] for donation in user_donations if "campaign_id" in donation))
    participated_campaigns = []
    if campaign_ids:
        participated_campaigns = await db.campaigns.find({"campaign_id": {"$in": campaign_ids}}).to_list(length=100)
    # Thống kê loại hoạt động
    fundraising_count = sum(1 for c in participated_campaigns if c.get("campaign_type") == "fundraising")
    donation_campaign_count = sum(1 for c in participated_campaigns if c.get("campaign_type") == "donation")
    # 4. Tổng đóng góp quỹ chung (từ phí trao đổi)
    # Đã tính ở trên: total_fee
    # 5. Thời gian hoạt động
    registered_at = user.get("created_at")
    first_item = await db.items.find({"user_id": user_id}).sort("created_at", 1).to_list(length=1)
    first_transaction = await db.transactions.find({"buyer_user_id": user_id}).sort("transaction_date", 1).to_list(length=1)
    last_item = await db.items.find({"user_id": user_id}).sort("created_at", -1).to_list(length=1)
    # 6. Hiệu quả hoạt động
    approve_rate = round(approved_items / total_items * 100, 2) if total_items else 0
    # Xuất file Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Personal Report"
    ws.append([f"Personal Report for {user.get('name', user_id)} (User ID: {user_id})"])
    ws.append([])
    # 1. Sản phẩm đã đăng
    ws.append(["1. Product Statistics"])
    ws.append([f"You have posted {total_items} products:"])
    ws.append(["Pending Approval", pending_items])
    ws.append(["Approved", approved_items])
    ws.append(["Rejected", rejected_items])
    ws.append(["Sold/Exchanged", sold_items])
    ws.append([])
    ws.append(["Rejected Products (with reason):"])
    ws.append(["Product Name", "Rejection Reason"])
    if rejected_list:
        for item in rejected_list:
            ws.append([item.get("name", ""), item.get("rejection_reason", "")])
    else:
        ws.append(["", ""])
    ws.append([])
    # 2. Giao dịch đã thực hiện
    ws.append(["2. Transaction Statistics"])
    total_transactions = buy_count + exchange_count + donation_count
    ws.append([f"You have participated in {total_transactions} transactions:"])
    ws.append(["Purchase", buy_count])
    ws.append(["Exchange", exchange_count])
    ws.append(["Donation", donation_count])
    ws.append(["Total Spent (Purchase + Exchange)", f"{total_spent:,} VNĐ"])
    ws.append(["Total Exchange Fee Contributed", f"{total_fee:,} VNĐ"])
    ws.append([])
    # 3. Activities Participated
    ws.append(["3. Activities Participated"])
    total_activities = fundraising_count + donation_campaign_count
    ws.append([f"You have participated in {total_activities} activities:"])
    ws.append(["Fundraising Campaigns", fundraising_count])
    ws.append(["Donation Campaigns", donation_campaign_count])
    ws.append(["Campaign Name", "Type", "Start Date", "End Date"])
    if participated_campaigns:
        for c in participated_campaigns:
            ws.append([
                c.get("name", ""),
                c.get("campaign_type", ""),
                c.get("start_date", ""),
                c.get("end_date", "")
            ])
    else:
        ws.append(["", "", "", ""])
    ws.append([])
    # 4. Fund Contribution
    ws.append(["4. Fund Contribution"])
    ws.append([f"You have contributed {total_fee:,} VNĐ to the common fund through {exchange_count} exchange transactions."])
    ws.append([])
    # 5. Activity Timeline
    ws.append(["5. Activity Timeline"])
    ws.append(["Registered At", registered_at or "N/A"])
    ws.append(["First Product Posted At", first_item[0]["created_at"] if first_item else "N/A"])
    ws.append(["First Transaction At", first_transaction[0]["transaction_date"] if first_transaction else "N/A"])
    ws.append(["Last Product Posted At", last_item[0]["created_at"] if last_item else "N/A"])
    ws.append([])
    # 6. Activity Effectiveness
    ws.append(["6. Activity Effectiveness"])
    ws.append(["Product Approval Rate", f"{approve_rate}%"])
    # Xuất file
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    filename = f"user_report_{user_id}.xlsx"
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename={filename}"})


@router.get("/dashboard", response_class=HTMLResponse)
async def user_dashboard(request: Request, user: dict = Depends(get_current_user)):
    db = Database.db
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    user_id = user["user_id"]
    # 1. Sản phẩm đã đăng
    total_items = await db.items.count_documents({"user_id": user_id})
    pending_items = await db.items.count_documents({"user_id": user_id, "status": "pending"})
    approved_items = await db.items.count_documents({"user_id": user_id, "status": "active"})
    rejected_items = await db.items.count_documents({"user_id": user_id, "status": "rejected"})
    sold_items = await db.items.count_documents({"user_id": user_id, "status": {"$in": ["sold", "exchanged"]}})
    # 2. Giao dịch đã thực hiện
    buy_count = await db.transactions.count_documents({"buyer_user_id": user_id, "transaction_type": "purchase"})
    exchange_count = await db.transactions.count_documents({"buyer_user_id": user_id, "transaction_type": "exchange"})
    donation_count = await db.transactions.count_documents({"buyer_user_id": user_id, "transaction_type": "donation"})
    # Tổng tiền đã chi (mua + trao đổi)
    total_spent = 0
    async for t in db.transactions.find({"buyer_user_id": user_id, "transaction_type": {"$in": ["purchase", "exchange"]}}):
        total_spent += t.get("amount", 0)
    total_fee = 0
    async for t in db.transactions.find({"buyer_user_id": user_id, "transaction_type": "exchange"}):
        total_fee += t.get("fee", 0)
    # 3. Hoạt động đã tham gia
    user_donations = await db.transactions.find({"buyer_user_id": user_id, "transaction_type": "donation"}).to_list(length=100)
    campaign_ids = list(set(donation["campaign_id"] for donation in user_donations if "campaign_id" in donation))
    participated_campaigns = []
    if campaign_ids:
        participated_campaigns = await db.campaigns.find({"campaign_id": {"$in": campaign_ids}}).to_list(length=100)
    fundraising_count = sum(1 for c in participated_campaigns if c.get("campaign_type") == "fundraising")
    donation_campaign_count = sum(1 for c in participated_campaigns if c.get("campaign_type") == "donation")
    total_activities = fundraising_count + donation_campaign_count
    # 4. Thời gian hoạt động
    registered_at = user.get("created_at")
    first_item = await db.items.find({"user_id": user_id}).sort("created_at", 1).to_list(length=1)
    first_transaction = await db.transactions.find({"buyer_user_id": user_id}).sort("transaction_date", 1).to_list(length=1)
    last_item = await db.items.find({"user_id": user_id}).sort("created_at", -1).to_list(length=1)
    # 5. Hiệu quả hoạt động
    approve_rate = round(approved_items / total_items * 100, 2) if total_items else 0
    personal_report = {
        "total_items": total_items,
        "pending_items": pending_items,
        "approved_items": approved_items,
        "rejected_items": rejected_items,
        "sold_items": sold_items,
        "buy_count": buy_count,
        "exchange_count": exchange_count,
        "donation_count": donation_count,
        "total_transactions": buy_count + exchange_count + donation_count,
        "total_spent": total_spent,
        "total_fee": total_fee,
        "fundraising_count": fundraising_count,
        "donation_campaign_count": donation_campaign_count,
        "total_activities": total_activities,
        "registered_at": registered_at,
        "first_item": first_item[0]["created_at"] if first_item else None,
        "first_transaction": first_transaction[0]["transaction_date"] if first_transaction else None,
        "last_item": last_item[0]["created_at"] if last_item else None,
        "approve_rate": approve_rate,
    }
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user": user, "personal_report": personal_report}
    )
