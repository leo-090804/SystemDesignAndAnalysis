from app.models import campaign
from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query, Path, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from app.database.mongodb import Database
from app.services.auth import get_current_user
from datetime import datetime, timedelta
import uuid

router = APIRouter(prefix="/items", tags=["items"])
templates = Jinja2Templates(directory="templates")

# Make sure this directory exists
# UPLOAD_DIR = "static/uploads/items"
# os.makedirs(UPLOAD_DIR, exist_ok=True)


# Middleware to check user is logged in and active
async def user_required(request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    if not user.get("is_active"):
        raise HTTPException(status_code=403, detail="Account is locked")
    return user


@router.get("/", response_class=HTMLResponse)
async def browse_items(
    request: Request,
    user: dict = Depends(user_required),
    category: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "latest",
    page: int = Query(1, ge=1),
):
    if user["role"] == "admin":
        return RedirectResponse(url="/admin/dashboard")

    db = Database.db
    limit = 12
    skip = (page - 1) * limit

    # Build query - only show approved (active) items
    # Exclude pending, rejected, pending_sale, and sold items
    query = {"status": "active"}

    # Handle category filter - convert to int only if it has a value
    if category and category.strip():
        try:
            category_int = int(category)
            query["cate_id"] = category_int
        except ValueError:
            # If category isn't a valid integer, ignore it
            pass

    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
        ]

    # Determine sort order
    sort_options = {
        "latest": [("created_at", -1)],
        "oldest": [("created_at", 1)],
        "price_low": [("price", 1)],
        "price_high": [("price", -1)],
    }
    sort_order = sort_options.get(sort_by, sort_options["latest"])

    # Get items
    items = await db.items.find(query).sort(sort_order).skip(skip).limit(limit).to_list(length=limit)
    total_items = await db.items.count_documents(query)
    total_pages = (total_items + limit - 1) // limit if total_items > 0 else 1

    # Get categories for filter dropdown
    categories = await db.categories.find({}).to_list(length=100)

    for item in items:
        campaign = await db.campaigns.find_one({"campaign_id": item.get("campaign_id")})
        if campaign:
            item["campaign_type"] = campaign.get("campaign_type")
        else:
            item["campaign_type"] = None

    return templates.TemplateResponse(
        "items/browse.html",
        {
            "request": request,
            "user": user,
            "items": items,
            "categories": categories,
            "category": category,
            "search": search,
            "sort_by": sort_by,
            "page": page,
            "total_pages": total_pages,
        },
    )


@router.get("/create", response_class=HTMLResponse)
async def create_item_form(request: Request, user: dict = Depends(user_required)):
    if user["role"] == "admin":
        raise HTTPException(status_code=403, detail="Admins cannot post items")

    db = Database.db
    categories = await db.categories.find({}).to_list(length=100)

    # Fetch active campaigns for donation items
    active_campaigns = await db.campaigns.find({"status": "active"}).to_list(length=100)

    return templates.TemplateResponse(
        "items/create.html",
        {"request": request, "user": user, "categories": categories, "active_campaigns": active_campaigns},
    )


