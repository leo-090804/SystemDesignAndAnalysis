import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query, Path
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from app.database.mongodb import Database
from app.services.auth import get_current_user
from datetime import datetime

router = APIRouter(prefix="/admin/transactions", tags=["admin"])
templates = Jinja2Templates(directory="templates")

# Middleware to check admin rights
async def admin_required(request: Request):
    user = await get_current_user(request)
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user

@router.get("/", response_class=HTMLResponse)
async def list_transactions(
    request: Request,
    admin: dict = Depends(admin_required),
    status: Optional[str] = None,
    page: int = Query(1, ge=1)
):
    db = Database.db
    
    # Build base query with status filter if provided
    base_query = {}
    if status:
        base_query["status"] = status
    
    # REGULAR TRANSACTIONS (item purchases)
    regular_query = {
        **base_query,
        "transaction_type": "purchase"
    }
    
    regular_transactions = await db.transactions.find(regular_query).sort("transaction_date", -1).to_list(length=100)
    
    # CAMPAIGN TRANSACTIONS (donations)
    campaign_query = {
        **base_query,
        "transaction_type": "donation"
    }
    
    campaign_transactions = await db.transactions.find(campaign_query).sort("transaction_date", -1).to_list(length=100)
    
    # Get related data for each transaction
    for transaction in regular_transactions:
        # Get item info
        item = await db.items.find_one({"item_id": transaction["item_id"]})
        transaction["item"] = item if item else {"name": "Unknown Item"}
        
        # Get buyer info
        buyer = await db.users.find_one({"user_id": transaction["buyer_user_id"]})
        transaction["buyer"] = buyer if buyer else {"name": "Unknown User"}
        
        # Get seller info
        seller = await db.users.find_one({"user_id": transaction["seller_user_id"]})
        transaction["seller"] = seller if seller else {"name": "Unknown User"}
    
    # Enrich campaign transactions data
    for transaction in campaign_transactions:
        # Get campaign info
        campaign = await db.campaigns.find_one({"campaign_id": transaction["campaign_id"]})
        transaction["campaign"] = campaign if campaign else {"name": "Unknown Campaign"}
        
        # Get donor info
        if campaign["campaign_type"] == "fundraising":
            donor = await db.users.find_one({"user_id": transaction["buyer_user_id"]})
            transaction["donor"] = donor if donor else {"name": "Unknown User"}
            
        elif campaign["campaign_type"] == "donation":
            donor = await db.users.find_one({"user_id": transaction["seller_user_id"]})
            transaction["donor"] = donor if donor else {"name": "Unknown User"}
    
    return templates.TemplateResponse(
        "admin/transactions.html",
        {"request": request, "user": admin, 
         "regular_transactions": regular_transactions,
         "campaign_transactions": campaign_transactions,
         "status": status, "page": page}
    )

@router.get("/{transaction_id}", response_class=HTMLResponse)
async def view_transaction(
    request: Request,
    transaction_id: int = Path(...),
    admin: dict = Depends(admin_required)
):
    db = Database.db
    transaction = await db.transactions.find_one({"transaction_id": transaction_id})
    
    if not transaction:
        return templates.TemplateResponse(
            "admin/error.html",
            {"request": request, "user": admin, "message": "Transaction not found"}
        )
    
    # Get item info
    item = await db.items.find_one({"item_id": transaction["item_id"]})
    
    # Get buyer info
    buyer = await db.users.find_one({"user_id": transaction["buyer_user_id"]})
    
    # Get seller info
    seller = await db.users.find_one({"user_id": transaction["seller_user_id"]})
    
    return templates.TemplateResponse(
        "admin/view_transaction.html",
        {"request": request, "user": admin, "transaction": transaction,
         "item": item, "buyer": buyer, "seller": seller}
    )

