from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query, Path
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from app.database.mongodb import Database
from app.services.auth import get_current_user
from datetime import datetime
import logging
import uuid

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

    # Item status breakdown for charts
    item_status = {
        "active": active_items,
        "pending": pending_items_count,
        "rejected": rejected_items,
        "sold": sold_items,
        "pending_sale": pending_sale_items,
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

    return templates.TemplateResponse(
        "admin/view_item.html", {"request": request, "user": admin, "item": item, "owner": owner, "category": category}
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
                "noti_id": str(uuid.uuid4().int),
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
        {"item_id": item_id}, {"$set": {"status": "rejected", "rejection_reason": reason}}
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
    organizer_id: int = Form(...),  # Changed from organizer text to organizer_id
    start_date: str = Form(...),
    end_date: str = Form(...),
    campaign_type: str = Form(...),
    goal_amount: Optional[float] = Form(None),
):
    db = Database.db

    try:
        # Validate the organizer exists
        organizer = await db.users.find_one({"user_id": int(organizer_id)})
        if not organizer:
            users = await db.users.find({"is_active": True}).sort("name", 1).to_list(length=100)
            return templates.TemplateResponse(
                "admin/create_campaign.html",
                {"request": request, "user": admin, "users": users, "error": "Selected organizer not found"},
            )

        # Continue with campaign creation using the organizer information
        # ...existing code...

        campaign = {
            "name": name,
            "description": description,
            "start_date": start_date,
            "end_date": end_date,
            "campaign_type": campaign_type,
            "goal_amount": goal_amount,
            "current_amount": 0.0,
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "created_by": organizer["user_id"],
            "organizer_name": organizer["name"],
            # "campaign_id": await get_next_id(db, "campaigns", "campaign_id")
            "campaign_id": int(str(uuid.uuid4().int)[:9]),
        }

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

        # Get creator info (safely)
        creator = None
        if "created_by" in campaign:
            creator = await db.users.find_one({"user_id": campaign["created_by"]})

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
        except Exception as e:
            print(f"Error fetching campaign items: {str(e)}")

        # Calculate total value safely
        total_value = sum(item.get("price", 0) for item in campaign_items)

        # Handle missing fields
        if "organizer" not in campaign:
            campaign["organizer"] = "Unknown"

        return templates.TemplateResponse(
            "admin/view_campaign.html",
            {
                "request": request,
                "user": admin,
                "campaign": campaign,
                "creator": creator,
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
    organizer: str = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    goal_amount: Optional[float] = Form(None),
    status: str = Form(...),
):
    db = Database.db

    try:
        # Update campaign with new data
        update_data = {
            "name": name,
            "description": description,
            "organizer": organizer,
            "start_date": start_date,
            "end_date": end_date,
            "goal_amount": goal_amount,
            "status": status,
        }

        result = await db.campaigns.update_one({"campaign_id": campaign_id}, {"$set": update_data})

        if result.modified_count:
            # Create notification about campaign update
            # (We'll implement notifications in a future update)

            # Redirect to the campaign view
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
