import requests
import json
import re
import urllib.parse
import time
import base64
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

# --- Data Transfer Objects (Simulated using Dicts) ---
# These match the structure implied by the Kotlin DTOs and JSON responses

PopularResult = Dict[str, Any]
SearchResult = Dict[str, Any]
DetailsResult = Dict[str, Any]
SeriesResult = Dict[str, Any]
EpisodeResult = Dict[str, Any]
VideoLink = Dict[str, Any]
Track = Dict[str, str]
FilterSearchParams = Dict[str, Any]

# --- Placeholder Extractors ---
# (Keep placeholders as full implementation is complex and separate)
class BaseExtractor:
    def __init__(self, session: requests.Session, headers: Dict[str, str] = None):
        self.session = session
        self.headers = headers if headers else {}

class AllAnimeExtractor(BaseExtractor):
    def __init__(self, session: requests.Session, headers: Dict[str, str], site_url: str):
        super().__init__(session, headers)
        self.site_url = site_url
        # self.playlist_utils = PlaylistUtils(session, headers) # Placeholder

    def videoFromUrl(self, url: str, name: str) -> List[Dict[str, Any]]:
        print(f"[Placeholder] AllAnimeExtractor.videoFromUrl: {url}, Name: {name}")
        # TODO: Implement logic from references/AllAnimeExtractor.kt.txt
        # Fetch /getVersion, then clock.json, parse VideoLink, handle HLS/MP4/DASH
        return []

class GogoStreamExtractor(BaseExtractor):
    def videosFromUrl(self, serverUrl: str) -> List[Dict[str, Any]]:
        print(f"[Placeholder] GogoStreamExtractor.videosFromUrl: {serverUrl}")
        # TODO: Implement logic from references/GogoStreamExtractor.kt.txt
        # Fetch page, extract keys, decrypt ajax params, fetch ajax, decrypt sources
        return []

class DoodExtractor(BaseExtractor):
    def videosFromUrl(self, url: str, quality: str = None, redirect: bool = True) -> List[Dict[str, Any]]:
        print(f"[Placeholder] DoodExtractor.videosFromUrl: {url}")
        # TODO: Implement logic from references/DoodExtractor.kt.txt
        # Fetch page, extract pass_md5, generate token, fetch video URL
        return []

class OkruExtractor(BaseExtractor):
    def videosFromUrl(self, url: str, prefix: str = "", fixQualities: bool = True) -> List[Dict[str, Any]]:
        print(f"[Placeholder] OkruExtractor.videosFromUrl: {url}")
        # TODO: Implement logic from references/OkruExtractor.kt.txt
        # Fetch page, extract data-options, parse JSON/HLS/DASH
        return []

class Mp4uploadExtractor(BaseExtractor):
     def videosFromUrl(self, url: str, headers: Dict[str, str]) -> List[Dict[str, Any]]:
         print(f"[Placeholder] Mp4uploadExtractor for URL: {url}")
         # TODO: Implement logic from references/Mp4uploadExtractor.kt.txt (if provided)
         return []

class StreamlareExtractor(BaseExtractor):
    def videosFromUrl(self, url: str, prefix: str = "", suffix: str = "") -> List[Dict[str, Any]]:
        print(f"[Placeholder] StreamlareExtractor for URL: {url}")
        # TODO: Implement logic from references/StreamlareExtractor.kt.txt
        # POST to API, parse response, handle HLS/direct links
        return []

class FilemoonExtractor(BaseExtractor):
    def videosFromUrl(self, url: str, prefix: str = "") -> List[Dict[str, Any]]:
        print(f"[Placeholder] FilemoonExtractor for URL: {url}")
        # TODO: Implement logic from references/FilemoonExtractor.kt.txt (if provided)
        # Fetch page, unpack JS, extract m3u8 URL
        return []

