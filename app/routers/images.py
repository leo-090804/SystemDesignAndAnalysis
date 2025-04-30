from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from app.database.mongodb import Database

router = APIRouter(tags=["public"])

@router.get("/api/items/{item_id}/image")
async def get_item_image(item_id: int):
    """Retrieve image directly from items collection"""
    db = Database.db
    
    # Find the item
    item = await db.items.find_one({"item_id": item_id})
    
    if not item or "image_data" not in item:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Return the image with appropriate content type
    return Response(
        content=item["image_data"], 
        media_type=item.get("image_content_type", "image/jpeg")
    )
