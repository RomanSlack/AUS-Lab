from fastapi import FastAPI
from pydantic import BaseModel
from agentic_controller import AgenticSwarmController
from fastapi.middleware.cors import CORSMiddleware
import typer
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

controller: AgenticSwarmController

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

@app.get("/leader")
async def get_leader():
    leader = controller.get_leader()
    return {"leader": leader}

def main(
    node_id: str = typer.Option("node1", help="The ID of the node"),
    port: int = typer.Option(8000, help="The port to run the server on"),
    raft_port: int = typer.Option(8001, help="The port for the raft protocol"),
    redis_port: int = typer.Option(6379, help="The port for the Redis server"),
):
    global controller
    peers = ["localhost:8001", "localhost:8002", "localhost:8003"]
    self_address = f"localhost:{raft_port}"
    partner_addrs = [p for p in peers if p != self_address]

    controller = AgenticSwarmController(
        api_base_url=f"http://localhost:{port}",
        node_id=node_id,
        self_address=self_address,
        partner_addrs=partner_addrs,
        redis_host="localhost",
        redis_port=redis_port,
    )
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    typer.run(main)