class StreamWishExtractor(BaseExtractor):
    def videosFromUrl(self, url: str, videoNameGen=None) -> List[Dict[str, Any]]:
        print(f"[Placeholder] StreamWishExtractor for URL: {url}")
        # TODO: Implement logic from references/StreamWishExtractor.kt (1).txt
        # Fetch embed page, unpack JS, extract m3u8 URL and subtitles
        return []

# --- Playlist Utils Placeholder ---
class PlaylistUtils:
    def __init__(self, session: requests.Session, headers: Dict[str, str] = None):
        self.session = session
        self.headers = headers if headers is not None else {}

    def extractFromHls(self, playlistUrl: str, referer: str = "", videoNameGen=None, subtitleList: List[Track] = None, audioList: List[Track] = None) -> List[Dict[str, Any]]:
        print(f"[Placeholder] PlaylistUtils.extractFromHls: {playlistUrl}")
        # TODO: Implement HLS parsing logic from references/PlaylistUtils.kt.txt
        # Fetch playlist, parse #EXT-X-STREAM-INF, handle relative URLs
        # Return dummy data for now to avoid breaking video source fetching
        quality = "720p" if "720" in playlistUrl else "1080p" if "1080" in playlistUrl else "Unknown"
        name = videoNameGen(quality) if videoNameGen else quality
        return [{'url': playlistUrl, 'quality': name, 'headers': self.headers}]

    def extractFromDash(self, mpdUrl: str, videoNameGen=None, referer: str = "", subtitleList: List[Track] = None, audioList: List[Track] = None) -> List[Dict[str, Any]]:
        print(f"[Placeholder] PlaylistUtils.extractFromDash: {mpdUrl}")
        # TODO: Implement DASH parsing logic from references/PlaylistUtils.kt.txt
        return []

# --- Main Scraper Class ---
class AllAnimeScraper:
    # --- Constants ---
    PAGE_SIZE = 26

    # GraphQL Query Constants (Copied carefully, ensure formatting is exact)
    SEARCH_QUERY = "query ($search: SearchInput, $limit: Int, $page: Int, $translationType: VaildTranslationType, $countryOrigin: Country) { shows(search: $search, limit: $limit, page: $page, translationType: $translationType, countryOrigin: $countryOrigin) { edges { _id name englishName nativeName thumbnail slugTime type season score availableEpisodesDetail } } }"
# Note: Added more fields to SEARCH_QUERY based on parseAnime usage

    DETAILS_QUERY = "query ($_id: String!) { show(_id: $_id) { _id name englishName nativeName thumbnail description genres studios season { quarter year } status score type availableEpisodesDetail { sub dub } } }"
# Note: Added more fields to DETAILS_QUERY based on animeDetailsParse usage

    EPISODES_QUERY = "query ($_id: String!) { show(_id: $_id) { _id availableEpisodesDetail { sub dub } } }"

    STREAMS_QUERY = "query ($showId: String!, $translationType: VaildTranslationType!, $episodeString: String!) { episode(showId: $showId, translationType: $translationType, episodeString: $episodeString) { sourceUrls } }"
