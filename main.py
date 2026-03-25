from test_web import create_app
from agent import create_agent
from tool import tools
import uvicorn


agent = create_agent()

app = create_app(agent, tools)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)