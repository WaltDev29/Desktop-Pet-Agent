import os
import httpx
import base64
import logging

logger = logging.getLogger(__name__)

# dotenv 등 환경 변수에서 가져오기
API_SERVER = os.environ.get("API_SERVER")

async def upload_image(base64_data: str, user_id: str, session_id: str) -> dict:
    """
    외부 API_SERVER 로 이미지를 전송하고 결과(dict)를 반환받습니다.
    반환 형태: {"url": str, "uuid": str, "session_id": str, "uploaded_at": float}
    """
    import time
    if not API_SERVER:
        logger.warning("[Storage] API_SERVER 환경 변수가 설정되지 않았습니다. 업로드를 우회합니다.")
        return {"url": "", "uuid": "", "session_id": session_id, "uploaded_at": time.time()}
    
    if "," in base64_data:
        base64_data = base64_data.split(",")[1]
        
    try:
        image_bytes = base64.b64decode(base64_data)
    except Exception as e:
        logger.error(f"[Storage] Base64 디코딩 실패: {e}")
        return {"url": "", "uuid": "", "session_id": session_id, "uploaded_at": time.time()}

    url = f"{API_SERVER.rstrip('/')}/api/v1/images/upload"
    files = {"file": ("image.png", image_bytes, "image/png")}
    data = {"user_id": user_id, "session_id": session_id}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, files=files, data=data, timeout=15)
            response.raise_for_status()
            
            result = response.json()
            image_url = result.get("image_url")
            image_uuid = result.get("image_uuid", "dummy-uuid")
            
            if not image_url:
                raise ValueError("응답에 image_url이 없습니다.")
                
            logger.info(f"[Storage] 이미지 외부 서버 업로드 성공: {image_url}")
            return {"url": image_url, "uuid": image_uuid, "session_id": session_id, "uploaded_at": time.time()}
    except Exception as e:
        logger.error(f"[Storage] 외부 서버 업로드 실패: {e}")
        return {"url": "", "uuid": "", "session_id": session_id, "uploaded_at": time.time()}

async def refresh_image_url(user_id: str, session_id: str, image_uuid: str) -> str:
    """기존 이미지의 새로운 Presigned URL을 발급받습니다."""
    if not API_SERVER:
        return ""
    
    url = f"{API_SERVER.rstrip('/')}/api/v1/images/refresh_url"
    params = {"user_id": user_id, "session_id": session_id, "image_uuid": image_uuid}
    
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, params=params, timeout=10)
            res.raise_for_status()
            return res.json().get("image_url", "")
    except Exception as e:
        logger.error(f"[Storage] URL 갱신 실패 (uuid={image_uuid}): {e}")
        return ""

async def delete_session_images(user_id: str, session_id: str):
    """특정 대화 세션의 모든 이미지를 물리적으로 삭제 요청합니다."""
    if not API_SERVER:
        return
        
    url = f"{API_SERVER.rstrip('/')}/api/v1/images/session"
    params = {"user_id": user_id, "session_id": session_id}
    
    try:
        async with httpx.AsyncClient() as client:
            res = await client.delete(url, params=params, timeout=10)
            res.raise_for_status()
            logger.info(f"[Storage] 대화 세션({session_id}) 이미지 폐기 완료")
    except Exception as e:
        logger.error(f"[Storage] 세션 파일 삭제 실패: {e}")
