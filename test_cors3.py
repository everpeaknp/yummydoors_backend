import asyncio
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import FastAPI
import uvicorn

app = FastAPI()

class PrintMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        print("Received method:", request.method)
        print("Received headers:", dict(request.headers))
        response = await call_next(request)
        return response

app.add_middleware(PrintMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.options("/api/v1/favorites/menu-items/1")
async def root_options():
    return {"message": "Hello OPTIONS"}

@app.post("/api/v1/favorites/menu-items/1")
async def root():
    return {"message": "Hello World"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8005)
