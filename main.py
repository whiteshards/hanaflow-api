from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List, Optional
from anime_scrapers.hanime_scraper import HanimeScraper
from anime_scrapers.hahomoe_scraper import HahoMoeSearcher
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
hanime_scraper = HanimeScraper()

# Dictionary to store scrapers by name
scrapers = {
    "comick": comick_scraper,
    "nhentai": nhentai_scraper,
    "hanime": hanime_scraper
}

# Dictionary to store anime scrapers by name
anime_scrapers = {
    "hanime": hanime_scraper,
    "hahomoe": HahoMoeSearcher()
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

@app.get("/api/filters")
async def get_filters(
    source: str = Query(..., description="Source to get filters for (comick, nhentai, hanime, hahomoe)")
):
    """
    Get available filters for a specific source

    - **source**: The source to get filters for (comick, nhentai, hanime, hahomoe)
    """
    start_time = time.time()

    # Validate all sources (manga and anime)
    all_sources = list(scrapers.keys()) + list(anime_scrapers.keys())
    unique_sources = list(dict.fromkeys(all_sources))

    if source not in unique_sources:
        raise HTTPException(status_code=400, detail=f"Invalid source. Available sources: {', '.join(unique_sources)}")

    try:
        if source == "comick":
            from manga_scrapers.comick import ComickFilters
            filters = ComickFilters.get_filters()
        elif source == "nhentai":
            filters = nhentai_scraper.get_filters()
        elif source == "hanime":
            filters = {
                "tags": [{"id": tag["id"], "name": tag["name"]} for tag in hanime_scraper.get_tags()],
                "brands": [{"id": brand["id"], "name": brand["name"]} for brand in hanime_scraper.get_brands()],
                "sorts": [{"title": sort[0], "value": sort[1]} for sort in hanime_scraper.get_sortable_list()],
                "tagsModes": [
                    {"title": "All tags must match (AND)", "value": "AND"},
                    {"title": "Any tag can match (OR)", "value": "OR"}
                ],
                "quality": hanime_scraper.QUALITY_LIST
            }
        elif source == "hahomoe":
            hahomoe_scraper = anime_scrapers["hahomoe"]
            filters = {
                "tags": [{"id": tag["id"], "name": tag["name"]} for tag in hahomoe_scraper.get_tags()],
                "sorts": [{"title": sort[0], "value": sort[1]} for sort in hahomoe_scraper.get_sortable_list()],
                "quality": hahomoe_scraper.quality_list
            }
        else:
            raise HTTPException(status_code=400, detail=f"Filters not available for source: {source}")

        # Calculate execution time
        execution_time_ms = int((time.time() - start_time) * 1000)

        # Prepare response
        response = {
            "source": source,
            "filters": filters,
            "executionTimeMs": execution_time_ms
        }

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting filters: {str(e)}")

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

@app.get("/api/manga/details")
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

@app.get("/api/manga/get-pages")
async def get_manga_pages(
    source: str = Query(..., description="Source to fetch from (comick, nhentai)"),
    id: str = Query(..., description="ID or chapter ID of the manga"),
    #chapter_id: Optional[str] = Query(None, description="Chapter ID for multi-chapter manga (optional)")
):
    """
    Get pages for a specific manga or chapter

    - **source**: Source name (nhentai, comick, etc.)
    - **id**: ID of the manga
    - **chapter_id**: Optional chapter ID for multi-chapter manga
    """
    start_time = time.time()
    chapter_id=id
    try:
        if source == "nhentai":
            scraper = NHentaiScraper()

            # Create a manga/chapter object with minimal info needed for the scraper
            if chapter_id:
                # Use chapter_id if provided
                chapter = {"id": chapter_id, "url": f"/g/{chapter_id}/"}
                pages = scraper.get_pages(chapter)
            else:
                # Otherwise, get the manga first, then its chapters, then pages of first chapter
                manga = {"id": id, "url": f"/g/{id}/"}
                details = scraper.get_manga_details(manga)
                chapters = scraper.get_chapters(details)

                if not chapters:
                    raise HTTPException(status_code=404, detail="No chapters found for this manga")

                pages = scraper.get_pages(chapters[0])

            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)

            # Return pages with full URLs
            return {
                "source": source,
                "manga_id": id,
                "chapter_id": chapter_id or (chapters[0]["id"] if 'chapters' in locals() else id),
                "pages": pages,
                "executionTimeMs": execution_time_ms
            }

        elif source == "comick":
            scraper = ComickScraper()

            # Handle chapter pages request
            if chapter_id:
                # Direct chapter request
                chapter = {"id": chapter_id, "url": f"/comic/{id}/{chapter_id}-chapter-1-en"}
                pages = scraper.get_pages(chapter_id)
            else:
                # Get manga details first
                #manga = {"id": id, "url": f"/comic/{id}#"}
                #details = scraper.get_manga_details(manga)

                # Get chapters
                #chapter = {"id": chapter_id, "url":}
                chapters = scraper.get_chapters(chapter_id)
                if not chapters:
                    raise HTTPException(status_code=404, detail="No chapters found for this manga")

                # Get pages for first chapter
                pages = scraper.get_pages(chapters[0])

            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)

            # Return pages with metadata
            return {
                "source": source,
                "manga_id": id,
                "chapter_id": chapter_id or (chapters[0]["id"] if 'chapters' in locals() else ""),
                "pages": pages,
                "executionTimeMs": execution_time_ms
            }

        else:
            raise HTTPException(status_code=400, detail=f"Unknown source: {source}")

    except Exception as e:
        # Log the error
        print(f"Error getting pages: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting pages: {str(e)}")



