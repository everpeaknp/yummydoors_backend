from starlette.middleware.cors import CORSMiddleware
from fastapi import FastAPI
import uvicorn
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "*"], allow_credentials=True, allow_methods=["*"])

@app.post("/api/v1/favorites/menu-items/1")
async def root():
    return {"message": "Hello World"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
