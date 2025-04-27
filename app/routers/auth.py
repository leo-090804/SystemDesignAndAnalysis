from fastapi import APIRouter, Depends, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from typing import Optional
from app.services.auth import authenticate_user, create_access_token, create_user, ACCESS_TOKEN_EXPIRE_MINUTES
from app.models.user import UserCreate

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.post("/login")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        user = await authenticate_user(form_data.username, form_data.password)

        # Check if authentication failed
        if not user:
            return templates.TemplateResponse(
                "auth/login.html", {"request": request, "error": "Invalid username or password"}
            )

        # Check if account is locked
        if user == "locked":
            return templates.TemplateResponse(
                "auth/login.html",
                {"request": request, "error": "Your account has been locked. Please contact an administrator."},
            )

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(data={"sub": user["username"]}, expires_delta=access_token_expires)

        # Redirect admin to admin dashboard, other users to regular dashboard
        redirect_url = "/admin/dashboard" if user["role"] == "admin" else "/dashboard"
        response = RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
        return response
    except Exception as e:
        print(f"Login error: {str(e)}")
        return templates.TemplateResponse(
            "auth/login.html", {"request": request, "error": "An error occurred. Please try again."}
        )


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("auth/register.html", {"request": request})


@router.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    name: str = Form(...),
    role: str = Form(...),
    grade: Optional[str] = Form(None),
    subject: Optional[str] = Form(None),
    organization: Optional[str] = Form(None),
):
    user_create = UserCreate(
        username=username,
        password=password,
        name=name,
        role=role,
        grade=grade,
        subject=subject,
        organization=organization,
    )

    user = await create_user(user_create)
    if not user:
        return templates.TemplateResponse(
            "auth/register.html", {"request": request, "error": "Username already exists"}
        )

    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="access_token")
    return response