# Note: Simplified STREAMS_QUERY based on Kotlin usage (sourceUrls is the primary need)

    # Hoster Names (from Kotlin companion object)
    INTERAL_HOSTER_NAMES = [
        "Default", "Ac", "Ak", "Kir", "Rab", "Luf-mp4",
        "Si-Hls", "S-mp4", "Ac-Hls", "Uv-mp4", "Pn-Hls",
    ]
    ALT_HOSTER_NAMES = [
        "player", "vidstreaming", "okru", "mp4upload",
        "streamlare", "doodstream", "filemoon", "streamwish",
    ]

    # --- Initialization ---
    def __init__(self):
        # Preferences (Mimicking Kotlin SharedPreferences)
        self.preferences = {
            "preferred_domain": "https://api.allanime.day",
            "preferred_site_domain": "https://allanime.to",
            "preferred_sub": "sub",
            "preferred_title_style": "romaji",
            "preferred_quality": "1080",
            "preferred_server": "site_default",
            "hoster_selection": {"default", "ac", "ak", "kir", "luf-mp4", "si-hls", "s-mp4", "ac-hls"},
            "alt_hoster_selection": {"player", "vidstreaming", "okru", "mp4upload", "streamlare", "doodstream", "filemoon", "streamwish"}
        }

        self.base_url = self.preferences["preferred_domain"]
        self.site_url = self.preferences["preferred_site_domain"]
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Accept': '*/*',
            # 'Content-Type': 'application/json', # Let requests handle this based on json=
            'Origin': self.site_url,
            'Referer': f"{self.site_url}/", # Referer should be site_url
        }

        # Initialize extractors
        self.all_anime_extractor = AllAnimeExtractor(self.session, self.headers, self.site_url)
        self.gogo_stream_extractor = GogoStreamExtractor(self.session)
        self.dood_extractor = DoodExtractor(self.session)
        self.okru_extractor = OkruExtractor(self.session)
        self.mp4upload_extractor = Mp4uploadExtractor(self.session, self.headers)
        self.streamlare_extractor = StreamlareExtractor(self.session)
        self.filemoon_extractor = FilemoonExtractor(self.session, self.headers)
        self.streamwish_extractor = StreamWishExtractor(self.session, self.headers)
        self.playlist_utils = PlaylistUtils(self.session, self.headers)

    # --- Private Helper Methods ---

    def _get_preference(self, key: str) -> Any:
        """Helper to get preference value."""
        return self.preferences.get(key)

    def _build_post_request(self, data_object: Dict[str, Any]) -> requests.PreparedRequest:
        """Builds a POST request with JSON payload, matching Kotlin's buildPost."""
        # payload = json.dumps(data_object) # Use requests' json parameter instead
        post_headers = self.headers.copy()
        # post_headers['Content-Length'] = str(len(payload)) # requests calculates this
        # post_headers['Content-Type'] = 'application/json; charset=utf-8' # requests sets this with json=
        post_headers['Host'] = urllib.parse.urlparse(self.base_url).netloc # Add Host header

        # Use requests' json parameter for automatic serialization and Content-Type
        req = requests.Request(
            'POST',
            f"{self.base_url}/api",
            headers=post_headers,
            json=data_object # Use json parameter here
        )
        return self.session.prepare_request(req)

    def _parse_anime(self, response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parses anime list from search or latest updates response (like Kotlin's parseAnime)."""
        anime_list = []
        shows = response_data.get('data', {}).get('shows', {})
        edges = shows.get('edges', [])

        title_style = self._get_preference("preferred_title_style")

        for edge in edges:
            # Kotlin uses 'ani' for the edge item directly in search results
            item = edge # Use the edge directly

            if not item or '_id' not in item:
                continue

            title = item.get('name', 'Unknown Title')
            if title_style == "eng":
                title = item.get('englishName') or title
            elif title_style == "native":
                title = item.get('nativeName') or title

            thumbnail_url = item.get('thumbnail')
            # Construct URL format similar to Kotlin for details/episode fetching
            # url = _id<&sep>slugTime<&sep>slug
            url = f"{item.get('_id')}<&sep>{item.get('slugTime', '')}<&sep>{self._slugify(item.get('name', ''))}"

            anime_list.append({
                'title': f"{title} [AllAnime]",
                'url': url,
                'poster': thumbnail_url,
                'source': 'allanime',
                # Add other potential fields if needed later from 'item'
                'type': item.get('type'),
                'year': item.get('season', {}).get('year'),
            })
        return anime_list

    def _slugify(self, text: str) -> str:
        """Converts text to a URL-friendly slug (like Kotlin's slugify)."""
        if not text: return ""
        text = text.lower()
        text = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
        text = re.sub(r'-{2,}', '-', text) # Replace multiple hyphens
        return text

    def _decrypt_source(self, source_url: str) -> str:
        """Decrypts the source URL if it's obfuscated (like Kotlin's decryptSource)."""
        if not source_url or not source_url.startswith("-"):
            return source_url

        try:
            # Logic from Kotlin: substringAfterLast('-').chunked(2).map{toInt(16).toByte()}.toByteArray().map{(it.toInt() xor 56).toChar()}.joinToString("")
            hex_part = source_url.split('-')[-1]
            if len(hex_part) % 2 != 0: # Ensure even length for hex decoding
                print(f"Warning: Odd length hex string in decryptSource: {hex_part}")
                return source_url # Cannot decode odd-length hex

            decoded_bytes = bytes.fromhex(hex_part)
            decrypted_bytes = bytes([b ^ 56 for b in decoded_bytes])
            return decrypted_bytes.decode('utf-8', errors='replace') # Use replace for potential decoding errors
        except ValueError as e: # Catch specific hex decoding errors
             print(f"Error decoding hex in decryptSource: {e}, URL: {source_url}")
             return source_url # Return original if decryption fails
        except Exception as e:
            print(f"Error decrypting source URL: {e}, URL: {source_url}")
            return source_url # Return original if decryption fails

    def _parse_status(self, status_string: Optional[str]) -> str:
        """Parses status string to a standard format (like Kotlin's parseStatus)."""
        status_map = {
            "Releasing": "Ongoing",
            "Finished": "Completed",
            "Not Yet Released": "Ongoing", # Treat as Ongoing
            "Cancelled": "Cancelled",
            "On Hiatus": "On Hiatus",
        }
        return status_map.get(status_string, "Unknown") if status_string else "Unknown"

    # --- Public Scraper Methods ---

    def search_anime(self, query: str, filters: Optional[FilterSearchParams] = None) -> List[Dict[str, Any]]:
        """Search for anime on AllAnime by title or filters."""
        print(f"🔍 Searching for '{query}' on AllAnime...")
        results = []
        page = 1
        # Pagination is handled by the API returning results until empty, not explicit page limit needed here.

        try:
            variables = {
                "search": {
                    "allowAdult": False, # Default values
                    "allowUnknown": False
                },
                "limit": self.PAGE_SIZE,
                "page": page,
                "translationType": self._get_preference("preferred_sub"),
                "countryOrigin": "ALL" # Default, filters might override
            }
            if query:
                variables["search"]["query"] = query
            else:
                # TODO: Implement filter logic based on AllAnimeFilters.kt.txt
                # This requires translating getSearchParameters and applying filter values
                print("⚠️ Filter search is not yet implemented for AllAnime.")
                # Example structure if filters were passed:
                # if filters:
                #     variables["search"]["season"] = filters.get("season", "all") # Example
                #     variables["countryOrigin"] = filters.get("origin", "ALL") # Example
                #     # ... add other filters (genres, types, year, sortBy)
                pass # Proceed with default search if no query and filters not implemented

            data = {
                "variables": variables,
                "query": self.SEARCH_QUERY
            }

            request = self._build_post_request(data)
            response = self.session.send(request, timeout=20) # Add timeout

            if response.status_code == 400:
                 print(f"❌ AllAnime search failed (400 Bad Request). Payload: {json.dumps(data)}")
                 with open("error.txt", "w") as n: n.write(str(data))
                 print(f"Response Text: {response.text[:500]}") # Print beginning of error response
                 return []
            response.raise_for_status() # Raise an exception for other bad status codes

            response_data = response.json()
            page_results = self._parse_anime(response_data)
            results.extend(page_results)

            # Note: AllAnime API doesn't seem to have explicit pagination info in search response.
            # The Kotlin code checks if results == PAGE_SIZE. We'll assume one page for CLI simplicity for now.
            # If pagination is needed, the API structure might require a different approach.

        except requests.exceptions.Timeout:
            print("❌ AllAnime search request timed out.")
        except requests.exceptions.RequestException as e:
            print(f"❌ AllAnime search failed: {e}")
            with open("error.txt", "w") as ne:
                ne.write(str(e))
            # Print response body if available for debugging
            if e.response is not None:
                print(f"Response status: {e.response.status_code}")
                try:
                    print(f"Response body: {e.response.text[:500]}")
                except Exception:
                    print("Could not read response body.")
        except json.JSONDecodeError:
            print("❌ Failed to parse JSON response from AllAnime search.")
        except Exception as e:
            import traceback
            print(f"An unexpected error occurred during AllAnime search: {e}")
            print(traceback.format_exc())

        return results

    def get_anime_details(self, url: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about an anime (like Kotlin's animeDetailsParse)."""
        print(f"📝 Getting details for {url} from AllAnime...")
        try:
            anime_id = url.split("<&sep>")[0]

            variables = {"_id": anime_id}
            data = {"variables": variables, "query": self.DETAILS_QUERY}

            request = self._build_post_request(data)
            response = self.session.send(request, timeout=15)
            response.raise_for_status()

            response_data: DetailsResult = response.json()
            show = response_data.get('data', {}).get('show')

            if not show:
                print("❌ No details found for this anime.")
                return None

            # --- Parse details similar to Kotlin ---
            title_style = self._get_preference("preferred_title_style")
            title = show.get('name', 'Unknown Title')
            if title_style == "eng":
                title = show.get('englishName') or title
            elif title_style == "native":
                title = show.get('nativeName') or title

            genres = show.get('genres') or []
            status = self._parse_status(show.get('status'))
            studios = show.get('studios') or []
            author = studios[0] if studios else None # Kotlin uses first studio as author

            description_raw = show.get('description', '')
            description = 'No description available'
            if description_raw:
                # Basic HTML cleaning like Jsoup in Kotlin
                temp_desc = description_raw.replace('<br>', '\n').replace('<br/>', '\n')
                description = re.sub(r'<[^>]+>', '', temp_desc).strip() # Remove HTML tags

            # Additional Info section
            info = {'Status': status} # Start with status
            show_type = show.get('type')
            if show_type: info['Type'] = show_type
            season_info = show.get('season')
            if season_info:
                info['Aired'] = f"{season_info.get('quarter', '-')} {season_info.get('year', '-')}"
            score = show.get('score')
            if score is not None: info['Score'] = f"{score}★"
            if studios: info['Studios'] = ", ".join(studios)
            # Add more fields if needed

            return {
                'id': anime_id,
                'url': url, # Keep original URL for episode fetching
                'title': f"{title} [AllAnime]", # Add source tag
                'poster': show.get('thumbnail'),
                'description': description,
                'genres': ", ".join(genres),
                'info': info,
                'source': 'allanime'
            }

        except requests.exceptions.Timeout:
            print("❌ AllAnime details request timed out.")
            return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to get anime details from AllAnime: {e}")
            return None
        except json.JSONDecodeError:
            print("❌ Failed to parse JSON response from AllAnime details.")
            return None
        except Exception as e:
            import traceback
            print(f"An unexpected error occurred during AllAnime details fetch: {e}")
            print(traceback.format_exc())
            return None

    def get_episodes(self, anime_details: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get episode list for an anime (like Kotlin's episodeListParse)."""
        if not anime_details or 'url' not in anime_details:
            print("❌ Invalid anime details. Cannot get episodes.")
            return []

        print(f"🎬 Getting episodes for {anime_details.get('title', 'anime')} from AllAnime...")
        episodes = []
        try:
            anime_id = anime_details['url'].split("<&sep>")[0]
            sub_pref = self._get_preference("preferred_sub")

            variables = {"_id": anime_id}
            data = {"variables": variables, "query": self.EPISODES_QUERY}

            request = self._build_post_request(data)
            response = self.session.send(request, timeout=15)
            response.raise_for_status()

            response_data: SeriesResult = response.json()
            show = response_data.get('data', {}).get('show')

            if not show:
                print("❌ No episode details found in API response.")
                return []

            available_episodes = show.get('availableEpisodesDetail', {})
            episode_list_raw = available_episodes.get(sub_pref, []) # Get sub or dub list

            if not episode_list_raw:
                 print(f"❌ No '{sub_pref}' episodes found for this anime.")
                 # Optionally, try the other type if one is empty
                 other_pref = "dub" if sub_pref == "sub" else "sub"
                 episode_list_raw = available_episodes.get(other_pref, [])
                 if episode_list_raw:
                     print(f"ℹ️ Found '{other_pref}' episodes instead.")
                     sub_pref = other_pref # Switch preference for this fetch
                 else:
                     return [] # Return empty if both are empty

            show_id = show.get('_id') # Get show ID for stream query

            for ep_str in episode_list_raw:
                # Construct JSON payload URL for get_video_sources
                episode_payload = {
                    "variables": {
                        "showId": show_id,
                        "translationType": sub_pref,
                        "episodeString": ep_str
                    },
                    "query": self.STREAMS_QUERY
                }
                episode_url_json = json.dumps(episode_payload)

                episodes.append({
                    'number': ep_str, # Keep as string, matches Kotlin
                    'title': f"Episode {ep_str} ({sub_pref})",
                    'url': episode_url_json, # Store JSON payload as URL
                    'source': 'allanime'
                    # 'date' and 'thumbnail' not available in this API response
                })

            # Sort episodes numerically (handle floats like "0.5")
            episodes.sort(key=lambda x: float(x['number']) if re.match(r'^-?\d+(\.\d+)?$', x['number']) else float('inf'))

            return episodes

        except requests.exceptions.Timeout:
            print("❌ AllAnime episodes request timed out.")
            return []
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to get episodes from AllAnime: {e}")
            return []
        except json.JSONDecodeError:
            print("❌ Failed to parse JSON response from AllAnime episodes.")
            return []
        except Exception as e:
            import traceback
            print(f"An unexpected error occurred during AllAnime episode fetch: {e}")
            print(traceback.format_exc())
            return []

    def get_video_sources(self, episode_url_payload: str) -> List[Dict[str, Any]]:
        """Get video sources for an episode (like Kotlin's getVideoList)."""
        print(f"🎥 Extracting video sources from AllAnime episode...")
        video_sources = []
        server_list: List[Tuple[Dict[str, Any], float]] = [] # Store as (server_info, priority)

        try:
            data = json.loads(episode_url_payload) # Parse the payload stored in the URL
            request = self._build_post_request(data)
            response = self.session.send(request, timeout=20)

            if response.status_code == 400:
                 print(f"❌ AllAnime stream fetch failed (400 Bad Request). Payload: {json.dumps(data)}")
                 print(f"Response Text: {response.text[:500]}")
                 return []
            response.raise_for_status()

            response_data: EpisodeResult = response.json()
            episode_data = response_data.get('data', {}).get('episode')

            if not episode_data or 'sourceUrls' not in episode_data:
                print("❌ No video sources found in API response.")
                return []

            raw_source_urls = episode_data.get('sourceUrls', [])
            if not isinstance(raw_source_urls, list):
                 print(f"❌ Unexpected format for sourceUrls: {type(raw_source_urls)}")
                 return []

            # --- Server Selection Logic (from Kotlin getVideoList) ---
            hoster_selection = self._get_preference("hoster_selection")
            alt_hoster_selection = self._get_preference("alt_hoster_selection")
            mappings = {
                "vidstreaming": ["vidstreaming", "https://gogo", "playgo1.cc", "playtaku", "vidcloud"],
                "doodstream": ["dood"], "okru": ["ok.ru", "okru"],
                "mp4upload": ["mp4upload.com"], "streamlare": ["streamlare.com"],
                "filemoon": ["filemoon", "moonplayer"], "streamwish": ["wish"],
            }

            temp_server_list = []
            for video_source in raw_source_urls:
                 # Ensure video_source is a dictionary
                 if not isinstance(video_source, dict):
                     print(f"Skipping invalid video source item: {video_source}")
                     continue

                 source_url_raw = video_source.get('sourceUrl', '')
                 source_url = self._decrypt_source(source_url_raw)
                 source_name_raw = video_source.get('sourceName', '')
                 source_name = source_name_raw.lower()
                 source_type = video_source.get('type', '')
                 priority = float(video_source.get('priority', 0.0)) # Ensure float

                 server_info = {'url': source_url, 'name': '', 'priority': priority, 'type': source_type, 'raw_name': source_name_raw}

                 # Check internal hosters
                 is_internal = False
                 if source_url.startswith("/apivtwo/"):
                     for name in self.INTERAL_HOSTER_NAMES:
                         if re.search(r'\b' + name.lower() + r'\b', source_name):
                             if name.lower() in hoster_selection:
                                 server_info['name'] = f"internal {source_name_raw}"
                                 temp_server_list.append((server_info, priority))
                                 is_internal = True
                                 break
                     if is_internal: continue # Skip other checks if matched internal

                 # Check player type
                 if source_type == "player" and "player" in alt_hoster_selection:
                     server_info['name'] = f"player@{source_name_raw}"
                     temp_server_list.append((server_info, priority))
                     continue # Skip other checks if matched player

                 # Check alternative hosters
                 matched_alt = False
                 for alt_hoster, url_matches in mappings.items():
                     if alt_hoster in alt_hoster_selection and any(match in source_url for match in url_matches):
                         server_info['name'] = alt_hoster
                         temp_server_list.append((server_info, priority))
                         matched_alt = True
                         break
                 # if not matched_alt:
                 #     print(f"Debug: Skipped server - URL: {source_url}, Name: {source_name_raw}, Type: {source_type}")


            # --- Extract Videos from Selected Servers ---
            # Note: This part calls placeholder extractors. Needs full implementation.
            extracted_video_list: List[Tuple[Dict[str, Any], float]] = [] # Store as (video_dict, priority)

            for server_info, priority in temp_server_list:
                s_name = server_info['name']
                s_url = server_info['url']
                s_raw_name = server_info['raw_name'] # Original name for internal extractor

                try:
                    videos = []
                    if s_name.startswith("internal "):
                        videos = self.all_anime_extractor.videoFromUrl(s_url, s_raw_name)
                    elif s_name.startswith("player@"):
                        # TODO: Implement player logic (needs /getVersion endpoint)
                        print(f"Player type extraction not implemented for: {s_url}")
                        # videos = [{'url': s_url, 'quality': f"Original ({s_name})", 'headers': self.headers}] # Basic placeholder
                    elif s_name == "vidstreaming":
                        videos = self.gogo_stream_extractor.videosFromUrl(s_url.replace("//", "https://"))
                    elif s_name == "doodstream":
                        videos = self.dood_extractor.videosFromUrl(s_url)
                    elif s_name == "okru":
                        videos = self.okru_extractor.videosFromUrl(s_url)
                    elif s_name == "mp4upload":
                        videos = self.mp4upload_extractor.videosFromUrl(s_url, self.headers)
                    elif s_name == "streamlare":
                        videos = self.streamlare_extractor.videosFromUrl(s_url)
                    elif s_name == "filemoon":
                        videos = self.filemoon_extractor.videosFromUrl(s_url, prefix="Filemoon:")
                    elif s_name == "streamwish":
                        videos = self.streamwish_extractor.videosFromUrl(s_url, videoNameGen=lambda q: f"StreamWish:{q}")

                    # Add extracted videos with their server priority
                    for video in videos:
                        # Ensure video is a dict before adding source and priority
                        if isinstance(video, dict):
                            video['source'] = 'allanime' # Add source identifier
                            extracted_video_list.append((video, priority))
                        elif hasattr(video, 'videoUrl') and hasattr(video, 'videoTitle'): # Handle Video object from placeholders
                             video_dict = {
                                 'url': video.videoUrl,
                                 'quality': video.videoTitle,
                                 'headers': video.headers,
                                 'source': 'allanime',
                                 'subtitles': [{'url': sub.url, 'language': sub.lang} for sub in getattr(video, 'subtitleTracks', [])]
                             }
                             extracted_video_list.append((video_dict, priority))


                except Exception as e:
                    print(f"Error extracting videos from server {s_name} ({s_url}): {e}")
                    import traceback
                    print(traceback.format_exc())
                    continue

            # --- Sort Videos (like Kotlin's prioritySort) ---
            pref_server = self._get_preference("preferred_server")
            quality_pref = self._get_preference("preferred_quality")
            sub_pref = self._get_preference("preferred_sub") # sub or dub

            def sort_key(video_tuple: Tuple[Dict[str, Any], float]):
                video_dict, server_priority = video_tuple
                quality = video_dict.get('quality', '').lower()

                # Score based on server preference
                server_score = 0
                if pref_server != "site_default":
                    # Check if quality string contains the preferred server name (case-insensitive)
                    if pref_server in quality:
                        server_score = 1 # Higher score if preferred server matches
                else:
                    # Use server priority if prefServer is site_default
                    # Higher priority value means lower preference in sorting (hence negative)
                    server_score = -server_priority

                # Score based on quality preference
                quality_score = 0
                if quality_pref in quality:
                    quality_score = 1 # Higher score if preferred quality matches

                # Score based on sub/dub preference (simple check in quality name)
                sub_dub_score = 0
                if sub_pref in quality:
                    sub_dub_score = 1

                # Return tuple for sorting (higher scores first)
                return (server_score, quality_score, sub_dub_score)

            sorted_video_tuples = sorted(extracted_video_list, key=sort_key, reverse=True)
            video_sources = [v[0] for v in sorted_video_tuples] # Extract only the video dicts

            # --- Save to urls.txt ---
            if video_sources:
                with open('urls.txt', 'a', encoding='utf-8') as url_file:
                    try:
                        ep_str = data.get('variables', {}).get('episodeString', 'Unknown Episode')
                        url_file.write(f"\n==== AllAnime: Episode {ep_str} ({self._get_preference('preferred_sub')}) ====\n")
                    except Exception:
                        url_file.write(f"\n==== AllAnime: Unknown Episode ====\n")

                    for stream in video_sources:
                        q = stream.get('quality', 'Unknown Quality')
                        u = stream.get('url', 'No URL')
                        url_file.write(f"{q}: {u}\n")
                        for sub in stream.get('subtitles', []):
                             lang = sub.get('language', 'Unknown')
                             sub_url = sub.get('url', 'No URL')
                             url_file.write(f"  Subtitle ({lang}): {sub_url}\n")

                print(f"✅ Found {len(video_sources)} video streams and saved to urls.txt")
            else:
                 print("ℹ️ No video streams found after processing servers.")


            return video_sources

        except requests.exceptions.Timeout:
            print("❌ AllAnime stream fetch request timed out.")
            return []
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to get video sources from AllAnime: {e}")
            return []
        except json.JSONDecodeError:
            print("❌ Failed to parse JSON payload/response for AllAnime video sources.")
            return []
        except Exception as e:
            import traceback
            print(f"An unexpected error occurred during AllAnime video source fetch: {e}")
            print(traceback.format_exc())
            return []


# --- Basic Video class equivalent for type hinting ---
# (Used by placeholder extractors, can be removed if extractors return dicts)
class Video:
    def __init__(self, videoUrl: str, videoTitle: str, videoPageUrl: str = "", headers: Dict[str, str] = None, subtitleTracks: List[Track] = None, audioTracks: List[Track] = None):
        self.videoUrl = videoUrl
        self.videoTitle = videoTitle
        self.videoPageUrl = videoPageUrl
        self.headers = headers if headers is not None else {}
        self.subtitleTracks = subtitleTracks if subtitleTracks is not None else []
        self.audioTracks = audioTracks if audioTracks is not None else []