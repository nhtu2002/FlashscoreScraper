import os
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

from flashscorescraper import scrape_odds, scrape_event, scrape_event_info
from scraper.scraper_factory import ScraperFactory
from utils.detect_sport import detect_sport_from_url
from models.odds_filter import OddsFilter

app = FastAPI(title="Flashscore Scraper API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def serve_ui():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"status": "ok", "message": "API dang chay"}

def scrape_homepage_matches(target_url: str = "https://www.flashscore.com/"):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 2000}
        )
        page = context.new_page()
        page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_selector(".event__match", timeout=15000)

        # Cuộn trang để Flashscore tải đầy đủ các trận bên dưới
        for _ in range(4):
            page.mouse.wheel(0, 2500)
            page.wait_for_timeout(800)

        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")
    matches = []
    current_league = "Unknown League"

    # Duyệt tuần tự qua từng tiêu đề giải đấu và từng dòng trận đấu
    elements = soup.select(".wcl-header_u3QP5, .event__header, .event__match")
    for el in elements:
        classes = el.get("class", [])
        if "event__match" not in classes:
            # Lấy tên quốc gia + giải đấu
            texts = [t.strip() for t in el.stripped_strings if t.strip() not in ("Standings", "Draw")]
            if texts:
                current_league = " - ".join(texts[:2])
        else:
            match_id = el.get("id", "").replace("g_1_", "")
            time_el = el.select_one(".event__time, .event__stage--block")
            status = time_el.get_text(strip=True) if time_el else ""

            home_el = el.select_one(".event__homeParticipant, .event__participant--home")
            away_el = el.select_one(".event__awayParticipant, .event__participant--away")
            home = home_el.get_text(strip=True) if home_el else ""
            away = away_el.get_text(strip=True) if away_el else ""

            score_h_el = el.select_one(".event__score--home")
            score_a_el = el.select_one(".event__score--away")
            score_h = score_h_el.get_text(strip=True) if score_h_el else "-"
            score_a = score_a_el.get_text(strip=True) if score_a_el else "-"

            is_live = "event__match--live" in classes or "'" in status or status in ("Half Time", "HT")
            is_finished = "Finished" in status or "AET" in status or "Pen" in status

            state = "live" if is_live else ("finished" if is_finished else "scheduled")

            if home and away:
                matches.append({
                    "id": match_id,
                    "league": current_league,
                    "status": status,
                    "state": state,
                    "home": home,
                    "away": away,
                    "score": f"{score_h} - {score_a}",
                    "url": f"https://www.flashscore.com/match/{match_id}/" if match_id else ""
                })

    return {"total": len(matches), "matches": matches}

@app.get("/api/scrape")
def run_scraper(
    action: str = Query("home", description="home | event | odds | event-info | league"),
    url: str = Query("https://www.flashscore.com/", description="Link Flashscore"),
    sport: Optional[str] = Query(None),
    engine: str = Query("playwright"),
    with_stats: bool = Query(False),
    odds_types: Optional[str] = Query(None)
):
    try:
        if action == "home":
            return scrape_homepage_matches(url or "https://www.flashscore.com/")

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
            raise HTTPException(status_code=400, detail="Action không hợp lệ.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
