import os
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

# Load local environment variables
load_dotenv()

# Import the LangGraph agent runner
from agentic_workflow import run_agent

# Initialize FastAPI App
app = FastAPI(
    title="AI Travel Planner Backend",
    description="FastAPI Backend serving the LangGraph ReAct Agentic Workflow",
    version="1.0.0"
)

# Request / Response Schemas
class QueryRequest(BaseModel):
    query: str
    thread_id: Optional[str] = "default_thread"
    groq_api_key: Optional[str] = None

class QueryResponse(BaseModel):
    response: str
    itinerary_data: Optional[str] = None

@app.post("/query", response_model=QueryResponse)
async def query_agent(request: QueryRequest):
    """
    Submits a query to the travel planner agent and returns the response.
    Maintains thread-based conversation memory.
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
        
    # Resolve API Key
    api_key = request.groq_api_key or os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Groq API Key is required. Please set it in .env or provide it in the request."
        )
        
    try:
        # Execute the agent
        res_dict = run_agent(
            query=request.query,
            thread_id=request.thread_id,
            groq_api_key=api_key
        )
        return QueryResponse(
            response=res_dict["response"],
            itinerary_data=res_dict["itinerary_data"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """
    Simple status endpoint for backend checking.
    """
    # Check if Groq API key is present in environment
    env_configured = bool(os.environ.get("GROQ_API_KEY"))
    return {
        "status": "healthy",
        "groq_api_key_configured": env_configured
    }

if __name__ == "__main__":
    import uvicorn
    # Start the server on port 8000
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
