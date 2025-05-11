from app.models import campaign
from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query, Path, UploadFile, File, status as http_status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from app.database.mongodb import Database
from app.services.auth import get_current_user
from datetime import datetime, timedelta
import uuid
import base64

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
            item['campaign_type'] = campaign.get("campaign_type")
        else:
            item['campaign_type'] = None
        
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
        {
            "request": request, 
            "user": user, 
            "categories": categories,
            "active_campaigns": active_campaigns
        }
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
    campaign_id: Optional[str] = Form(None),
    exchange_requirements: Optional[str] = Form(None),
    transaction_fee: Optional[float] = Form(None),
    image: UploadFile = File(None),
):
    if user["role"] == "admin":
        raise HTTPException(status_code=403, detail="Admins cannot post items")

    db = Database.db

    # Get next item ID
    next_item_id = int(str(uuid.uuid4().int)[:9])

    # Xử lý campaign_id rỗng hoặc không hợp lệ
    if campaign_id in (None, ""): 
        campaign_id = None
    else:
        try:
            campaign_id = int(campaign_id)
        except Exception:
            campaign_id = None

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

    # Add transaction fee if provided and transaction type is exchange
    if transaction_fee and transaction_type in ['exchange', 'exchange_sale']:
        new_item["transaction_fee"] = transaction_fee

    # Handle campaign selection
    campaign_type = None
    if transaction_type == "for_campaign" and campaign_id:
        try:
            # Look up the campaign to get its type
            campaign = await db.campaigns.find_one({"campaign_id": campaign_id})
            if campaign:
                new_item["campaign_id"] = campaign_id
                campaign_type = campaign.get("campaign_type")
                
                # For donation campaigns, create a transaction directly
                if campaign_type == "donation":
                    # Mark the item specially
                    new_item["donated"] = True
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
                        "campaign_id": campaign_id,
                        "message": f"Item donation for campaign: {campaign.get('name', 'Unknown Campaign')}"
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
            item['campaign_type'] = campaign_id.get("campaign_type")
        else:
            item['campaign_type'] = None

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

    # Nếu là chủ sở hữu, lấy danh sách đề xuất trao đổi
    exchange_proposals = []
    if user["user_id"] == item["user_id"]:
        exchange_proposals = await db.transactions.find({
            "transaction_type": "exchange_proposal",
            "item_id": item_id
        }).sort("transaction_date", -1).to_list(length=20)

    return templates.TemplateResponse(
        "items/view.html",
        {
            "request": request,
            "user": user,
            "item": item,
            "owner": owner,
            "category": category,
            "related_items": related_items,
            "exchange_proposals": exchange_proposals,
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


@router.post("/{item_id}/delete")
async def delete_item(item_id: int = Path(...), user: dict = Depends(user_required)):
    db = Database.db
    item = await db.items.find_one({"item_id": item_id})
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="You do not have permission to delete this item")
    if item["status"] in ["sold", "pending_sale", "donation_pending"]:
        raise HTTPException(status_code=400, detail="Cannot delete item with active or completed transaction")
    # Xóa item
    result = await db.items.delete_one({"item_id": item_id})
    if result.deleted_count:
        # Nếu item đã được duyệt (status == 'active'), gửi thông báo cho admin
        if item["status"] == "active":
            admin_users = await db.users.find({"role": "admin"}).to_list(length=100)
            for admin in admin_users:
                admin_notification = {
                    "message": f"User '{user['name']}' has deleted an approved item: '{item['name']}' (ID: {item_id})!",
                    "created_at": datetime.now().isoformat(),
                    "is_read": False,
                    "is_seen": False,
                    "noti_id": int(str(uuid.uuid4().int)[:9]),
                    "user_id": admin["user_id"],
                    "related_item_id": item_id,
                    "related_transaction_id": None,
                }
                await db.notifications.insert_one(admin_notification)
        return {"success": True}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete item")


@router.post("/{item_id}/exchange-proposal")
async def exchange_proposal(
    item_id: int,
    request: Request,
    user: dict = Depends(user_required),
    your_item_name: str = Form(...),
    your_item_condition: str = Form(...),
    message: str = Form(None),
    your_item_image: UploadFile = File(None),
):
    db = Database.db
    item = await db.items.find_one({"item_id": item_id})
    if not item or item["status"] != "active":
        raise HTTPException(status_code=404, detail="Item not found or not active")
    if user["user_id"] == item["user_id"]:
        raise HTTPException(status_code=400, detail="You cannot propose exchange for your own item")
    # Lưu hình ảnh sản phẩm Y nếu có
    image_data = None
    image_content_type = None
    image_filename = None
    if your_item_image and your_item_image.filename:
        image_data = await your_item_image.read()
        image_content_type = your_item_image.content_type
        image_filename = your_item_image.filename
    # Tạo transaction đề xuất trao đổi
    transaction_id = int(str(uuid.uuid4().int)[:9])
    transaction = {
        "transaction_id": transaction_id,
        "transaction_type": "exchange_proposal",
        "item_id": item_id,
        "buyer_user_id": user["user_id"],
        "seller_user_id": item["user_id"],
        "proposal": {
            "your_item_name": your_item_name,
            "your_item_condition": your_item_condition,
            "message": message,
            "image_data": image_data,
            "image_content_type": image_content_type,
            "image_filename": image_filename,
        },
        "transaction_date": datetime.now().isoformat(),
        "status": "pending",
        "status_updated_at": datetime.now().isoformat(),
    }
    # Thêm transaction_fee nếu item có
    if item.get("transaction_fee"):
        transaction["transaction_fee"] = item["transaction_fee"]
    await db.transactions.insert_one(transaction)
    # Gửi thông báo cho chủ sở hữu sản phẩm
    admin_notification = {
        "message": f"You have received an exchange proposal for item '{item['name']}' from {user['name']}",
        "created_at": datetime.now().isoformat(),
        "is_read": False,
        "is_seen": False,
        "noti_id": int(str(uuid.uuid4().int)[:9]),
        "user_id": item["user_id"],
        "related_item_id": item_id,
        "related_transaction_id": transaction_id,
    }
    await db.notifications.insert_one(admin_notification)
    # Gửi thông báo cho tất cả admin
    admin_users = await db.users.find({"role": "admin"}).to_list(length=100)
    for admin in admin_users:
        noti = {
            "message": f"New exchange proposal for item '{item['name']}' from {user['name']}",
            "created_at": datetime.now().isoformat(),
            "is_read": False,
            "is_seen": False,
            "noti_id": int(str(uuid.uuid4().int)[:9]),
            "user_id": admin["user_id"],
            "related_item_id": item_id,
            "related_transaction_id": transaction_id,
        }
        await db.notifications.insert_one(noti)
    # Redirect về trang sản phẩm với thông báo
    return RedirectResponse(url=f"/items/{item_id}", status_code=http_status.HTTP_303_SEE_OTHER)


@router.post("/{item_id}/exchange-proposal/{proposal_id}/accept")
async def accept_exchange_proposal(item_id: int, proposal_id: int, user: dict = Depends(user_required)):
    db = Database.db
    item = await db.items.find_one({"item_id": item_id})
    proposal = await db.transactions.find_one({"transaction_id": proposal_id, "transaction_type": "exchange_proposal"})
    if not item or not proposal:
        raise HTTPException(status_code=404, detail="Item or proposal not found")
    if user["user_id"] != item["user_id"]:
        raise HTTPException(status_code=403, detail="Only the owner can accept proposals")
    if proposal["status"] != "pending":
        raise HTTPException(status_code=400, detail="Proposal already processed")
    # Cập nhật trạng thái proposal
    await db.transactions.update_one({"transaction_id": proposal_id}, {"$set": {"status": "accepted", "status_updated_at": datetime.now().isoformat()}})
    # Cập nhật trạng thái item (pending_exchange)
    await db.items.update_one({"item_id": item_id}, {"$set": {"status": "pending_exchange", "exchange_transaction_id": proposal_id}})
    # Gửi thông báo cho người đề xuất
    notify = {
        "message": f"The owner has accepted the exchange proposal for item '{item['name']}' from {proposal['buyer_user_id']}",
        "created_at": datetime.now().isoformat(),
        "is_read": False,
        "is_seen": False,
        "noti_id": int(str(uuid.uuid4().int)[:9]),
        "user_id": proposal["buyer_user_id"],
        "related_item_id": item_id,
        "related_transaction_id": proposal_id,
    }
    await db.notifications.insert_one(notify)
    # Gửi thông báo cho tất cả admin
    admin_users = await db.users.find({"role": "admin"}).to_list(length=100)
    for admin in admin_users:
        noti = {
            "message": f"The owner has accepted the exchange proposal for item '{item['name']}' from {proposal['buyer_user_id']}",
            "created_at": datetime.now().isoformat(),
            "is_read": False,
            "is_seen": False,
            "noti_id": int(str(uuid.uuid4().int)[:9]),
            "user_id": admin["user_id"],
            "related_item_id": item_id,
            "related_transaction_id": proposal_id,
        }
        await db.notifications.insert_one(noti)
    return RedirectResponse(url=f"/items/{item_id}", status_code=http_status.HTTP_303_SEE_OTHER)


@router.post("/{item_id}/exchange-proposal/{proposal_id}/reject")
async def reject_exchange_proposal(item_id: int, proposal_id: int, user: dict = Depends(user_required)):
    db = Database.db
    item = await db.items.find_one({"item_id": item_id})
    proposal = await db.transactions.find_one({"transaction_id": proposal_id, "transaction_type": "exchange_proposal"})
    if not item or not proposal:
        raise HTTPException(status_code=404, detail="Item or proposal not found")
    if user["user_id"] != item["user_id"]:
        raise HTTPException(status_code=403, detail="Only the owner can reject proposals")
    if proposal["status"] != "pending":
        raise HTTPException(status_code=400, detail="Proposal already processed")
    # Cập nhật trạng thái proposal
    await db.transactions.update_one({"transaction_id": proposal_id}, {"$set": {"status": "rejected", "status_updated_at": datetime.now().isoformat()}})
    # Nếu không còn proposal nào pending, item trở lại active
    pending_count = await db.transactions.count_documents({"item_id": item_id, "transaction_type": "exchange_proposal", "status": "pending"})
    if pending_count == 0:
        await db.items.update_one({"item_id": item_id}, {"$set": {"status": "active", "exchange_transaction_id": None}})
    # Gửi thông báo cho người đề xuất
    notify = {
        "message": f"Your exchange proposal for item '{item['name']}' has been rejected.",
        "created_at": datetime.now().isoformat(),
        "is_read": False,
        "is_seen": False,
        "noti_id": int(str(uuid.uuid4().int)[:9]),
        "user_id": proposal["buyer_user_id"],
        "related_item_id": item_id,
        "related_transaction_id": proposal_id,
    }
    await db.notifications.insert_one(notify)
    return RedirectResponse(url=f"/items/{item_id}", status_code=http_status.HTTP_303_SEE_OTHER)

# Route cho admin xác nhận hoàn tất trao đổi
@router.post("/admin/items/{item_id}/exchange-complete/{proposal_id}")
async def admin_complete_exchange(item_id: int, proposal_id: int, admin: dict = Depends(get_current_user)):
    db = Database.db
    item = await db.items.find_one({"item_id": item_id})
    proposal = await db.transactions.find_one({"transaction_id": proposal_id, "transaction_type": "exchange_proposal"})
    if not item or not proposal:
        raise HTTPException(status_code=404, detail="Item or proposal not found")
    if admin["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin can complete exchange")
    # Cập nhật trạng thái transaction và item
    await db.transactions.update_one(
        {"transaction_id": proposal_id}, 
        {
            "$set": {
                "status": "completed",
                "status_updated_at": datetime.now().isoformat(),
                "completed_at": datetime.now().isoformat()
            }
        }
    )
    await db.items.update_one({"item_id": item_id}, {"$set": {"status": "exchanged"}})
    # Gửi thông báo cho các bên liên quan
    notify_buyer = {
        "message": f"The exchange transaction for item '{item['name']}' has been confirmed as completed by admin!",
        "created_at": datetime.now().isoformat(),
        "is_read": False,
        "is_seen": False,
        "noti_id": int(str(uuid.uuid4().int)[:9]),
        "user_id": proposal["buyer_user_id"],
        "related_item_id": item_id,
        "related_transaction_id": proposal_id,
    }
    notify_seller = {
        "message": f"The exchange transaction for item '{item['name']}' has been confirmed as completed by admin!",
        "created_at": datetime.now().isoformat(),
        "is_read": False,
        "is_seen": False,
        "noti_id": int(str(uuid.uuid4().int)[:9]),
        "user_id": proposal["seller_user_id"],
        "related_item_id": item_id,
        "related_transaction_id": proposal_id,
    }
    await db.notifications.insert_one(notify_buyer)
    await db.notifications.insert_one(notify_seller)
    return RedirectResponse(url=f"/admin/items/{item_id}", status_code=http_status.HTTP_303_SEE_OTHER)

def b64encode(data):
    if data:
        return base64.b64encode(data).decode('utf-8')
    return ''
templates.env.filters['b64encode'] = b64encode
