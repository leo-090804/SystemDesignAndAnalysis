from fastapi import APIRouter, Depends, HTTPException, Request, Path, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional  # Add this import for Optional type
from datetime import datetime
from app.database.mongodb import Database
from app.services.auth import get_current_user

router = APIRouter(tags=["notifications"])
templates = Jinja2Templates(directory="templates")

# Middleware to check user is logged in
async def user_required(request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user

@router.get("/notifications", response_class=HTMLResponse)
async def list_notifications(
    request: Request,
    user: dict = Depends(user_required),
    page: int = Query(1, ge=1)
):
    db = Database.db
    limit = 15
    skip = (page - 1) * limit
    
    # Get notifications for this user
    notifications = await db.notifications.find(
        {"user_id": user["user_id"]}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(length=limit)
    
    total_notifications = await db.notifications.count_documents({"user_id": user["user_id"]})
    total_pages = (total_notifications + limit - 1) // limit if total_notifications > 0 else 1
    
    # Get additional info for related items/transactions
    for notification in notifications:
        if notification.get("related_item_id"):
            item = await db.items.find_one({"item_id": notification["related_item_id"]})
            if item:
                notification["item"] = item
        
        if notification.get("related_transaction_id"):
            transaction = await db.transactions.find_one({"transaction_id": notification["related_transaction_id"]})
            if transaction:
                notification["transaction"] = transaction
    
    # Mark all as seen (not the same as read)
    await db.notifications.update_many(
        {"user_id": user["user_id"], "is_seen": {"$ne": True}},
        {"$set": {"is_seen": True}}
    )
    
    return templates.TemplateResponse(
        "notifications/list.html",
        {"request": request, "user": user, "notifications": notifications,
         "page": page, "total_pages": total_pages}
    )

@router.get("/api/notifications/unread-count")
async def get_unread_count(request: Request, user: dict = Depends(user_required)):
    db = Database.db
    count = await db.notifications.count_documents({
        "user_id": user["user_id"],
        "is_read": False
    })
    
    return {"count": count}

@router.get("/api/notifications/recent")
async def get_recent_notifications(request: Request, user: dict = Depends(user_required), since: Optional[str] = None):
    db = await Database.get_db()
    
    # Build query
    query = {"user_id": user["user_id"]}
    
    # If since parameter is provided, only get notifications after that time
    if since:
        try:
            since_date = datetime.fromisoformat(since)
            query["created_at"] = {"$gt": since_date.isoformat()}
        except (ValueError, TypeError):
            # If invalid date format, ignore the since parameter
            pass
    
    # Get notifications
    notifications = await db.notifications.find(query).sort("created_at", -1).limit(5).to_list(length=5)
    
    # Mark notifications as seen
    notification_ids = [notification["_id"] for notification in notifications]
    if notification_ids:
        await db.notifications.update_many(
            {"_id": {"$in": notification_ids}, "is_seen": {"$ne": True}},
            {"$set": {"is_seen": True}}
        )
    
    # Get the unread count
    unread_count = await db.notifications.count_documents({
        "user_id": user["user_id"],
        "is_read": False
    })
    
    # Format the notifications for the dropdown
    formatted_notifications = []
    for notification in notifications:
        formatted_notifications.append({
            "id": str(notification["_id"]),
            "noti_id": notification["noti_id"],
            "message": notification["message"],
            "created_at": notification["created_at"],
            "is_read": notification["is_read"],
            "related_item_id": notification.get("related_item_id"),
            "related_transaction_id": notification.get("related_transaction_id")
        })
    
    return {
        "notifications": formatted_notifications,
        "unread_count": unread_count,
        "server_time": datetime.now().isoformat()
    }

@router.post("/api/notifications/{noti_id}/mark-read")
async def mark_notification_as_read(
    noti_id: int = Path(...),
    user: dict = Depends(user_required)
):
    db = Database.db
    
    result = await db.notifications.update_one(
        {"noti_id": noti_id, "user_id": user["user_id"]},
        {"$set": {"is_read": True}}
    )
    
    if result.modified_count:
        return {"success": True}
    else:
        return {"success": False, "message": "Notification not found or already marked as read"}

@router.post("/api/notifications/mark-all-read")
async def mark_all_as_read(user: dict = Depends(user_required)):
    db = Database.db
    
    result = await db.notifications.update_many(
        {"user_id": user["user_id"], "is_read": False},
        {"$set": {"is_read": True}}
    )
    
    return {"success": True, "count": result.modified_count}
