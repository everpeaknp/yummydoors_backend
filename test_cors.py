from starlette.middleware.cors import CORSMiddleware
from fastapi import FastAPI
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "*"], allow_credentials=True)
print("Middleware added successfully!")
