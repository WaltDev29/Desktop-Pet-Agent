import sys
import asyncio

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from agent_server import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    if sys.platform == 'win32':
        config = uvicorn.Config("main:app", host="0.0.0.0", port=8001, loop="asyncio")
        server = uvicorn.Server(config)
        asyncio.run(server.serve())
    else:
        uvicorn.run("main:app", host="0.0.0.0", port=8001)
