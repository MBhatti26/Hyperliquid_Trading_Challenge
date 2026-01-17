from fastapi import FastAPI
from src.api.trades import router as trades_router

app = FastAPI(title="Hyperliquid Trading Challenge API")

app.include_router(trades_router)

if __name__ == "__main__":
  import uvicorn
  uvicorn.run(app, host="0.0.0.0", port=8000)