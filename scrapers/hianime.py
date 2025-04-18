import requests
from bs4 import BeautifulSoup
import cloudscraper
import logging

# Configure logging for potential issues during scraping
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

class HiAnimeScraper:
    def __init__(self):
        self.source_name = "hianime"
        self.base_url = "https://hianimez.to"
        self.search_url = f"{self.base_url}/search"
        # Use a session for potential performance improvements and cookie handling
        self.session = cloudscraper.create_scraper()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': self.base_url + "/"
        }
        self.ajax_headers = self.headers.copy()
        self.ajax_headers.update({
            'Accept': 'application/json, text/javascript, */*; q=0.01', # More specific for AJAX
            'X-Requested-With': 'XMLHttpRequest'
        })

    def _make_request(self, url, params=None, headers=None, is_ajax=False):
        """Helper function to make requests and handle basic errors."""
        try:
            current_headers = self.ajax_headers if is_ajax else self.headers
            if headers: # Allow overriding headers if needed
                current_headers = headers

            response = self.session.get(url, params=params, headers=current_headers, timeout=15) # Added timeout
            response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
            return response
        except requests.exceptions.Timeout:
            logging.error(f"Request timed out: {url}")
            raise ConnectionError(f"Request timed out for {url}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed for {url}: {e}")
            raise ConnectionError(f"Failed to connect to {url}: {e}")

    def _parse_search_results(self, soup):
        """Parses the search results page."""
        search_results_div = soup.select('div.film_list-wrap div.flw-item')
        results = []
        if not search_results_div:
            return results

        for item in search_results_div:
            try:
                title_elem = item.select_one('div.film-detail h3.film-name a')
                if not title_elem: continue

                title = title_elem.text.strip()
                url_path = title_elem.get('href', '').strip()
                # Remove query parameters from the path
                url_path = url_path.split('?')[0]
                if not url_path or not url_path.startswith('/'): continue
                full_url = self.base_url + url_path # Now constructed without query params

                poster_elem = item.select_one('div.film-poster img')
                poster = poster_elem['data-src'] if poster_elem and 'data-src' in poster_elem.attrs else None

                info_items = item.select('div.fd-infor span.fdi-item')
                item_type = info_items[0].text.strip() if len(info_items) > 0 else None
                year = info_items[1].text.strip() if len(info_items) > 1 else None

                results.append({
                    'name': title,
                    'url': full_url,
                    'poster_thumbnail': poster, # Keep thumbnail separate initially
                    'type': item_type,
                    'year': year
                })
            except Exception as e:
                logging.warning(f"Error parsing a search result item: {e}")
                continue
        return results

    def _get_details(self, url):
        """Gets detailed information for a specific anime URL."""
        try:
            response = self._make_request(url)
            soup = BeautifulSoup(response.text, 'html.parser')

            details = {'url': url} # Start with the URL

            # Extract Anime ID from URL (needed for episodes)
            # Extract Anime ID from URL (needed for episodes)
            # URL passed in should already be cleaned by _parse_search_results
            try:
                potential_id = url.split('-')[-1]
                if potential_id.isdigit():
                    details['id'] = potential_id
                else:
                    # Handle cases where the last part isn't the ID (maybe title has numbers?)
                    # Attempt to find the last numeric part
                    parts = url.split('-')
                    numeric_parts = [p for p in parts if p.isdigit()]
                    if numeric_parts:
                        details['id'] = numeric_parts[-1] # Take the last numeric part
                    else:
                         raise ValueError(f"Could not find numeric ID in URL parts: {parts}")

            except (IndexError, ValueError) as e:
                logging.warning(f"Could not extract valid anime ID from URL {url}: {e}")
                raise ValueError(f"Invalid anime URL format or non-numeric ID found: {url}")


            details['name'] = soup.select_one('h2.film-name').text.strip() if soup.select_one('h2.film-name') else None
            details['poster'] = soup.select_one('div.anisc-poster img')['src'] if soup.select_one('div.anisc-poster img') else None
            desc_elem = soup.select_one('div.film-description div.text')
            details['description'] = desc_elem.text.strip() if desc_elem else None

            # Extract other info
            other_info = {}
            info_div = soup.select_one('div.anisc-info')
            if info_div:
                for item in info_div.select('div.item'):
                    label_elem = item.select_one('span.item-head')
                    value_elem = item.select_one('span.name, div.text') # Handles different value structures
                    if label_elem and value_elem:
                        label = label_elem.text.strip().replace(':', '') # Clean label
                        value = value_elem.text.strip()
                        other_info[label] = value
            details['other_info'] = other_info

            return details

        except ConnectionError as e:
             # Propagate connection errors
             raise e
        except Exception as e:
            logging.error(f"Failed to get details for {url}: {e}")
            raise ValueError(f"Could not parse details page for {url}: {e}")


    def _get_episodes(self, anime_id, referer_url):
        """Gets the detailed list of episodes using the AJAX endpoint."""
        if not anime_id:
            raise ValueError("Anime ID is required to fetch episodes.")

        episode_list_url = f"{self.base_url}/ajax/v2/episode/list/{anime_id}"
        ajax_headers = self.ajax_headers.copy()
        ajax_headers['Referer'] = referer_url

        try:
            response = self._make_request(episode_list_url, headers=ajax_headers, is_ajax=True)
            ep_data = response.json()

            if 'status' not in ep_data or not ep_data['status'] or 'html' not in ep_data:
                logging.warning(f"Invalid episode list response format for anime ID {anime_id}: {ep_data}")
                raise ValueError("Invalid episode list response format")

            ep_soup = BeautifulSoup(ep_data['html'], 'html.parser')
            ep_items = ep_soup.select('a.ep-item')

            episodes = []
            for ep in ep_items:
                try:
                    ep_num = ep.get('data-number', None)
                    ep_title_attr = ep.get('title', '')
                    ep_title = f"Episode {ep_num}" if not ep_title_attr else ep_title_attr # Default title if needed
                    ep_url_path = ep.get('href', '')

                    if not ep_url_path: continue # Skip if no URL

                    ep_full_url = self.base_url + ep_url_path if ep_url_path.startswith('/') else ep_url_path

                    # Extract episode ID from URL like /watch/one-piece-108?ep=108118
                    episode_id = None
                    if "?ep=" in ep_full_url:
                        try:
                            episode_id = ep_full_url.split("?ep=")[-1]
                            if not episode_id.isdigit(): episode_id = None # Validate
                        except IndexError:
                            pass # ID not found

                    episode_data = {
                        'number': ep_num,
                        'title': ep_title,
                        'url': ep_full_url,
                        'id': episode_id, # This ID is needed to fetch servers/sources later
                        'thumbnail': ep.get('data-thumbnail') # Include thumbnail if available
                    }
                    episodes.append(episode_data)
                except Exception as e:
                    logging.warning(f"Error processing an episode item for anime {anime_id}: {e}")
                    continue # Skip this episode on error

            # Return the list of parsed episode dictionaries
            # Sorting might be needed depending on site order (e.g., episodes.sort(key=lambda x: int(x.get('number', 0))))
            return episodes

        except ConnectionError as e:
            raise e # Propagate connection errors
        except (ValueError, KeyError, requests.exceptions.JSONDecodeError) as e:
            logging.error(f"Failed to get or parse episodes for anime ID {anime_id}: {e}")
            raise ValueError(f"Could not retrieve or parse episodes for anime ID {anime_id}: {e}")
        except Exception as e:
            logging.error(f"Unexpected error getting episodes for anime ID {anime_id}: {e}")
            raise RuntimeError(f"Unexpected error fetching episodes: {e}")

    def _get_servers(self, episode_id, referer_url):
        """Gets available servers for a specific episode ID."""
        if not episode_id:
            raise ValueError("Episode ID is required to fetch servers.")

        servers_url = f"{self.base_url}/ajax/v2/episode/servers?episodeId={episode_id}"
        ajax_headers = self.ajax_headers.copy()
        ajax_headers['Referer'] = referer_url

        try:
            response = self._make_request(servers_url, headers=ajax_headers, is_ajax=True)
            servers_data = response.json()

            if 'status' not in servers_data or not servers_data['status'] or 'html' not in servers_data:
                logging.warning(f"Invalid servers response format for episode ID {episode_id}: {servers_data}")
                raise ValueError("Invalid servers response format")

            servers_soup = BeautifulSoup(servers_data['html'], 'html.parser')
            servers = []

            # Process each server type (sub, dub, etc.)
            for server_type_div in servers_soup.select('div.servers-sub, div.servers-dub, div.servers-raw, div.servers-softsub'): # Adjusted selectors
                server_category = server_type_div.get('class', ['unknown'])[0].replace('servers-', '') # Extract category
                server_items = server_type_div.select('div.item')

                for item in server_items:
                    try:
                        server_id = item.get('data-id')
                        server_name = item.text.strip()
                        # data-type might indicate 'iframe' or 'player' - could be useful later
                        server_link_type = item.get('data-type')

                        if server_id and server_name:
                            servers.append({
                                'id': server_id,
                                'name': server_name,
                                'category': server_category, # e.g., 'sub', 'dub'
                                'type': server_link_type # e.g., 'iframe'
                            })
                    except Exception as e:
                        logging.warning(f"Error processing a server item for episode {episode_id}: {e}")
                        continue

            return servers

        except ConnectionError as e:
            raise e # Propagate connection errors
        except (ValueError, KeyError, requests.exceptions.JSONDecodeError) as e:
            logging.error(f"Failed to get or parse servers for episode ID {episode_id}: {e}")
            raise ValueError(f"Could not retrieve or parse servers for episode ID {episode_id}: {e}")
        except Exception as e:
            logging.error(f"Unexpected error getting servers for episode ID {episode_id}: {e}")
            raise RuntimeError(f"Unexpected error fetching servers: {e}")

    def _extract_streamtape(self, url):
        """Extracts the direct video URL from a Streamtape embed URL."""
        try:
            # Normalize URL
            if not url.startswith("https://streamtape.com/e/"):
                 # Example: https://streamtape.com/v/QkGb8x8ZqkHkXqY/
                 parts = url.split('/')
                 tape_id = next((part for part in reversed(parts) if part), None) # Find last non-empty part
                 if not tape_id: raise ValueError("Could not extract Streamtape ID")
                 url = f"https://streamtape.com/e/{tape_id}"

            response = self._make_request(url) # Use standard headers, referer might not be needed here
            soup = BeautifulSoup(response.text, 'html.parser')
            target_line = "document.getElementById('robotlink')"
            script_tag = soup.find('script', string=lambda t: t and target_line in t)

            if not script_tag:
                logging.warning(f"Could not find target script tag on Streamtape page: {url}")
                return None

            script_content = script_tag.string
            # Extract the parts needed for the URL
            # Example: "document.getElementById('robotlink').innerHTML = '//streamtape.com/get_video?id=QkGb8x8ZqkHkXqY&expires=1713370715&ip=...' + ('&token=...');"
            # Or: "... + ('xcdd');"
            try:
                part1_raw = script_content.split("innerHTML = '")[1].split("'")[0]
                part2_raw = script_content.split("+ (")[1].split(")")[0]
                # Clean up part2 if it's like ('xyz')
                part2 = part2_raw.strip("'")

                if not part1_raw.startswith("//"): # Ensure it starts correctly
                    raise ValueError("Unexpected format for part1")

                video_url = f"https:{part1_raw}{part2}"
                return video_url
            except (IndexError, ValueError) as e:
                logging.error(f"Failed to parse Streamtape script content for {url}: {e}\nContent: {script_content}")
                return None

        except (ConnectionError, ValueError) as e:
            logging.error(f"Failed to extract Streamtape URL from {url}: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error extracting Streamtape URL from {url}: {e}")
            return None # Don't raise, just return None

    def _get_source_url(self, server_name, server_id, referer_url):
        """
        Gets the actual streaming source URL for a given server ID.
        Attempts extraction for supported servers (Streamtape).
        Returns a dictionary with url, isDirectLink, and referer.
        """
        if not server_id:
            raise ValueError("Server ID is required to fetch source URL.")

        source_ajax_url = f"{self.base_url}/ajax/v2/episode/sources?id={server_id}"
        ajax_headers = self.ajax_headers.copy()
        ajax_headers['Referer'] = referer_url

        source_info = {
            "url": None,
            "isDirectLink": False,
            "referer": None # Default referer is None unless needed
        }

        try:
            response = self._make_request(source_ajax_url, headers=ajax_headers, is_ajax=True)
            source_data = response.json()

            initial_link = source_data.get('link')
            if not initial_link:
                logging.warning(f"Invalid source response format or empty link for server ID {server_id}: {source_data}")
                return source_info # Return default info with None URL

            source_info["url"] = initial_link # Store initial link first

            # --- Attempt Extraction ---
            if "streamtape" in server_name.lower():
                logging.info(f"Attempting Streamtape extraction for: {initial_link}")
                direct_url = self._extract_streamtape(initial_link)
                if direct_url:
                    source_info["url"] = direct_url
                    source_info["isDirectLink"] = True
                    # Streamtape might not need a specific referer once extracted
                    source_info["referer"] = None # Or maybe initial_link? Test needed.
                    logging.info(f"Streamtape extraction successful: {direct_url}")
                else:
                    logging.warning(f"Streamtape extraction failed for: {initial_link}")
                    # Keep initial link, set referer to streamtape domain?
                    try:
                         source_info["referer"] = "https://" + initial_link.split('/')[2] + "/"
                    except IndexError:
                         source_info["referer"] = "https://streamtape.com/"


            # Check for HiAnime's specific names for MegaCloud servers
            elif server_name.lower() in ["hd-1", "hd-2"]:
                 from .megacloud_utils import MegaCloudExtractor
                 logging.info(f"Attempting MegaCloud extraction for server '{server_name}': {initial_link}")
                 
                 extractor = MegaCloudExtractor(self.session)
                 videos = extractor.get_videos_from_url(initial_link)
                 
                 if videos:
                     # Return the first video URL as direct link
                     source_info["url"] = videos[0].url
                     source_info["isDirectLink"] = True
                     source_info["referer"] = "https://megacloud.tv/"
                     logging.info(f"MegaCloud extraction successful: {videos[0].url}")
                 else:
                     logging.warning("MegaCloud extraction failed, returning embed link")
                     source_info["isDirectLink"] = False
                     source_info["referer"] = "https://megacloud.tv/"
                 if source_data.get('encrypted') and isinstance(encrypted_data, str):
                     decrypted_sources = decrypt_source_url(encrypted_data) # Call the utility
                     if decrypted_sources and isinstance(decrypted_sources, list) and decrypted_sources:
                         # Assuming the first source is the primary one (e.g., HLS master playlist)
                         direct_url = decrypted_sources[0].get('file')
                         if direct_url:
                             source_info["url"] = direct_url
                             source_info["isDirectLink"] = True # Mark as direct (likely HLS)
                             # Referer for HLS might be the embed domain
                             try:
                                 source_info["referer"] = "https://" + initial_link.split('/')[2] + "/"
                             except IndexError:
                                 source_info["referer"] = "https://megacloud.tv/" # Fallback
                             logging.info(f"MegaCloud decryption successful: {direct_url}")
                         else:
                             logging.warning("Decryption successful but no 'file' found in source.")
                             source_info["isDirectLink"] = False # Keep initial link
                             source_info["referer"] = "https://" + initial_link.split('/')[2] + "/"
                     else:
                         logging.warning(f"MegaCloud decryption failed for server ID {server_id}.")
                         source_info["isDirectLink"] = False # Keep initial link
                         source_info["referer"] = "https://" + initial_link.split('/')[2] + "/"
                 elif not source_data.get('encrypted'):
                      logging.info("MegaCloud source is not encrypted. Using initial link.")
                      # Use the initial link directly if not encrypted (should be rare)
                      source_info["url"] = initial_link
                      source_info["isDirectLink"] = True # Assume direct if not encrypted
                      source_info["referer"] = "https://" + initial_link.split('/')[2] + "/"
                 else:
                      logging.warning("MegaCloud source format unexpected (encrypted flag mismatch or sources not string).")
                      source_info["isDirectLink"] = False # Keep initial link
                      source_info["referer"] = "https://" + initial_link.split('/')[2] + "/"

            # Add other extractors here if needed (e.g., _extract_rapidcloud)

            else:
                 # For unknown servers, return the initial link and guess referer might be needed
                 logging.warning(f"No specific extractor for server '{server_name}'. Returning initial link: {initial_link}")
                 source_info["isDirectLink"] = False
                 # Guess referer might be the original anime page
                 source_info["referer"] = referer_url


            return source_info

        except ConnectionError as e:
            # Error fetching the *initial* link
            logging.error(f"Connection error fetching initial source link for server ID {server_id}: {e}")
            raise e # Propagate connection errors
        except (KeyError, requests.exceptions.JSONDecodeError) as e:
            logging.error(f"Failed to get or parse initial source link JSON for server ID {server_id}: {e}")
            # Return default info with None URL
            return source_info
        except Exception as e:
            logging.error(f"Unexpected error getting source URL for server ID {server_id}: {e}")
            # Don't raise, return default info
            return source_info


    def search(self, query):
        """
        Searches for anime, gets details and episode list for each result.
        Returns a list of dictionaries in a standardized format.
        """
        final_results = []
        try:
            params = {'keyword': query}
            search_response = self._make_request(self.search_url, params=params)
            search_soup = BeautifulSoup(search_response.text, 'html.parser')
            basic_results = self._parse_search_results(search_soup)

            if not basic_results:
                # Return empty list if no initial results found, not an error
                return []

            for basic_result in basic_results:
                anime_url = basic_result.get('url')
                if not anime_url:
                    continue # Skip if URL is missing

                result_data = {
                    "source": self.source_name,
                    "status": "success", # Assume success initially
                    "data": basic_result, # Start with basic info
                    "error": None
                }

                try:
                    # Fetch detailed info
                    details = self._get_details(anime_url)
                    result_data["data"].update(details) # Merge details

                    # Fetch episode list using the extracted ID
                    anime_id = details.get('id')
                    episodes_list = []
                    total_episodes = 0
                    if anime_id:
                        try:
                            episodes_list = self._get_episodes(anime_id, anime_url)
                            total_episodes = len(episodes_list)
                        except (ConnectionError, ValueError, RuntimeError) as ep_error:
                            # Log error fetching episodes but don't fail the whole result
                            logging.warning(f"Could not fetch episodes for {anime_url} (ID: {anime_id}): {ep_error}")
                            result_data["error"] = f"Failed to retrieve episodes: {ep_error}" # Add episode error info
                            # Keep status as success, but indicate episode issue in error field? Or change status?
                            # Let's keep status success but add error detail.
                    else:
                        logging.warning(f"Could not determine anime ID for {anime_url}, cannot fetch episodes.")
                        result_data["error"] = "Could not determine anime ID to fetch episodes."


                    result_data["data"]["episodes"] = episodes_list # Add episode list
                    result_data["data"]["totalEpisodes"] = total_episodes

                    # Add the extracted anime_id to the response data
                    result_data["data"]["anime_id"] = anime_id # Add the ID here

                    # Clean up redundant/intermediate fields if necessary
                    result_data["data"].pop('poster_thumbnail', None) # Remove thumbnail if full poster exists
                    result_data["data"].pop('id', None) # Remove the temporary internal 'id' key used during processing

                except (ConnectionError, ValueError, RuntimeError, Exception) as e:
                    # Handle errors during the _get_details phase or unexpected errors
                    # Ensure anime_id is None if details failed before ID extraction
                    result_data["data"]["anime_id"] = details.get('id') if 'details' in locals() and details else None
                    logging.warning(f"Failed to process result '{basic_result.get('name', 'N/A')}' ({anime_url}): {e}")
                    result_data["status"] = "error"
                    # Overwrite potential episode error if a more general details error occurred
                    result_data["error"] = f"Failed to retrieve full details: {e}"
                    result_data["data"]["episodes"] = [] # Ensure episodes list is empty on error
                    result_data["data"]["totalEpisodes"] = 0
                    # Keep basic data even if details/episodes fail
                    # result_data["data"] = basic_result # Reset to basic if preferred

                final_results.append(result_data)

            return final_results

        except ConnectionError as e:
            # If the initial search fails due to connection issues
            logging.error(f"Initial search connection failed for query '{query}': {e}")
            # Return a single error entry for the source
            return [{
                "source": self.source_name,
                "status": "error",
                "data": None,
                "error": f"Failed to connect to source: {e}"
            }]
        except Exception as e:
            # Catch any other unexpected errors during the search process
            logging.exception(f"An unexpected error occurred during search for query '{query}': {e}") # Log full traceback
             # Return a single error entry for the source
            return [{
                "source": self.source_name,
                "status": "error",
                "data": None,
                "error": f"An unexpected error occurred: {e}"
            }]