@router.post("/create")
async def create_item(
    request: Request,
    user: dict = Depends(user_required),
    name: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    category: int = Form(...),
    transaction_type: str = Form(...),
    campaign_id: Optional[int] = Form(None),
    exchange_requirements: Optional[str] = Form(None),
    image: UploadFile = File(None),
):
    if user["role"] == "admin":
        raise HTTPException(status_code=403, detail="Admins cannot post items")

    db = Database.db

    # Get next item ID
    next_item_id = int(str(uuid.uuid4().int)[:9])

    # Create the basic item document
    new_item = {
        "name": name,
        "description": description,
        "price": price,
        "status": "pending",  # Items need admin approval
        "created_at": datetime.now().isoformat(),
        "approved_at": None,
        "rejection_reason": None,
        "item_id": next_item_id,
        "user_id": user["user_id"],
        "cate_id": category,
        "transaction_type": transaction_type,  # Save as transaction_type, not type
    }

    # Add exchange requirements if provided
    if exchange_requirements:
        new_item["exchange_requirements"] = exchange_requirements

    # Handle campaign selection
    campaign_type = None
    if transaction_type == "for_campaign" and campaign_id:
        try:
            campaign_id_int = int(campaign_id)
            # Look up the campaign to get its type
            campaign = await db.campaigns.find_one({"campaign_id": campaign_id_int})
            if campaign:
                new_item["campaign_id"] = campaign_id_int
                campaign_type = campaign.get("campaign_type")

                # For donation campaigns, create a transaction directly
                if campaign_type == "donation":
                    # Mark the item specially
                    # new_item["donated"] = True
                    new_item["status"] = "donation_pending"

                    # Create donation transaction
                    transaction_id = int(str(uuid.uuid4().int)[:9])

                    donation_transaction = {
                        "transaction_id": transaction_id,
                        "item_id": next_item_id,
                        "buyer_user_id": None,  # No buyer for donations
                        "seller_user_id": user["user_id"],
                        "transaction_type": "donation",
                        "amount": 0,  # No monetary value for item donation
                        "transaction_date": datetime.now().isoformat(),
                        "status": "pending",  # Needs admin approval
                        "status_updated_at": datetime.now().isoformat(),
                        "campaign_id": campaign_id_int,
                        "message": f"Item donation for campaign: {campaign.get('name', 'Unknown Campaign')}",
                    }

                    # Insert the transaction
                    await db.transactions.insert_one(donation_transaction)

                    # Add transaction reference to item
                    new_item["transaction_id"] = transaction_id

                    # Notify admin about the donation
                    admin_users = await db.users.find({"role": "admin"}).to_list(length=100)
                    for admin in admin_users:
                        admin_notification = {
                            "message": f"New item donation for campaign '{campaign.get('name', 'Unknown')}' requires approval.",
                            "created_at": datetime.now().isoformat(),
                            "is_read": False,
                            "is_seen": False,
                            "noti_id": int(str(uuid.uuid4().int)[:9]),
                            "user_id": admin["user_id"],
                            "related_item_id": next_item_id,
                            "related_transaction_id": transaction_id,
                        }
                        await db.notifications.insert_one(admin_notification)

                    # Create notification for the donor
                    donor_notification = {
                        "message": f"Your item '{name}' has been submitted as a donation to '{campaign.get('name', 'Unknown')}' campaign.",
                        "created_at": datetime.now().isoformat(),
                        "is_read": False,
                        "is_seen": False,
                        "noti_id": int(str(uuid.uuid4().int)[:9]),
                        "user_id": user["user_id"],
                        "related_item_id": next_item_id,
                        "related_transaction_id": transaction_id,
                    }
                    await db.notifications.insert_one(donor_notification)
        except ValueError:
            # Handle invalid campaign_id
            pass

    # Handle image upload - store directly in the items document
    if image and image.filename:
        # Read the file content
        contents = await image.read()

        # Add the image data and metadata to the item document
        new_item["image_data"] = contents
        new_item["image_content_type"] = image.content_type
        new_item["image_filename"] = image.filename

        # Create a URL path for templates to use
        new_item["image_path"] = f"/api/items/{next_item_id}/image"
    else:
        new_item["image_path"] = None

    # Insert the item into the database
    result = await db.items.insert_one(new_item)

    if result.inserted_id:
        # Send notifications to admins about the new item
        admin_users = await db.users.find({"role": "admin"}).to_list(length=100)
        for admin in admin_users:
            admin_notification = {
                "message": f"New item '{name}' posted by {user['name']} needs approval.",
                "created_at": datetime.now().isoformat(),
                "is_read": False,
                "is_seen": False,
                # "noti_id": await get_next_id(db, "notifications", "noti_id"),
                "noti_id": int(str(uuid.uuid4().int)[:9]),
                "user_id": admin["user_id"],
                "related_item_id": next_item_id,
                "related_transaction_id": None,
            }
            await db.notifications.insert_one(admin_notification)

        # Redirect to my items page
        return RedirectResponse(url="/items/my", status_code=303)
    else:
        # If insert fails, return to the form with an error
        categories = await db.categories.find({}).to_list(length=100)
        return templates.TemplateResponse(
            "items/create.html",
            {
                "request": request,
                "user": user,
                "categories": categories,
                "error": "Failed to create item. Please try again.",
            },
        )