@router.post("/{transaction_id}/approve")
async def approve_transaction(
    transaction_id: int = Path(...),
    admin: dict = Depends(admin_required)
):
    db = Database.db
    now = datetime.now().isoformat()

    # Get transaction
    transaction = await db.transactions.find_one({"transaction_id": transaction_id})
    if not transaction:
        return {"success": False, "message": "Transaction not found"}

    # Check if transaction is in pending status
    if transaction["status"] != "pending":
        return {"success": False, "message": f"Cannot approve transaction in {transaction['status']} status"}

    # Handle based on transaction type
    if transaction["transaction_type"] == "purchase":
        # For purchase transactions

        # Get item
        item = await db.items.find_one({"item_id": transaction["item_id"]})
        if not item:
            return {"success": False, "message": "Item not found"}

        # Get buyer and seller
        buyer = await db.users.find_one({"user_id": transaction["buyer_user_id"]})
        seller = await db.users.find_one({"user_id": transaction["seller_user_id"]})
        if not buyer or not seller:
            return {"success": False, "message": "Buyer or seller not found"}

        # Update transaction status
        await db.transactions.update_one(
            {"transaction_id": transaction_id},
            {"$set": {
                "status": "completed",
                "status_updated_at": now
            }}
        )

        # Update item status
        await db.items.update_one(
            {"item_id": transaction["item_id"]},
            {"$set": {
                "status": "sold",
                "sold_at": now
            }}
        )

        # Send notifications
        # To buyer
        await db.notifications.insert_one({
            "message": f"Your purchase of '{item['name']}' has been approved.",
            "created_at": now,
            "is_read": False,
            "is_seen": False,
            # "noti_id": await get_next_id(db, "notifications", "noti_id"),
            "noti_id": int(str(uuid.uuid4().int)[:9]),
            "user_id": buyer["user_id"],
            "related_item_id": item["item_id"],
            "related_transaction_id": transaction_id
        })

        # To seller
        await db.notifications.insert_one(
            {
                "message": f"Your sale of '{item['name']}' has been completed.",
                "created_at": now,
                "is_read": False,
                "is_seen": False,
                # "noti_id": await get_next_id(db, "notifications", "noti_id"),
                "noti_id": int(str(uuid.uuid4().int)[:9]),
                "user_id": seller["user_id"],
                "related_item_id": item["item_id"],
                "related_transaction_id": transaction_id,
            }
        )

    elif transaction["transaction_type"] == "donation":
        # For donation transactions

        # Get campaign
        campaign = await db.campaigns.find_one({"campaign_id": transaction["campaign_id"]})
        if not campaign:
            return {"success": False, "message": "Campaign not found"}

        # Get donor for fundrasing campaign
        if campaign["campaign_type"] == "fundraising": 
            donor = await db.users.find_one({"user_id": transaction["buyer_user_id"]})
            if not donor:
                return {"success": False, "message": "Donor not found"}

            # Update transaction status
            await db.transactions.update_one(
                {"transaction_id": transaction_id},
                {"$set": {
                    "status": "completed",
                    "status_updated_at": now
                }}
            )

            # Update campaign amount now that donation is approved
            new_amount = campaign.get("current_amount", 0) + transaction["amount"]
            await db.campaigns.update_one(
                {"campaign_id": transaction["campaign_id"]},
                {"$set": {"current_amount": new_amount}}
            )

            await db.items.update_one(
                {"item_id": transaction["item_id"]}, 
                {"$set": 
                    {"status": "sold", 
                     "sold_at": now
                }}
            )

            # Send notifications
            # To donor
            await db.notifications.insert_one(
                {
                    "message": f"Your donation of ${transaction['amount']:.2f} to '{campaign['name']}' has been approved.",
                    "created_at": now,
                    "is_read": False,
                    "is_seen": False,
                    # "noti_id": await get_next_id(db, "notifications", "noti_id"),
                    "noti_id": int(str(uuid.uuid4().int)[:9]),
                    "user_id": donor["user_id"],
                    "related_item_id": None,
                    "related_transaction_id": transaction_id,
                }
            )

            # To campaign creator
            await db.notifications.insert_one(
                {
                    "message": f"A donation of ${transaction['amount']:.2f} from {donor['name']} to '{campaign['name']}' has been approved.",
                    "created_at": now,
                    "is_read": False,
                    "is_seen": False,
                    # "noti_id": await get_next_id(db, "notifications", "noti_id"),
                    "noti_id": int(str(uuid.uuid4().int)[:9]),
                    "user_id": campaign["created_by"],
                    "related_item_id": None,
                    "related_transaction_id": transaction_id,
                }
            )

        # Get donor for donation campaign
        elif campaign["campaign_type"] == "donation":
            donor = await db.users.find_one({"user_id": transaction["seller_user_id"]})
            if not donor:
                return {"success": False, "message": "Donor not found"}

            # Update transaction status
            await db.transactions.update_one(
                {"transaction_id": transaction_id},
                {"$set": {
                    "status": "completed",
                    "status_updated_at": now
                }}
            )

            await db.items.update_one(
                {"item_id": transaction["item_id"]}, 
                {"$set": 
                    {"status": "donated", 
                     "donated_at": now
                }}
            )

            # Send notifications
            # To donor
            await db.notifications.insert_one(
                {
                    "message": f"Your donation of item {transaction['item_id']} to '{campaign['name']}' has been approved.",
                    "created_at": now,
                    "is_read": False,
                    "is_seen": False,
                    # "noti_id": await get_next_id(db, "notifications", "noti_id"),
                    "noti_id": int(str(uuid.uuid4().int)[:9]),
                    "user_id": donor["user_id"],
                    "related_item_id": None,
                    "related_transaction_id": transaction_id,
                }
            )

    else:
        return {"success": False, "message": f"Unknown transaction type: {transaction['transaction_type']}"}

    return {"success": True}

