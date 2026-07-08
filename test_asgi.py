import asyncio
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import PlainTextResponse

async def app(scope, receive, send):
    if scope["type"] == "http":
        await PlainTextResponse("Hello World")(scope, receive, send)

cors_app = CORSMiddleware(
    app,
    allow_origins=["http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

async def test():
    scope = {
        "type": "http",
        "method": "OPTIONS",
        "headers": [
            (b"origin", b"http://localhost:3000"),
            (b"access-control-request-method", b"POST"),
        ]
    }
    messages = []
    async def receive():
        return {"type": "http.request"}
    async def send(message):
        messages.append(message)
        
    await cors_app(scope, receive, send)
    print(messages)

if __name__ == "__main__":
    asyncio.run(test())
