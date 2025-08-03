from fastapi import FastAPI
from pydantic import BaseModel
from agent.agentic_workflow import GraphBuilder
from fastapi.responses import JSONResponse
from starlette.responses import JSONResponse
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Ensure GROQ_API_KEY is set
if not os.getenv("GROQ_API_KEY"):
    raise ValueError("GROQ_API_KEY is not set. Please set it in your .env file.")

app = FastAPI()

class QueryRequest(BaseModel):
    query: str

@app.post("/query")
async def query_travel_agent(query: QueryRequest):
    try:
        print(query)

        # No need to pass api_key if your GraphBuilder reads from env
        graph = GraphBuilder(model_provider="groq")
        react_app = graph()

        # Save visualized graph
        png_graph = react_app.get_graph().draw_mermaid_png()
        with open("my_graph.png", "wb") as f:
            f.write(png_graph)

        print(f"Graph saved as 'my_graph.png' in {os.getcwd()}")

        # Send user query
        messages = {"messages": [query.query]}
        output = react_app.invoke(messages)

        # Extract AI response
        if isinstance(output, dict) and "messages" in output:
            final_output = output["messages"][-1].content
        else:
            final_output = str(output)

        return {"answer": final_output}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
