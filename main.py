from fastapi import FastAPI
from src.api.leaderboard import router as leaderboard_router
from src.api.trades import router as trades_router
from src.api.pnl import router as pnl_rounter
from src.api.positions import router as positions_router

app = FastAPI(title="Hyperliquid Trading Challenge API")

app.include_router(leaderboard_router)
app.include_router(trades_router)
app.include_router(pnl_rounter)
app.include_router(positions_router)

if __name__ == "__main__":
  import uvicorn
  uvicorn.run(app, host="0.0.0.0", port=8000)