@app.get("/api/anime/search", response_model=MangaResponse)
async def search_anime(
    q: str = Query(..., description="Search query"),
    source: str = Query(..., description="Source to search (hanime, hahomoe)"),
    page: Optional[int] = Query(1, description="Page number", ge=1),
    limit: Optional[int] = Query(20, description="Results per page", ge=1, le=100)
):
    start_time = time.time()

    # Validate source
    if source not in anime_scrapers:
        raise HTTPException(status_code=400, detail=f"Invalid source. Available sources: {', '.join(anime_scrapers.keys())}")

    # Get the appropriate scraper
    scraper = anime_scrapers[source]

    try:
        # Search anime
        results = scraper.search_anime(q)

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
        raise HTTPException(status_code=500, detail=f"Error searching anime: {str(e)}")

@app.get("/api/anime/popular", response_model=MangaResponse)
async def get_popular_anime(
    source: str = Query(..., description="Source to fetch from (hanime,hahomoe)"),
    page: Optional[int] = Query(1, description="Page number", ge=1),
    limit: Optional[int] = Query(20, description="Results per page", ge=1, le=100)
):
    start_time = time.time()

    # Validate source
    if source not in anime_scrapers:
        raise HTTPException(status_code=400, detail=f"Invalid source. Available sources: {', '.join(anime_scrapers.keys())}")

    # Get the appropriate scraper
    scraper = anime_scrapers[source]

    try:
        # Get popular anime
        if source == "hahomoe":
            results = scraper.get_popular_anime(page)
        else:
            results = scraper.get_popular_anime()

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
        raise HTTPException(status_code=500, detail=f"Error fetching popular anime: {str(e)}")

@app.get("/api/anime/latest", response_model=MangaResponse)
async def get_latest_anime(
    source: str = Query(..., description="Source to fetch from (hanime,hahomoe)"),
    page: Optional[int] = Query(1, description="Page number", ge=1),
    limit: Optional[int] = Query(20, description="Results per page", ge=1, le=100)
):
    start_time = time.time()

    # Validate source
    if source not in anime_scrapers:
        raise HTTPException(status_code=400, detail=f"Invalid source. Available sources: {', '.join(anime_scrapers.keys())}")

    # Get the appropriate scraper
    scraper = anime_scrapers[source]

    try:
        # Get latest anime
        if source == "hahomoe":
            results = scraper.get_latest_anime(page)
        else:
            results = scraper.get_latest_anime()

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
        raise HTTPException(status_code=500, detail=f"Error fetching latest anime: {str(e)}")

@app.get("/api/anime/details")
async def get_anime_details(
    source: str = Query(..., description="Source to fetch from (hanime, hahomoe)"),
    id: str = Query(..., description="URL/ID of the anime")
):
    """
    Get detailed information about an anime including episodes

    - **source**: Source name (hanime, hahomoe)
    - **id**: URL/ID of the anime
    """
    start_time = time.time()

    # Validate source
    if source not in anime_scrapers:
        raise HTTPException(status_code=400, detail=f"Invalid source. Available sources: {', '.join(anime_scrapers.keys())}")

    # Get the appropriate scraper
    scraper = anime_scrapers[source]

    try:
        # Get anime details
        details = scraper.get_anime_details(id)

        if not details:
            raise HTTPException(status_code=404, detail=f"Anime not found: {id}")

        # Get episodes for this anime
        episodes = scraper.get_episodes(details)

        # Add episodes to details
        details["episodes"] = episodes

        # Calculate execution time
        execution_time_ms = int((time.time() - start_time) * 1000)

        # Add execution time to response
        details["executionTimeMs"] = execution_time_ms

        return details

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting anime details: {str(e)}")

@app.get("/api/anime/get-episode")
async def get_anime_episode(
    source: str = Query(..., description="Source to fetch from (hanime, hahomoe)"),
    id: str = Query(..., description="URL/ID of the anime episode")
):
    """
    Get streaming links for a specific anime episode

    - **source**: Source name (hanime, hahomoe)
    - **id**: URL/ID of the anime episode
    """
    start_time = time.time()

    # Validate source
    if source not in anime_scrapers:
        raise HTTPException(status_code=400, detail=f"Invalid source. Available sources: {', '.join(anime_scrapers.keys())}")

    # Get the appropriate scraper
    scraper = anime_scrapers[source]

    try:
        # Get video sources for the episode
        video_sources = scraper.get_video_sources(id)

        # Calculate execution time
        execution_time_ms = int((time.time() - start_time) * 1000)

        # Prepare response
        response = {
            "source": source,
            "episode_id": id,
            "streams": video_sources,
            "executionTimeMs": execution_time_ms
        }

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting anime episode data: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)