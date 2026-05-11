import os
import shutil
import uuid
import time
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
import jwt
from sqlalchemy.future import select
from app.core.config import settings
from app.db.database import get_db
from app.db.models import Attachment
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

def create_signed_url(request: Request, user_id: str, session_id: str, image_uuid: str):
    """Generate a URL with a temporal JWT token."""
    expire = time.time() + (settings.TOKEN_EXPIRE_HOURS * 3600)
    payload = {
        "user_id": user_id,
        "session_id": session_id,
        "image_uuid": image_uuid,
        "exp": expire
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    # Construct base URL from request
    base_url = str(request.base_url).rstrip("/")
    return f"{base_url}/view/{user_id}/{session_id}/{image_uuid}?token={token}"

@router.post("/api/v1/images/upload")
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    user_id: str = Form("default"),
    session_id: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    # Generate unique ID and path
    image_uuid = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1] or ".png"
    session_dir = os.path.join(settings.UPLOAD_DIR, user_id, session_id)
    os.makedirs(session_dir, exist_ok=True)
    
    file_path = os.path.join(session_dir, f"{image_uuid}{ext}")
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File save failed: {str(e)}")
    
    # TODO: DB의 sessions 테이블 검증 로직이 필요할 수 있으나 MVP를 위해 생략하거나
    # 여기서 Attachment 레코드를 생성할 수 있음.
    # new_attachment = Attachment(
    #     attachment_id=uuid.UUID(image_uuid),
    #     session_id=uuid.UUID(session_id) if session_id != "default" else None, # Needs careful handling of dummy uuids
    #     file_name=file.filename,
    #     storage_path=file_path
    # )
    # db.add(new_attachment)
    # await db.commit()

    image_url = create_signed_url(request, user_id, session_id, image_uuid)
    
    return {
        "status": "success",
        "image_url": image_url,
        "image_uuid": image_uuid
    }

@router.get("/api/v1/images/refresh_url")
async def refresh_url(
    request: Request,
    user_id: str = Query(...),
    session_id: str = Query(...),
    image_uuid: str = Query(...)
):
    # Check if file exists (any extension)
    session_dir = os.path.join(settings.UPLOAD_DIR, user_id, session_id)
    if not os.path.exists(session_dir):
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Look for the file with the given uuid
    found = False
    for f in os.listdir(session_dir):
        if f.startswith(image_uuid):
            found = True
            break
            
    if not found:
        raise HTTPException(status_code=404, detail="Image not found")
    
    new_url = create_signed_url(request, user_id, session_id, image_uuid)
    return {"image_url": new_url}

@router.delete("/api/v1/images/session")
async def delete_session(
    user_id: str = Query(...),
    session_id: str = Query(...)
):
    session_dir = os.path.join(settings.UPLOAD_DIR, user_id, session_id)
    
    if os.path.exists(session_dir):
        try:
            shutil.rmtree(session_dir)
            # Remove user dir if empty
            user_dir = os.path.join(settings.UPLOAD_DIR, user_id)
            if not os.listdir(user_dir):
                os.rmdir(user_dir)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")
            
    return {"status": "success", "message": "Session images purged."}

@router.get("/view/{user_id}/{session_id}/{image_uuid}")
async def view_image(
    user_id: str,
    session_id: str,
    image_uuid: str,
    token: str = Query(...)
):
    # Verify JWT
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if (payload.get("user_id") != user_id or 
            payload.get("session_id") != session_id or 
            payload.get("image_uuid") != image_uuid):
            raise HTTPException(status_code=403, detail="Invalid token details")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=403, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=403, detail="Invalid token")
        
    # Find file
    session_dir = os.path.join(settings.UPLOAD_DIR, user_id, session_id)
    if not os.path.exists(session_dir):
        raise HTTPException(status_code=404, detail="Image not found")
        
    file_name = None
    for f in os.listdir(session_dir):
        if f.startswith(image_uuid):
            file_name = f
            break
            
    if not file_name:
        raise HTTPException(status_code=404, detail="Image not found")
        
    file_path = os.path.join(session_dir, file_name)
    return FileResponse(file_path)
