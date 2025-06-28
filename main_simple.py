from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(title="キャバトレ API")

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 一時的に全許可
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "キャバトレ API is running! 🍾"}

@app.get("/health")
async def health():
    return {"status": "healthy", "api_key_exists": bool(os.getenv("GOOGLE_API_KEY"))}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))