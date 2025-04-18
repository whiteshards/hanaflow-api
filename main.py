from fastapi import FastAPI, HTTPException, Query
from typing import List, Dict, Any, Optional
import asyncio
import logging

from pydantic import BaseModel, Field
import traceback # For more detailed error logging

# Import scrapers
from scrapers.hianime import HiAnimeScraper

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Pydantic Models ---

class StreamSource(BaseModel):
    name: str
    url: Optional[str] = None
    type: Optional[str] = None # e.g., 'sub', 'dub'
    referer: Optional[str] = None # Required referer if url is not a direct link
    isDirectLink: bool = False # Indicates if the URL is likely directly playable

class EpisodeServer(BaseModel):
    name: str
    id: str
    category: Optional[str] = None # e.g., 'sub', 'dub'
    sources: List[StreamSource] = []

class EpisodeDetail(BaseModel):
    number: Optional[str] = None
    title: Optional[str] = None
    url: Optional[str] = None
    id: Optional[str] = None # Episode ID used by the source
    thumbnail: Optional[str] = None
    servers: List[EpisodeServer] = []

class EpisodeResponse(BaseModel):
    source: str
    anime_id: str
    episodes: List[EpisodeDetail]

# --- FastAPI App ---

app = FastAPI(
    title="HanaFlow API",
    description="API for scraping anime, movies, and other content.",
    version="0.1.0"
)

# Instantiate scrapers
# In the future, this could be dynamically loaded
available_scrapers = {
    "hianime": HiAnimeScraper()
}

@app.get("/search",
         response_model=List[Dict[str, Any]],
         summary="Search across all available sources",
         description="Performs a search query against all configured scrapers and returns combined results.")
async def search_content(
    query: str = Query(..., min_length=1, description="The search term for anime, movies, etc.")
):
    """
    Searches for content across different sources.

    - **query**: The search string (required).
    """
    if not query:
        raise HTTPException(status_code=400, detail="Query parameter cannot be empty.")

    logging.info(f"Received search request for query: '{query}'")

    scraper_tasks = []
    for source_name, scraper_instance in available_scrapers.items():
        # Using asyncio.to_thread for potentially blocking I/O operations in scrapers
        scraper_tasks.append(asyncio.to_thread(scraper_instance.search, query))

    try:
        # Run all scraper searches concurrently
        all_results_lists = await asyncio.gather(*scraper_tasks, return_exceptions=True)
    except Exception as e:
        logging.exception(f"Unexpected error during asyncio.gather for query '{query}': {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while processing scrapers.")

    combined_results = []
    for i, result_list in enumerate(all_results_lists):
        source_name = list(available_scrapers.keys())[i] # Get corresponding source name

        if isinstance(result_list, Exception):
            # Handle exceptions raised by individual scrapers during gather
            logging.error(f"Scraper '{source_name}' failed for query '{query}': {result_list}")
            combined_results.append({
                "source": source_name,
                "status": "error",
                "data": None,
                "error": f"Scraper execution failed: {result_list}"
            })
        elif isinstance(result_list, list):
             # If the scraper returned a list (even if it's an error list from within the scraper)
            if not result_list:
                 # Scraper ran successfully but found no results
                 logging.info(f"Scraper '{source_name}' found no results for query '{query}'.")
                 # Optionally add an entry indicating no results, or just omit it
                 # combined_results.append({
                 #     "source": source_name,
                 #     "status": "no_results",
                 #     "data": [],
                 #     "error": None
                 # })
            else:
                combined_results.extend(result_list) # Add the list of results/errors from the scraper
        else:
            # Handle unexpected return types from scrapers
            logging.error(f"Scraper '{source_name}' returned unexpected type for query '{query}': {type(result_list)}")
            combined_results.append({
                "source": source_name,
                "status": "error",
                "data": None,
                "error": "Scraper returned unexpected data type."
            })


    if not combined_results:
        # If after processing all scrapers, there are still no results or only errors leading to empty list
        logging.info(f"No results found across all scrapers for query: '{query}'")
        # Return 200 OK with empty list as per response_model,
        # or raise 404 if preferred:
        # raise HTTPException(status_code=404, detail="No results found for the given query.")

    logging.info(f"Search completed for query: '{query}'. Returning {len(combined_results)} result entries.")
    return combined_results

