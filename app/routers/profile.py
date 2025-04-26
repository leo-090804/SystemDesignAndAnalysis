from fastapi import APIRouter, Depends, HTTPException, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from app.database.mongodb import Database
from app.services.auth import get_current_user, get_password_hash, verify_password
import os
import shutil
import uuid

router = APIRouter(tags=["profile"])
templates = Jinja2Templates(directory="templates")

# Ensure upload directory exists
UPLOAD_DIR = "static/uploads/profiles"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Middleware to check user is logged in
async def user_required(request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user

@router.get("/profile", response_class=HTMLResponse)
async def view_profile(request: Request, user: dict = Depends(user_required)):
    # Admin should be redirected to admin dashboard
    if user["role"] == "admin":
        return RedirectResponse(url="/admin/dashboard")
    
    return templates.TemplateResponse(
        "profile/view.html",
        {"request": request, "user": user}
    )

@router.get("/profile/edit", response_class=HTMLResponse)
async def edit_profile_form(request: Request, user: dict = Depends(user_required)):
    # Admin should be redirected to admin dashboard
    if user["role"] == "admin":
        return RedirectResponse(url="/admin/dashboard")
    
    return templates.TemplateResponse(
        "profile/edit.html",
        {"request": request, "user": user}
    )

@router.post("/profile/edit")
async def update_profile(
    request: Request,
    user: dict = Depends(user_required),
    name: str = Form(...),
    grade: Optional[str] = Form(None),
    organization: Optional[str] = Form(None),
    current_password: Optional[str] = Form(None),
    new_password: Optional[str] = Form(None),
    confirm_password: Optional[str] = Form(None),
    profile_image: UploadFile = File(None)
):
    # Admin should be redirected to admin dashboard
    if user["role"] == "admin":
        return RedirectResponse(url="/admin/dashboard")
    
    db = Database.db
    update_data = {"name": name}
    
    # Update role-specific fields
    if user["role"] == "student" and grade:
        update_data["grade"] = grade
    
    if organization:
        update_data["organization"] = organization
    
    # Handle password change if provided
    error = None
    if current_password and new_password:
        # Verify current password
        if not verify_password(current_password, user["password_hash"]):
            error = "Current password is incorrect"
        elif new_password != confirm_password:
            error = "New passwords do not match"
        elif len(new_password) < 6:
            error = "New password must be at least 6 characters"
        else:
            # Hash new password
            update_data["password_hash"] = get_password_hash(new_password)
    
    # Handle profile image if provided
    if profile_image and profile_image.filename:
        # Generate unique filename
        file_ext = os.path.splitext(profile_image.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        # Save the file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(profile_image.file, buffer)
        
        # Store the relative path
        update_data["profile_image"] = f"/static/uploads/profiles/{unique_filename}"
    
    # If there's an error, return to form with error message
    if error:
        return templates.TemplateResponse(
            "profile/edit.html",
            {"request": request, "user": user, "error": error}
        )
    
    # Update user in database
    result = await db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": update_data}
    )
    
    # Redirect to profile view
    return RedirectResponse(url="/profile", status_code=303)
