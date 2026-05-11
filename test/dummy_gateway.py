import asyncio
import json
import logging
import websockets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DummyGateway")

async def handler(websocket):
    logger.info("클라이언트 연결됨!")
    try:
        async for message in websocket:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "register":
                client_id = data.get("payload", {}).get("client_id", "unknown")
                logger.info(f"에이전트 등록 완료: {client_id}")
                
                # 테스트용 Chat 메시지 보내기 (5초 후)
                async def send_test_chat():
                    await asyncio.sleep(5)
                    test_chat = {
                        "type": "chat",
                        "payload": {
                            "message": "안녕! 게이트웨이 테스트야.",
                            "images": []
                        }
                    }
                    logger.info("테스트용 Chat 메시지 에이전트로 전송...")
                    await websocket.send(json.dumps(test_chat))
                asyncio.create_task(send_test_chat())
                
            elif msg_type == "chat":
                payload = data.get("payload", {})
                images = payload.get("images", [])
                
                logger.info(f"Chat 수신: {payload.get('message')}")
                
                if images and any(not str(img).startswith("http") for img in images):
                    logger.info("Base64 이미지 감지. URL로 변환하여 에이전트에 반환합니다.")
                    # 실제 서버라면 여기서 S3 등에 업로드하고 URL을 받음
                    processed_payload = payload.copy()
                    processed_payload["images"] = [
                        f"https://picsum.photos/seed/{i}/800/600" for i in range(len(images))
                    ]
                    
                    response = {
                        "type": "chat",
                        "payload": processed_payload
                    }
                    await websocket.send(json.dumps(response))
                else:
                    logger.info("이미지가 없거나 이미 URL 형식입니다. (에이전트 답변 대기)")
                
            else:
                logger.info(f"수신된 메시지: {data}")
                
    except websockets.exceptions.ConnectionClosed:
        logger.info("클라이언트 연결 종료됨.")

async def main():
    logger.info("더미 게이트웨이 서버 시작 (ws://localhost:8080/ws)")
    async with websockets.serve(handler, "localhost", 8080):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
