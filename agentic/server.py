from fastapi import FastAPI
from pydantic import BaseModel
from agentic_controller import AgenticSwarmController
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

controller = AgenticSwarmController()

class CommandRequest(BaseModel):
    command: str

@app.post("/command")
async def process_command(request: CommandRequest):
    result = controller.process_command(request.command)
    return result

@app.get("/state")
async def get_state():
    state = controller.api_client.get_state()
    return state
