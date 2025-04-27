import asyncio
import logging
from datetime import datetime
import uuid
from app.database.mongodb import Database

logger = logging.getLogger(__name__)

async def check_expired_transactions():
    """Background task to check and cancel expired transactions."""
    try:
        # Use get_db instead of connect_to_database to reuse existing connection
        db = await Database.get_db()
        
        # Find expired processing transactions
        now = datetime.now().isoformat()
        expired_transactions = await db.transactions.find({
            "status": "processing",
            "expiration_date": {"$lt": now}
        }).to_list(length=100)
        
        for transaction in expired_transactions:
            logger.info(f"Cancelling expired transaction {transaction['transaction_id']}")
            
            # Update transaction status
            await db.transactions.update_one(
                {"transaction_id": transaction["transaction_id"]},
                {"$set": {
                    "status": "cancelled",
                    "status_updated_at": now,
                    "cancellation_reason": "Transaction expired"
                }}
            )
            
            # Restore item status to active
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
            await db.notifications.insert_one({
                "message": f"Your purchase of item #{transaction['item_id']} was cancelled due to expiration.",
                "created_at": now,
                "is_read": False,
                "is_seen": False,
                # "noti_id": await get_next_id(db, "notifications", "noti_id"),
                "noti_id": int(str(uuid.uuid4().int)[:9]),
                "user_id": transaction["buyer_user_id"],
                "related_item_id": transaction["item_id"],
                "related_transaction_id": transaction["transaction_id"]
            })
            
            # To seller
            await db.notifications.insert_one({
                "message": f"Transaction for your item #{transaction['item_id']} was cancelled due to expiration.",
                "created_at": now,
                "is_read": False,
                "is_seen": False,
                # "noti_id": await get_next_id(db, "notifications", "noti_id"),
                "noti_id": int(str(uuid.uuid4().int)[:9]),
                "user_id": transaction["seller_user_id"],
                "related_item_id": transaction["item_id"],
                "related_transaction_id": transaction["transaction_id"]
            })
        
        logger.info(f"Cancelled {len(expired_transactions)} expired transactions")
    
    except Exception as e:
        logger.error(f"Error in check_expired_transactions: {str(e)}")
    
    # Important: Do NOT close the database connection here

# async def get_next_id(db, collection_name, id_field):
#     last_doc = await db[collection_name].find_one(sort=[(id_field, -1)])
#     return 1 if not last_doc else last_doc[id_field] + 1

async def run_transaction_checker():
    """Run the transaction checker every hour."""
    while True:
        await check_expired_transactions()
        await asyncio.sleep(3600)  # Sleep for 1 hour