@router.get("/my", response_class=HTMLResponse)
async def my_items(
    request: Request, user: dict = Depends(user_required), status: Optional[str] = None, page: int = Query(1, ge=1)
):
    if user["role"] == "admin":
        return RedirectResponse(url="/admin/dashboard")

    db = Database.db
    limit = 10
    skip = (page - 1) * limit

    # Build query
    query = {"user_id": user["user_id"]}
    if status:
        query["status"] = status

    # Get user's items
    items = await db.items.find(query).skip(skip).limit(limit).to_list(length=limit)
    total_items = await db.items.count_documents(query)
    total_pages = (total_items + limit - 1) // limit if total_items > 0 else 1

    for item in items:
        campaign_id = await db.campaigns.find_one({"campaign_id": item.get("campaign_id")})
        if campaign_id:
            item["campaign_type"] = campaign_id.get("campaign_type")
        else:
            item["campaign_type"] = None

    return templates.TemplateResponse(
        "items/my_items.html",
        {"request": request, "user": user, "items": items, "status": status, "page": page, "total_pages": total_pages},
    )


@router.get("/{item_id}", response_class=HTMLResponse)
async def view_item(request: Request, item_id: int = Path(...), user: dict = Depends(user_required)):
    db = Database.db
    item = await db.items.find_one({"item_id": item_id})

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Regular users should only see active items unless they're the owner
    if user["role"] != "admin" and item["status"] != "active" and item["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Item is not available")

    # Get item owner and category information
    owner = await db.users.find_one({"user_id": item["user_id"]})
    
    category = await db.categories.find_one({"cate_id": item["cate_id"]})
    
    campaign = await db.campaigns.find_one({"campaign_id": item.get("campaign_id")})
    if campaign:
        campaign_type = campaign.get("campaign_type")
        item["campaign_type"] = campaign_type

    # Only fetch related items if the current item is active
    related_items = []
    if item["status"] == "active":
        # Related items (same category, excluding current item)
        related_items = (
            await db.items.find({"cate_id": item["cate_id"], "item_id": {"$ne": item_id}, "status": "active"})
            .limit(4)
            .to_list(length=4)
        )

    return templates.TemplateResponse(
        "items/view.html",
        {
            "request": request,
            "user": user,
            "item": item,
            "owner": owner,
            "category": category,
            "related_items": related_items,
        },
    )