@app.get("/episodes",
         response_model=EpisodeResponse, # Use the new response model
         summary="Get detailed episode list with streaming sources for a specific anime",
         description="Fetches all episodes, available servers, and streaming source URLs for a given anime ID from a specific source.")
async def get_episodes(
    source: str = Query(..., description="The scraper source to use (e.g., 'hianime')."),
    anime_id: str = Query(..., description="The internal ID of the anime from the specified source (obtained from /search results)."),
    anime_url: str = Query(..., description="The URL of the anime's main page on the source site (obtained from /search results, used as referer).")
):
    """
    Retrieves detailed episode information including streaming links.

    - **source**: The name of the scraper source (e.g., 'hianime').
    - **anime_id**: The ID the source uses for the anime.
    - **anime_url**: The anime's page URL on the source website.
    """
    logging.info(f"Received episode request for source: '{source}', anime_id: '{anime_id}'")

    if source not in available_scrapers:
        raise HTTPException(status_code=400, detail=f"Invalid source specified. Available sources: {list(available_scrapers.keys())}")

    scraper_instance = available_scrapers[source]

    # Check if the scraper has the required methods (simple check)
    if not all(hasattr(scraper_instance, method) for method in ['_get_episodes', '_get_servers', '_get_source_url']):
         logging.error(f"Scraper '{source}' is missing required methods for episode detail fetching.")
         raise HTTPException(status_code=501, detail=f"Source '{source}' does not support detailed episode fetching.")

    detailed_episodes: List[EpisodeDetail] = []

    try:
        # 1. Get the basic episode list
        # Use asyncio.to_thread as scraper methods are potentially blocking
        base_episodes = await asyncio.to_thread(scraper_instance._get_episodes, anime_id, anime_url)

        if not base_episodes:
            logging.warning(f"No base episodes found for source '{source}', anime_id '{anime_id}'.")
            # Return empty list if scraper finds none, rather than 404
            return EpisodeResponse(source=source, anime_id=anime_id, episodes=[])

        # 2. Concurrently fetch servers and sources for each episode
        server_tasks = []
        episode_map = {} # To map results back to episodes

        for index, ep in enumerate(base_episodes):
            ep_id = ep.get('id')
            if ep_id:
                # Store task and original episode data to reconstruct later
                server_tasks.append(asyncio.to_thread(scraper_instance._get_servers, ep_id, anime_url))
                episode_map[index] = ep # Map task index to original episode data
            else:
                 # If episode has no ID, create its detail entry without servers
                 detailed_episodes.append(EpisodeDetail(**ep, servers=[]))


        # Run server fetching concurrently
        server_results = await asyncio.gather(*server_tasks, return_exceptions=True)

        # 3. Process server results and fetch source URLs concurrently
        source_tasks = []
        server_map = {} # Map source task index back to server and episode index

        task_index = 0
        # Need to iterate through server_results and map back to original episodes
        processed_indices = set() # Keep track of episodes already added to detailed_episodes

        for i, servers_or_error in enumerate(server_results):
            original_ep_index = list(episode_map.keys())[i] # Get the original episode index this result corresponds to
            original_ep_data = episode_map[original_ep_index]

            # Create detail object only if not already created (for episodes without IDs)
            if original_ep_index not in processed_indices:
                 episode_detail = EpisodeDetail(**original_ep_data, servers=[])
                 processed_indices.add(original_ep_index)
            else:
                 # Find the existing detail object (this part is tricky, maybe build the list at the end)
                 # Let's rebuild the detailed_episodes list at the end for simplicity
                 continue # Skip processing here, will handle later


            if isinstance(servers_or_error, Exception):
                logging.error(f"Failed to get servers for episode_id '{original_ep_data.get('id')}' (Anime: {anime_id}): {servers_or_error}")
                # Add episode detail even if servers fail
            elif isinstance(servers_or_error, list):
                for server in servers_or_error:
                    server_id = server.get('id')
                    if server_id:
                         # Prepare server detail, sources will be added later
                        server_detail = EpisodeServer(**server, sources=[])
                        episode_detail.servers.append(server_detail) # Add server to the current episode detail
                        # Add task to fetch sources for this server, passing server name
                        source_tasks.append(asyncio.to_thread(scraper_instance._get_source_url, server_detail.name, server_id, anime_url))
                        # Map task index back to the server object reference
                        server_map[task_index] = {'server_obj': server_detail}
                        task_index += 1
                    else:
                        logging.warning(f"Server found without ID for episode '{original_ep_data.get('id')}': {server.get('name')}")

        # Rebuild detailed_episodes list ensuring correct order and inclusion of episodes without IDs
        final_detailed_episodes = []
        server_results_map = {list(episode_map.keys())[i]: res for i, res in enumerate(server_results)}

        for index, ep_data in enumerate(base_episodes):
             episode_detail = EpisodeDetail(**ep_data, servers=[]) # Start fresh for each episode
             if index in server_results_map: # Check if servers were fetched for this episode
                 servers_or_error = server_results_map[index]
                 if isinstance(servers_or_error, list):
                     for server in servers_or_error:
                         server_id = server.get('id')
                         if server_id:
                             # Find the corresponding server_detail object created earlier (this mapping is complex)
                             # It's easier to just create the server objects here again
                             server_detail = EpisodeServer(**server, sources=[])
                             episode_detail.servers.append(server_detail)
                         else:
                              logging.warning(f"Server found without ID for episode '{ep_data.get('id')}': {server.get('name')}")

             final_detailed_episodes.append(episode_detail)


        # Run source fetching concurrently (using the already prepared tasks and server_map)
        source_results = await asyncio.gather(*source_tasks, return_exceptions=True)

        # 4. Populate sources into the server objects within final_detailed_episodes
        for i, source_url_or_error in enumerate(source_results):
             map_info = server_map[i]
             server_obj_ref = map_info['server_obj'] # This reference might be stale if we rebuilt the list

             # We need to find the correct server object in final_detailed_episodes to update
             # This requires iterating through final_detailed_episodes and their servers... complex
             # Let's simplify: Fetch sources sequentially *after* getting servers, or restructure

             # --- Simplified Approach: Fetch sources sequentially after getting servers ---
             # This avoids the complex mapping issue but is less concurrent

             # (Alternative logic would go here - fetch sources sequentially inside the server loop)

             # --- Sticking with concurrent approach, but fixing mapping ---
             # Find the correct server object in final_detailed_episodes based on server_id
             target_server_id = server_obj_ref.id
             found = False
             for ep_detail in final_detailed_episodes:
                 for server_detail in ep_detail.servers:
                     if server_detail.id == target_server_id:
                         source_info = source_url_or_error # This now returns a dict or an Exception
                         if isinstance(source_info, Exception):
                             logging.error(f"Failed to get source URL for server_id '{server_detail.id}': {source_info}")
                         elif isinstance(source_info, dict) and source_info.get("url"):
                             # Populate StreamSource using the dictionary returned by _get_source_url
                             server_detail.sources.append(StreamSource(
                                 name=server_detail.name,
                                 url=source_info.get("url"),
                                 type=server_detail.category,
                                 referer=source_info.get("referer"),
                                 isDirectLink=source_info.get("isDirectLink", False)
                             ))
                         else:
                             # Handle cases where _get_source_url returned None or an empty dict
                             logging.warning(f"No valid source info returned for server_id '{server_detail.id}' (Name: {server_detail.name})")
                         found = True
                         break
                 if found: break


        # Sort detailed_episodes by episode number if possible
        def sort_key(ep):
            try:
                # Handle potential non-numeric episode numbers like 'OVA' or 'Movie'
                num_str = str(ep.number).strip()
                return float(num_str) if num_str.replace('.', '', 1).isdigit() else float('inf')
            except (ValueError, TypeError):
                return float('inf') # Place non-numeric/unparseable ones at the end
        final_detailed_episodes.sort(key=sort_key)


        logging.info(f"Episode details processing complete for source '{source}', anime_id '{anime_id}'.")
        return EpisodeResponse(source=source, anime_id=anime_id, episodes=final_detailed_episodes)

    except (ConnectionError, ValueError, RuntimeError) as e:
        # Handle errors from the initial _get_episodes call or other scraper issues
        logging.error(f"Scraper error for source '{source}', anime_id '{anime_id}': {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=502, detail=f"Error communicating with source or processing data: {e}")
    except Exception as e:
        # Catch-all for unexpected errors
        logging.exception(f"Unexpected error fetching episodes for source '{source}', anime_id '{anime_id}': {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected internal error occurred: {e}")


# Basic root endpoint for health check or info
@app.get("/", include_in_schema=False)
async def root():
    return {"message": "HanaFlow API is running."}

# To run the server (using uvicorn):
# uvicorn main:app --reload