@router.post("/{transaction_id}/cancel")
async def cancel_transaction(
    transaction_id: int = Path(...),
    reason: str = Form(...),
    admin: dict = Depends(admin_required)
):
    db = Database.db
    now = datetime.now().isoformat()

    # Get transaction
    transaction = await db.transactions.find_one({"transaction_id": transaction_id})
    if not transaction:
        return {"success": False, "message": "Transaction not found"}

    # Check if transaction is in pending status
    if transaction["status"] != "pending":
        return {"success": False, "message": f"Cannot cancel transaction in {transaction['status']} status"}

    # Handle based on transaction type
    if transaction["transaction_type"] == "purchase":
        # For purchase transactions

        # Get item
        item = await db.items.find_one({"item_id": transaction["item_id"]})
        if not item:
            return {"success": False, "message": "Item not found"}

        # Get buyer and seller
        buyer = await db.users.find_one({"user_id": transaction["buyer_user_id"]})
        seller = await db.users.find_one({"user_id": transaction["seller_user_id"]})
        if not buyer or not seller:
            return {"success": False, "message": "Buyer or seller not found"}

        # Update transaction status
        await db.transactions.update_one(
            {"transaction_id": transaction_id},
            {"$set": {
                "status": "cancelled",
                "status_updated_at": now,
                "cancellation_reason": reason
            }}
        )

        # Update item status back to active
        await db.items.update_one(
            {"item_id": transaction["item_id"]},
            {"$set": {
                "status": "active",
                "transaction_id": None,
                "buyer_user_id": None
            }}
        )

        # Send notifications
        # To buyer
        await db.notifications.insert_one(
            {
                "message": f"Your purchase of '{item['name']}' has been cancelled. Reason: {reason}",
                "created_at": now,
                "is_read": False,
                "is_seen": False,
                # "noti_id": await get_next_id(db, "notifications", "noti_id"),
                "noti_id": int(str(uuid.uuid4().int)[:9]),
                "user_id": buyer["user_id"],
                "related_item_id": item["item_id"],
                "related_transaction_id": transaction_id,
            }
        )

        # To seller
        await db.notifications.insert_one(
            {
                "message": f"Sale of your item '{item['name']}' has been cancelled. Reason: {reason}",
                "created_at": now,
                "is_read": False,
                "is_seen": False,
                # "noti_id": await get_next_id(db, "notifications", "noti_id"),
                "noti_id": int(str(uuid.uuid4().int)[:9]),
                "user_id": seller["user_id"],
                "related_item_id": item["item_id"],
                "related_transaction_id": transaction_id,
            }
        )

    elif transaction["transaction_type"] == "donation":
        # For donation transactions

        # Get campaign
        campaign = await db.campaigns.find_one({"campaign_id": transaction["campaign_id"]})
        if not campaign:
            return {"success": False, "message": "Campaign not found"}

        # Get donor
        donor = await db.users.find_one({"user_id": transaction["buyer_user_id"]})
        if not donor:
            return {"success": False, "message": "Donor not found"}

        # Update transaction status
        await db.transactions.update_one(
            {"transaction_id": transaction_id},
            {"$set": {
                "status": "cancelled",
                "status_updated_at": now,
                "cancellation_reason": reason
            }}
        )

        # Send notifications
        # To donor
        await db.notifications.insert_one(
            {
                "message": f"Your donation of ${transaction['amount']:.2f} to '{campaign['name']}' has been cancelled. Reason: {reason}",
                "created_at": now,
                "is_read": False,
                "is_seen": False,
                # "noti_id": await get_next_id(db, "notifications", "noti_id"),
                "noti_id": int(str(uuid.uuid4().int)[:9]),
                "user_id": donor["user_id"],
                "related_item_id": None,
                "related_transaction_id": transaction_id,
            }
        )

        # To campaign creator
        await db.notifications.insert_one(
            {
                "message": f"A donation of ${transaction['amount']:.2f} from {donor['name']} to campaign '{campaign['name']}' has been cancelled. Reason: {reason}",
                "created_at": now,
                "is_read": False,
                "is_seen": False,
                # "noti_id": await get_next_id(db, "notifications", "noti_id"),
                "noti_id": int(str(uuid.uuid4().int)[:9]),
                "user_id": campaign["created_by"],
                "related_item_id": None,
                "related_transaction_id": transaction_id,
            }
        )

    else:
        return {"success": False, "message": f"Unknown transaction type: {transaction['transaction_type']}"}

    return {"success": True}

# async def get_next_id(db, collection_name, id_field):
#     last_doc = await db[collection_name].find_one(sort=[(id_field, -1)])
#     return 1 if not last_doc else last_doc[id_field] + 1