@router.post("/{item_id}/purchase")
async def purchase_item(item_id: int = Path(...), user: dict = Depends(user_required)):
    if user["role"] == "admin":
        raise HTTPException(status_code=403, detail="Admins cannot purchase items")

    db = Database.db

    # Find the item
    item = await db.items.find_one({"item_id": item_id})
    if not item:
        return {"success": False, "message": "Item not found"}

    # Check if item is available
    if item["status"] != "active":
        return {"success": False, "message": "Item is not available for purchase"}

    # Check if user is trying to buy their own item
    if item["user_id"] == user["user_id"]:
        return {"success": False, "message": "You cannot purchase your own item"}

    # Get seller information
    seller = await db.users.find_one({"user_id": item["user_id"]})
    if not seller:
        return {"success": False, "message": "Seller information not found"}

    try:
        # Calculate transaction expiration date (2 days from now)
        now = datetime.now()
        expiration_date = (now + timedelta(days=2)).isoformat()

        # Create transaction record
        transaction_id = int(str(uuid.uuid4().int)[:9])

        transaction = {
            "transaction_id": transaction_id,
            "transaction_type": "purchase",
            "amount": item["price"],
            "transaction_date": now.isoformat(),
            "status": "pending",
            "status_updated_at": now.isoformat(),
            "expiration_date": expiration_date,
            "cancellation_reason": None,
            "buyer_user_id": user["user_id"],
            "seller_user_id": seller["user_id"],
            "item_id": item_id,
            "campaign_id": None,
        }

        campaign_id = item.get("campaign_id")
        if campaign_id:
            transaction["campaign_id"] = campaign_id
            transaction["transaction_type"] = "donation"

        db.transactions.insert_one(transaction)

        # Update item status to pending_sale
        await db.items.update_one(
            {"item_id": item_id},
            {"$set": {"status": "pending_sale", "transaction_id": transaction_id, "buyer_user_id": user["user_id"]}},
        )

        # Create notification for seller
        seller_notification = {
            "message": f"Your item '{item['name']}' has a pending purchase from {user['name']}. Waiting for admin approval.",
            "created_at": now.isoformat(),
            "is_read": False,
            "is_seen": False,
            "noti_id": int(str(uuid.uuid4().int)[:9]),
            "user_id": seller["user_id"],
            "related_item_id": item_id,
            "related_transaction_id": transaction_id,
        }
        await db.notifications.insert_one(seller_notification)

        # Create notification for admin
        admin_users = await db.users.find({"role": "admin"}).to_list(length=100)
        for admin in admin_users:
            admin_notification = {
                "message": f"New purchase transaction: '{item['name']}' by {user['name']} needs approval.",
                "created_at": now.isoformat(),
                "is_read": False,
                "is_seen": False,
                # "noti_id": await get_next_id(db, "notifications", "noti_id"),
                "noti_id": int(str(uuid.uuid4().int)[:9]),
                "user_id": admin["user_id"],
                "related_item_id": item_id,
                "related_transaction_id": transaction_id,
                "priority": "high",  # Add priority to highlight this notification
            }
            await db.notifications.insert_one(admin_notification)

        # Create notification for buyer
        buyer_notification = {
            "message": f"Your purchase of '{item['name']}' is pending admin approval.",
            "created_at": now.isoformat(),
            "is_read": False,
            "is_seen": False,
            # "noti_id": await get_next_id(db, "notifications", "noti_id"),
            "noti_id": int(str(uuid.uuid4().int)[:9]),
            "user_id": user["user_id"],
            "related_item_id": item_id,
            "related_transaction_id": transaction_id,
        }
        await db.notifications.insert_one(buyer_notification)

        # If it's a fundraising purchase, create additional notifications
        # if transaction.get("campaign_id"):
        #     campaign = await db.campaigns.find_one({"campaign_id": transaction["campaign_id"]})
        #     if campaign:
        #         organizer_notification = {
        #             "message": f"Item '{item['name']}' has been purchased by {user['name']} for your campaign '{campaign.get('name')}'. Pending admin approval.",
        #             "created_at": now.isoformat(),
        #             "is_read": False,
        #             "is_seen": False,
        #             "noti_id": int(str(uuid.uuid4().int)[:9]),
        #             "user_id": campaign["organizer_id"],
        #             "related_item_id": item_id,
        #             "related_transaction_id": transaction_id,
        #             "priority": "high",
        #         }
        #         await db.notifications.insert_one(organizer_notification)

        #         # Also update admin notification to indicate this is a fundraising purchase
        #         for admin in admin_users:
        #             admin_notification["message"] = f"New fundraising purchase: '{item['name']}' by {user['name']} for campaign '{campaign.get('name')}'. Needs approval."
        #             await db.notifications.insert_one(admin_notification)

        return {
            "success": True,
            "message": "Purchase request submitted! Waiting for admin approval.",
            "transaction_id": transaction_id,
        }

    except Exception as e:
        print(f"Error processing purchase: {str(e)}")
        return {"success": False, "message": "An error occurred during purchase."}


@router.get("/purchased", response_class=HTMLResponse)
async def purchased_items(request: Request, user: dict = Depends(user_required), page: int = Query(1, ge=1)):
    if user["role"] == "admin":
        return RedirectResponse(url="/admin/dashboard")

    db = Database.db
    limit = 10
    skip = (page - 1) * limit

    # Find all items purchased by this user
    purchased_items = (
        await db.items.find({"status": "sold", "buyer_user_id": user["user_id"]})
        .sort("sold_at", -1)
        .skip(skip)
        .limit(limit)
        .to_list(length=limit)
    )

    total_items = await db.items.count_documents({"status": "sold", "buyer_user_id": user["user_id"]})

    total_pages = (total_items + limit - 1) // limit if total_items > 0 else 1

    # Get seller information for each item
    for item in purchased_items:
        seller = await db.users.find_one({"user_id": item["user_id"]})
        item["seller_name"] = seller.get("name", "Unknown Seller") if seller else "Unknown Seller"

    return templates.TemplateResponse(
        "items/purchased.html",
        {"request": request, "user": user, "items": purchased_items, "page": page, "total_pages": total_pages},
    )


@router.get("/{item_id}/delete")
async def delete_item(
    request: Request,
    item_id: int = Path(...),  # Make sure to define item_id as an integer
    user: dict = Depends(user_required),
):
    # Check that the user owns this item
    db = Database.db
    item = await db.items.find_one({"item_id": item_id})

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if item["user_id"] != user["user_id"] and user["role"] != "admin":
        raise HTTPException(status_code=403, detail="You don't have permission to delete this item")

    # Perform deletion
    result = await db.items.delete_one({"item_id": item_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=500, detail="Failed to delete item")

    # Redirect back to the my items page
    return RedirectResponse(url="/items/my", status_code=303)
