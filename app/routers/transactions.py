from fastapi import APIRouter, Depends, HTTPException, Request, Query, Path
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from app.database.mongodb import Database
from app.services.auth import get_current_user

router = APIRouter(tags=["transactions"])
templates = Jinja2Templates(directory="templates")

# Middleware to check user is logged in and active
async def user_required(request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    if not user.get("is_active"):
        raise HTTPException(status_code=403, detail="Account is locked")
    return user

@router.get("/transactions", response_class=HTMLResponse)
async def list_transactions(
    request: Request,
    user: dict = Depends(user_required),
    status: Optional[str] = None,
    page: int = Query(1, ge=1)
):
    if user["role"] == "admin":
        return RedirectResponse(url="/admin/transactions")

    db = await Database.get_db()
    
    # Build base query with status filter if provided
    base_query = {}
    if status:
        base_query["status"] = status
    
    # REGULAR TRANSACTIONS (item purchases)
    regular_query = {
        **base_query,
        "transaction_type": "purchase",
        "$or": [
            {"buyer_user_id": user["user_id"]},
            {"seller_user_id": user["user_id"]}
        ]
    }
    
    regular_transactions = await db.transactions.find(regular_query).sort("transaction_date", -1).to_list(length=100)
    
    # CAMPAIGN TRANSACTIONS (donations)
    campaign_query = {
        **base_query,
        "transaction_type": "donation",
        "buyer_user_id": user["user_id"]
    }
    
    campaign_transactions = await db.transactions.find(campaign_query).sort("transaction_date", -1).to_list(length=100)
    
    # Enrich regular transactions data
    for transaction in regular_transactions:
        # Get item info
        item = await db.items.find_one({"item_id": transaction["item_id"]})
        transaction["item"] = item if item else {"name": "Unknown Item"}
        
        # Determine if user is buyer or seller
        transaction["is_buyer"] = transaction["buyer_user_id"] == user["user_id"]
        
        # Get the other party's info
        other_user_id = transaction["seller_user_id"] if transaction["is_buyer"] else transaction["buyer_user_id"]
        other_user = await db.users.find_one({"user_id": other_user_id})
        transaction["other_party"] = other_user["name"] if other_user else "Unknown User"
    
    # Enrich campaign transactions data
    for transaction in campaign_transactions:
        campaign = await db.campaigns.find_one({"campaign_id": transaction["campaign_id"]})
        transaction["campaign"] = campaign if campaign else {"name": "Unknown Campaign"}
    
    return templates.TemplateResponse(
        "transactions/list.html",
        {"request": request, "user": user, 
         "regular_transactions": regular_transactions, 
         "campaign_transactions": campaign_transactions, 
         "status": status, "page": page}
    )

@router.get("/transactions/{transaction_id}", response_class=HTMLResponse)
async def view_transaction(
    request: Request,
    transaction_id: int = Path(...),
    user: dict = Depends(user_required)
):
    db = await Database.get_db()
    
    # Get transaction
    transaction = await db.transactions.find_one({"transaction_id": transaction_id})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Check if user is part of this transaction
    if transaction["buyer_user_id"] != user["user_id"] and transaction["seller_user_id"] != user["user_id"] and user["role"] != "admin":
        raise HTTPException(status_code=403, detail="You don't have permission to view this transaction")
    
    # Get item info
    item = await db.items.find_one({"item_id": transaction["item_id"]})
    
    # Get buyer and seller info
    buyer = await db.users.find_one({"user_id": transaction["buyer_user_id"]})
    seller = await db.users.find_one({"user_id": transaction["seller_user_id"]})
    
    # Determine if user is buyer or seller
    is_buyer = transaction["buyer_user_id"] == user["user_id"]
    
    return templates.TemplateResponse(
        "transactions/view.html",
        {"request": request, "user": user, "transaction": transaction,
         "item": item, "buyer": buyer, "seller": seller, "is_buyer": is_buyer}
    )
