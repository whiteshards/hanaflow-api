from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List, Optional
from manga_scrapers.comick import ComickScraper
from manga_scrapers.nhentai import NHentaiScraper
import time
import math
from pydantic import BaseModel

app = FastAPI(
    title="Manga Search API",
    description="API for searching manga from different sources",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize scrapers
comick_scraper = ComickScraper()
nhentai_scraper = NHentaiScraper()

# Dictionary to store scrapers by name
scrapers = {
    "comick": comick_scraper,
    "nhentai": nhentai_scraper
}

class MangaResponse(BaseModel):
    totalResults: int
    page: int
    limit: int
    source: str
    query: Optional[str] = None
    results: List[Dict[str, Any]]
    executionTimeMs: int

def paginate_results(results: List[Dict[str, Any]], page: int, limit: int) -> List[Dict[str, Any]]:
    """Paginate results based on page and limit parameters."""
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit

    if start_idx >= len(results):
        return []

    return results[start_idx:end_idx]

@app.get("/")
async def root():
    return {
        "message": "Welcome to the Manga Search API",
        "documentation": "/docs",
        "version": "1.0.0"
    }

@app.get("/api/manga/search", response_model=MangaResponse)
async def search_manga(
    q: str = Query(..., description="Search query"),
    source: str = Query(..., description="Source to search (comick, nhentai)"),
    page: Optional[int] = Query(1, description="Page number", ge=1),
    limit: Optional[int] = Query(20, description="Results per page", ge=1, le=100)
):
    start_time = time.time()

    # Validate source
    if source not in scrapers:
        raise HTTPException(status_code=400, detail=f"Invalid source. Available sources: {', '.join(scrapers.keys())}")

    # Get the appropriate scraper
    scraper = scrapers[source]

    try:
        # Search manga
        results = scraper.search_manga(q)

        # Add source to each result
        for result in results:
            result["source"] = source

        # Paginate results
        paginated_results = paginate_results(results, page, limit)

        # Calculate execution time
        execution_time_ms = int((time.time() - start_time) * 1000)

        # Prepare response
        response = {
            "totalResults": len(results),
            "page": page,
            "limit": limit,
            "source": source,
            "query": q,
            "results": paginated_results,
            "executionTimeMs": execution_time_ms
        }

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching manga: {str(e)}")

@app.get("/api/manga/popular", response_model=MangaResponse)
async def get_popular_manga(
    source: str = Query(..., description="Source to fetch from (comick, nhentai)"),
    page: Optional[int] = Query(1, description="Page number", ge=1),
    limit: Optional[int] = Query(20, description="Results per page", ge=1, le=100)
):
    start_time = time.time()

    # Validate source
    if source not in scrapers:
        raise HTTPException(status_code=400, detail=f"Invalid source. Available sources: {', '.join(scrapers.keys())}")

    # Get the appropriate scraper
    scraper = scrapers[source]

    try:
        # Get popular manga
        results = scraper.get_popular_manga()

        # Add source to each result
        for result in results:
            result["source"] = source

        # Paginate results
        paginated_results = paginate_results(results, page, limit)

        # Calculate execution time
        execution_time_ms = int((time.time() - start_time) * 1000)

        # Prepare response
        response = {
            "totalResults": len(results),
            "page": page,
            "limit": limit,
            "source": source,
            "results": paginated_results,
            "executionTimeMs": execution_time_ms
        }

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching popular manga: {str(e)}")

@app.get("/api/manga/latest", response_model=MangaResponse)
async def get_latest_manga(
    source: str = Query(..., description="Source to fetch from (comick, nhentai)"),
    page: Optional[int] = Query(1, description="Page number", ge=1),
    limit: Optional[int] = Query(20, description="Results per page", ge=1, le=100)
):
    start_time = time.time()

    # Validate source
    if source not in scrapers:
        raise HTTPException(status_code=400, detail=f"Invalid source. Available sources: {', '.join(scrapers.keys())}")

    # Get the appropriate scraper
    scraper = scrapers[source]

    try:
        # Get latest manga
        results = scraper.get_latest_manga()

        # Add source to each result
        for result in results:
            result["source"] = source

        # Paginate results
        paginated_results = paginate_results(results, page, limit)

        # Calculate execution time
        execution_time_ms = int((time.time() - start_time) * 1000)

        # Prepare response
        response = {
            "totalResults": len(results),
            "page": page,
            "limit": limit,
            "source": source,
            "results": paginated_results,
            "executionTimeMs": execution_time_ms
        }

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching latest manga: {str(e)}")

@app.get("/details")
async def get_details(
    source: str,
    id: str
):
    """
    Get detailed information about a manga/anime by ID from specified source

    - **source**: Source name (nhentai, comick, etc.)
    - **id**: ID of the manga/anime
    """
    try:
        if source == "nhentai":
            scraper = NHentaiScraper()
            manga = {"id": id, "url": f"/g/{id}/"}
            details = scraper.get_manga_details(manga)

            # Get chapter information
            chapters = scraper.get_chapters(details)
            details["chapters"] = chapters

            return details

        elif source == "comick":
            scraper = ComickScraper()
            manga = {"id": id, "url": f"/comic/{id}#"}
            details = scraper.get_manga_details(manga)

            # Get chapter information
            chapters = scraper.get_chapters(details)
            details["chapters"] = chapters

            return details

        else:
            raise HTTPException(status_code=400, detail=f"Unknown source: {source}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting details: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)