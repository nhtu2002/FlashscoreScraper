import os
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from flashscorescraper import scrape_odds, scrape_event, scrape_event_info
from scraper.scraper_factory import ScraperFactory
from utils.detect_sport import detect_sport_from_url
from models.odds_filter import OddsFilter

app = FastAPI(title="Flashscore Scraper API")

# Cho phép file HTML (mở từ máy tính hoặc web khác) gọi API không bị lỗi CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Flashscore Scraper API is running!"}

@app.get("/api/scrape")
def run_scraper(
    action: str = Query(..., description="event | odds | event-info | league"),
    url: str = Query(..., description="Link trận đấu hoặc giải đấu Flashscore"),
    sport: Optional[str] = Query(None, description="football, tennis, volleyball..."),
    engine: str = Query("playwright", description="playwright hoặc curl"),
    with_stats: bool = Query(False, description="Lấy thêm thống kê trận đấu (chỉ dùng cho action=event)"),
    odds_types: Optional[str] = Query(None, description="Các loại kèo cách nhau dấu phẩy, vd: 1x2-odds,over-under")
):
    try:
        detected_sport = sport if sport else detect_sport_from_url(url)

        if action == "event":
            return scrape_event(url, sport=detected_sport, engine=engine, with_stats=with_stats)

        elif action == "odds":
            odds_list = [x.strip() for x in odds_types.split(",")] if odds_types else []
            odds_filter = OddsFilter(odds=odds_list, bookmakers=[]) if odds_list else None
            return scrape_odds(url, sport=detected_sport, engine=engine, odds_filter=odds_filter)

        elif action == "event-info":
            return scrape_event_info(url, sport=detected_sport, engine=engine)

        elif action == "league":
            with ScraperFactory.create_scraper(engine_type=engine, sport_type=detected_sport, timeout=20) as scraper:
                scraper.event_url = url
                return scraper.fetch_and_parse_league(url)

        else:
            raise HTTPException(status_code=400, detail="Action không hợp lệ. Chọn: event, odds, event-info, league")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
