from re import A
from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query, Path, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from app.database.mongodb import Database
from app.services.auth import get_current_user
from datetime import datetime, timedelta
import os
import shutil
import uuid

router = APIRouter(prefix="/items", tags=["items"])
templates = Jinja2Templates(directory="templates")

# Make sure this directory exists
UPLOAD_DIR = "static/uploads/items"
os.makedirs(UPLOAD_DIR, exist_ok=True)


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
    category: Optional[int] = None,
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

    if category:
        query["cate_id"] = category
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

    return templates.TemplateResponse("items/create.html", {"request": request, "user": user, "categories": categories})


@router.post("/create")
async def create_item(
    request: Request,
    user: dict = Depends(user_required),
    name: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    category: int = Form(...),
    image: UploadFile = File(None),
):
    if user["role"] == "admin":
        raise HTTPException(status_code=403, detail="Admins cannot post items")

    db = Database.db

    # Get next item ID
    last_item = await db.items.find_one(sort=[("item_id", -1)])
    # next_item_id = 1 if not last_item else last_item["item_id"] + 1
    next_item_id = uuid.uuid4().int

    # Handle image upload if provided
    image_path = None
    if image and image.filename:
        # Generate unique filename
        file_ext = os.path.splitext(image.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)

        # Save the file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)

        # Store the relative path
        image_path = f"/static/uploads/items/{unique_filename}"

    # Create item
    new_item = {
        "name": name,
        "description": description,
        "image_path": image_path,
        "price": price,
        "status": "pending",  # Items need admin approval
        "created_at": datetime.now().isoformat(),
        "approved_at": None,
        "rejection_reason": None,
        "item_id": next_item_id,
        "user_id": user["user_id"],
        "cate_id": category,
    }

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
                "noti_id": uuid.uuid4().int,
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
        # transaction_id = await get_next_id(db, "transactions", "transaction_id")
        transaction_id = uuid.uuid4().int

        transaction = {
            "transaction_id": transaction_id,
            "transaction_type": "purchase",
            "amount": item["price"],
            "transaction_date": now.isoformat(),
            "status": "pending",  # Changed from "processing" to "pending"
            "status_updated_at": now.isoformat(),
            "expiration_date": expiration_date,
            "cancellation_reason": None,
            "buyer_user_id": user["user_id"],
            "seller_user_id": seller["user_id"],
            "item_id": item_id,
            "campaign_id": None,
        }

        await db.transactions.insert_one(transaction)

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
            # "noti_id": await get_next_id(db, "notifications", "noti_id"),
            "noti_id": uuid.uuid4().int,
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
                "noti_id": uuid.uuid4().int,
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
            "noti_id": uuid.uuid4().int,
            "user_id": user["user_id"],
            "related_item_id": item_id,
            "related_transaction_id": transaction_id,
        }
        await db.notifications.insert_one(buyer_notification)

        return {
            "success": True,
            "message": "Purchase request submitted! Waiting for admin approval.",
            "transaction_id": transaction_id,
        }
    except Exception as e:
        print(f"Error processing purchase: {str(e)}")
        return {"success": False, "message": "An error occurred during purchase."}


# Helper function to get next ID if not already defined
# async def get_next_id(db, collection_name, id_field):
#     last_doc = await db[collection_name].find_one(sort=[(id_field, -1)])
#     return 1 if not last_doc else last_doc[id_field] + 1


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
