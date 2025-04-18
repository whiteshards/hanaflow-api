
import requests
import json
import re
import urllib.parse
from bs4 import BeautifulSoup
import time
from datetime import datetime

class AniZoneSearcher:
    def __init__(self):
        self.base_url = "https://anizone.to"
        # Make sure base URL doesn't have trailing slash
        if self.base_url.endswith('/'):
            self.base_url = self.base_url[:-1]
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Origin': self.base_url,
            'Referer': self.base_url,
        }
        # Rate limiting to avoid overloading the server
        self.request_delay = 1.5  # seconds between requests
        self.last_request_time = 0
        
        # Livewire-specific data
        self.token = ""
        self.snapshots = {
            "anime_snapshot_key": "",
            "episode_snapshot_key": "",
            "video_snapshot_key": "",
        }
        self.load_count = 0
        
        # Quality preferences
        self.quality_entries = ["1080p", "720p", "480p", "360p"]
        self.quality_entry_values = ["1080", "720", "480", "360"]
        self.preferred_quality = "1080"
        
        # Audio preference
        self.dub = False  # Default to subbed content (False means prefer sub)
    
    def search_anime(self, query):
        """Search for anime on AniZone"""
        try:
            print(f"🔍 Searching for '{query}' on AniZone...")
            
            # Reset load count and snapshot
            self.load_count = 0
            self.snapshots["anime_snapshot_key"] = ""
            self.token = ""  # Reset token too to ensure fresh session
            
            # Prepare updates and calls for request
            # Structure the updates like the Kotlin implementation
            updates = {
                "data": {
                    "anime": [None, {"class": "anime", "key": 68, "s": "mdl"}],
                    "title": None,
                    "search": query,
                    "listSize": 1104,
                    "sort": "title-asc",
                    "sortOptions": [
                        {"release-asc": "First Aired", "release-desc": "Last Aired"}, 
                        {"s": "arr"}
                    ],
                    "view": "list",
                    "paginators": [{"page": 1}, {"s": "arr"}]
                }
            }
            calls = []
            
            # Try to make the request with retries
            response = None
            max_retries = 3
            for retry in range(max_retries):
                print(f"🔄 Attempt {retry + 1}/{max_retries} to search AniZone...")
                response = self.create_livewire_request("anime_snapshot_key", updates, calls)
                
                if response is None:
                    print(f"⚠️ AniZone request failed, retrying...")
                    time.sleep(2)
                    continue
                    
                if response.status_code != 200:
                    print(f"❌ Search failed with status code: {response.status_code}")
                    time.sleep(2)
                    continue
                
                print("✅ Successfully connected to AniZone")
                break  # Successfully got a response
            
            if response is None or response.status_code != 200:
                print("❌ AniZone search failed after retries")
                return []
            
            # Process response
            response_data = response.json()
            html = self.get_html_from_livewire(response_data, "anime_snapshot_key")
            
            # Parse results
            anime_list = []
            anime_elements = html.select("div.grid > div")
            
            for element in anime_elements:
                thumbnail = element.select_one("img")
                thumbnail_url = thumbnail["src"] if thumbnail else None
                
                link = element.select_one("a.inline")
                if not link:
                    continue
                
                anime_url = link["href"]
                title = link.text.strip()
                
                # Ensure URL is absolute
                if not anime_url.startswith("http"):
                    anime_url = self.base_url + anime_url
                
                anime_list.append({
                    'title': f"{title} [AniZone]",
                    'url': anime_url,
                    'poster': thumbnail_url,
                    'type': "Unknown",
                    'year': "Unknown",
                    'source': 'anizone'
                })
            
            self.load_count = len(anime_list)
            
            # Check if there are more results to load
            has_next_page = html.select_one("div[x-intersect~=loadMore]") is not None
            
            # Load more results if available
            while has_next_page:
                updates = {}
                calls = [
                    {
                        "path": "",
                        "method": "loadMore",
                        "params": []
                    }
                ]
                
                more_response = self.create_livewire_request("anime_snapshot_key", updates, calls)
                
                if more_response and more_response.status_code == 200:
                    more_data = more_response.json()
                    more_html = self.get_html_from_livewire(more_data, "anime_snapshot_key")
                    
                    more_anime_elements = more_html.select("div.grid > div")[self.load_count:]
                    
                    for element in more_anime_elements:
                        thumbnail = element.select_one("img")
                        thumbnail_url = thumbnail["src"] if thumbnail else None
                        
                        link = element.select_one("a.inline")
                        if not link:
                            continue
                        
                        anime_url = link["href"]
                        title = link.text.strip()
                        
                        # Ensure URL is absolute
                        if not anime_url.startswith("http"):
                            anime_url = self.base_url + anime_url
                        
                        anime_list.append({
                            'title': f"{title} [AniZone]",
                            'url': anime_url,
                            'poster': thumbnail_url,
                            'type': "Unknown",
                            'year': "Unknown",
                            'source': 'anizone'
                        })
                    
                    self.load_count = len(anime_list)
                    has_next_page = more_html.select_one("div[x-intersect~=loadMore]") is not None
                else:
                    break
            
            return anime_list
            
        except Exception as e:
            print(f"❌ AniZone search failed: {e}")
            import traceback
            print(traceback.format_exc())
            return []
    
    def get_anime_details(self, url):
        """Get detailed information about an anime"""
        try:
            print(f"📝 Getting details for {url} from AniZone...")
            
            # Get the anime page
            response = self.session.get(url, headers=self.headers)
            
            if response.status_code != 200:
                print(f"❌ Failed to get anime details: Status code {response.status_code}")
                return None
            
            # Parse the HTML
            document = BeautifulSoup(response.text, 'html.parser')
            
            # Get the main info div
            info_div = document.select("div.flex.items-start > div")
            if len(info_div) < 2:
                print("❌ Could not find anime info section")
                return None
            
            info_div = info_div[1]
            
            # Get the thumbnail
            thumbnail = document.select_one("div.flex.items-start img")
            thumbnail_url = thumbnail["src"] if thumbnail else None
            
            if thumbnail_url and not thumbnail_url.startswith(('http://', 'https://')):
                thumbnail_url = urllib.parse.urljoin(self.base_url, thumbnail_url)
            
            # Get the title
            title_element = info_div.select_one("h1")
            title = title_element.text.strip() if title_element else "Unknown Title"
            
            # Get status
            status_element = info_div.select("span.flex")
            status = "Unknown"
            if len(status_element) > 1:
                status_text = status_element[1].text.strip().lower()
                if status_text == "completed":
                    status = "Completed"
                elif status_text == "ongoing":
                    status = "Ongoing"
            
            # Get description
            description_element = info_div.select_one("div:has(>h3:contains(Synopsis)) > div")
            description = description_element.text.strip() if description_element else "No description available"
            
            # Get genres
            genre_elements = info_div.select("div > a")
            genres = ", ".join([genre.text.strip() for genre in genre_elements]) if genre_elements else "Unknown"
            
            # Create info object
            info = {
                'Status': status,
                'Genres': genres
            }
            
            # Return anime details
            return {
                'id': url.split("/")[-1],
                'url': url,
                'title': f"{title} [AniZone]",
                'poster': thumbnail_url,
                'description': description,
                'genres': genres,
                'info': info,
                'source': 'anizone'
            }
            
        except Exception as e:
            print(f"❌ Failed to get anime details from AniZone: {e}")
            import traceback
            print(traceback.format_exc())
            return None
    
    def get_episodes(self, anime_details):
        """Get episode list for an anime"""
        if not anime_details or 'url' not in anime_details:
            print("❌ Invalid anime details. Cannot get episodes.")
            return []
        
        try:
            print(f"🎬 Getting episodes for anime from AniZone...")
            anime_url = anime_details['url']
            
            # First, get the detail page directly to ensure we have the correct page
            print(f"🔄 Loading anime detail page first...")
            detail_response = self.session.get(anime_url, headers=self.headers)
            
            if detail_response.status_code != 200:
                print(f"❌ Failed to get anime detail page: Status code {detail_response.status_code}")
                return []
                
            # Parse the detail page to find episode section
            detail_document = BeautifulSoup(detail_response.text, 'html.parser')
            
            # Reset load count and snapshot
            self.load_count = 0
            # Extract snapshot from the detail page
            self.snapshots["episode_snapshot_key"] = self.get_snapshot_from_document(detail_document)
            # Reset token to get a fresh one
            self.token = ""
            
            # Get token from detail page
            token_script = detail_document.select_one('script[data-csrf]')
            if token_script and 'data-csrf' in token_script.attrs:
                self.token = token_script['data-csrf']
            else:
                # Try another approach to find the token
                meta_token = detail_document.select_one('meta[name="csrf-token"]')
                if meta_token:
                    self.token = meta_token.get('content', '')
                else:
                    token_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', detail_response.text)
                    if token_match:
                        self.token = token_match.group(1)
            
            if not self.token:
                print("❌ Could not extract CSRF token from detail page")
            
            # Create livewire request for episodes
            updates = {
                "sort": "release-desc"  # Sort by release date desc (newest first)
            }
            calls = []
            
            # Make the initial request with a full page URL
            response = self.create_livewire_request("episode_snapshot_key", updates, calls, anime_url)
            
            if not response or response.status_code != 200:
                print(f"⚠️ Livewire request failed: Status code {response.status_code if response else 'None'}")
                print("📋 Trying direct parsing of episode list from detail page instead...")
                
                # Use the detail document we already have as fallback
                html = detail_document
            else:
                # Process the livewire response
                response_data = response.json()
                html = self.get_html_from_livewire(response_data, "episode_snapshot_key")
            
            # Parse episodes
            episode_list = []
            
            # Try different selectors for episode elements since the structure might vary
            episode_elements = html.select("ul > li")
            if not episode_elements:
                episode_elements = html.select("div.grid > div")  # Alternative structure
            if not episode_elements:
                episode_elements = html.select(".episodes-list li")  # Another alternative
                
            print(f"🔍 Found {len(episode_elements)} potential episode elements")
            
            for element in episode_elements:
                # Try different selectors for links
                link = element.select_one("a[href]")
                if not link:
                    link = element.select_one("a")  # Try any anchor
                if not link:
                    continue
                
                episode_url = link.get("href", "")
                if not episode_url:
                    continue
                    
                if not episode_url.startswith("http"):
                    episode_url = self.base_url + episode_url
                
                # Try different selectors for title
                title_element = element.select_one("h3")
                if not title_element:
                    title_element = element.select_one(".episode-title")
                if not title_element:
                    title_element = link  # Use link text as fallback
                    
                title = title_element.text.strip() if title_element else "Unknown Episode"
                
                # Extract episode number from title if possible
                episode_number = "0"
                match = re.search(r'Episode (\d+)', title)
                if match:
                    episode_number = match.group(1)
                
                # Get upload date if available
                date_elements = element.select("div.flex-row > span")
                upload_date = None
                if len(date_elements) > 1:
                    date_str = date_elements[1].text.strip()
                    try:
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                        upload_date = int(date_obj.timestamp())
                    except:
                        upload_date = None
                
                episode_list.append({
                    'number': episode_number,
                    'title': title,
                    'url': episode_url,
                    'thumbnail': None,
                    'date': upload_date,
                    'source': 'anizone'
                })
            
            self.load_count = len(episode_list)
            
            # Check if there are more episodes
            has_more = html.select_one("div[x-intersect~=loadMore]") is not None
            
            # Load more episodes if available
            while has_more:
                updates = {}
                calls = [
                    {
                        "path": "",
                        "method": "loadMore",
                        "params": []
                    }
                ]
                
                more_response = self.create_livewire_request("episode_snapshot_key", updates, calls)
                
                if not more_response or more_response.status_code != 200:
                    break
                
                more_data = more_response.json()
                more_html = self.get_html_from_livewire(more_data, "episode_snapshot_key")
                
                more_episode_elements = more_html.select("ul > li")[self.load_count:]
                
                for element in more_episode_elements:
                    link = element.select_one("a[href]")
                    if not link:
                        continue
                    
                    episode_url = link["href"]
                    if not episode_url.startswith("http"):
                        episode_url = self.base_url + episode_url
                    
                    title_element = element.select_one("h3")
                    title = title_element.text.strip() if title_element else "Unknown Episode"
                    
                    # Extract episode number from title if possible
                    episode_number = "0"
                    match = re.search(r'Episode (\d+)', title)
                    if match:
                        episode_number = match.group(1)
                    
                    # Get upload date if available
                    date_elements = element.select("div.flex-row > span")
                    upload_date = None
                    if len(date_elements) > 1:
                        date_str = date_elements[1].text.strip()
                        try:
                            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                            upload_date = int(date_obj.timestamp())
                        except:
                            upload_date = None
                    
                    episode_list.append({
                        'number': episode_number,
                        'title': title,
                        'url': episode_url,
                        'thumbnail': None,
                        'date': upload_date,
                        'source': 'anizone'
                    })
                
                self.load_count = len(episode_list)
                has_more = more_html.select_one("div[x-intersect~=loadMore]") is not None
            
            # Sort episodes by number
            episode_list.sort(key=lambda x: float(x['number']) if x['number'].replace('.', '', 1).isdigit() else 0, reverse=True)
            
            return episode_list
            
        except Exception as e:
            print(f"❌ Failed to get episodes from AniZone: {e}")
            import traceback
            print(traceback.format_exc())
            return []
    
    def get_video_sources(self, episode_url):
        """Get video sources for a specific episode"""
        try:
            print(f"🎥 Getting video sources from {episode_url}...")
            
            # Reset snapshot
            self.snapshots["video_snapshot_key"] = ""
            
            # Get the episode page
            response = self.session.get(episode_url, headers=self.headers)
            
            if response.status_code != 200:
                print(f"❌ Failed to get episode page: Status code {response.status_code}")
                return []
            
            # Parse the HTML
            document = BeautifulSoup(response.text, 'html.parser')
            
            # Get episode info for the url.txt file
            episode_info = episode_url.split('/')[-1]
            
            # Get the server selects
            server_selects = []
            for button in document.select("button[wire\:click]"):
                if "setVideo" in button["wire:click"]:
                    server_selects.append(button)
            
            if not server_selects:
                print("❌ No video servers found")
                return []
            
            # Get subtitles
            subtitles = []
            for track in document.select("track[kind=subtitles]"):
                subtitle_url = track["src"]
                subtitle_label = track["label"]
                subtitles.append({
                    'url': subtitle_url,
                    'language': subtitle_label
                })
            
            # Get the initial m3u8 URL
            media_player = document.select_one("media-player")
            if not media_player:
                print("❌ No media player found")
                return []
            
            initial_m3u8 = media_player["src"]
            
            # Get the snapshot for video changes
            self.snapshots["video_snapshot_key"] = self.get_snapshot_from_document(document)
            
            # Initialize video sources with the first server
            m3u8_list = [{
                'url': initial_m3u8,
                'name': server_selects[0].text.strip(),
                'subtitles': subtitles
            }]
            
            # Process other servers
            for video_server in server_selects[1:]:
                try:
                    # Extract video ID from wire:click attribute
                    regex = r"setVideo\('(\d+)'\)"
                    match = re.search(regex, video_server["wire:click"])
                    if not match:
                        continue
                    
                    video_id = match.group(1)
                    
                    # Create livewire request to change video
                    updates = {}
                    calls = [
                        {
                            "path": "",
                            "method": "setVideo",
                            "params": [int(video_id)]
                        }
                    ]
                    
                    # Make the request
                    video_response = self.create_livewire_request(
                        "video_snapshot_key", 
                        updates, 
                        calls, 
                        episode_url
                    )
                    
                    if not video_response or video_response.status_code != 200:
                        print(f"❌ Failed to get video server {video_id}: Status code {video_response.status_code if video_response else 'None'}")
                        continue
                    
                    # Process the response
                    video_data = video_response.json()
                    video_html = self.get_html_from_livewire(video_data, "video_snapshot_key")
                    
                    # Get subtitles for this server
                    server_subtitles = []
                    for track in video_html.select("track[kind=subtitles]"):
                        subtitle_url = track["src"]
                        subtitle_label = track["label"]
                        server_subtitles.append({
                            'url': subtitle_url,
                            'language': subtitle_label
                        })
                    
                    # Get m3u8 URL for this server
                    media_player = video_html.select_one("media-player")
                    if media_player and "src" in media_player.attrs:
                        m3u8_list.append({
                            'url': media_player["src"],
                            'name': video_server.text.strip(),
                            'subtitles': server_subtitles
                        })
                except Exception as e:
                    print(f"❌ Error processing server: {e}")
                    continue
            
            # Write to urls.txt
            with open('urls.txt', 'a') as url_file:
                url_file.write(f"\n==== AniZone: {episode_info} ====\n")
                
                for server in m3u8_list:
                    url_file.write(f"{server['name']}: {server['url']}\n")
                    for sub in server['subtitles']:
                        url_file.write(f"  Subtitle ({sub['language']}): {sub['url']}\n")
            
            # Process m3u8 lists to extract qualities
            video_sources = []
            
            # Order servers based on preferences
            ordered_servers = m3u8_list
            if self.dub:
                # If dub is preferred, keep original order (dub first)
                pass
            else:
                # If sub is preferred, reverse the order (sub first)
                ordered_servers = list(reversed(m3u8_list))
            
            for server in ordered_servers:
                try:
                    # Get the m3u8 playlist
                    playlist_response = self.session.get(server['url'], headers=self.headers)
                    
                    if playlist_response.status_code != 200:
                        print(f"❌ Failed to get m3u8 playlist: Status code {playlist_response.status_code}")
                        continue
                    
                    playlist_content = playlist_response.text
                    
                    # Check if it's a master playlist
                    if "#EXT-X-STREAM-INF:" in playlist_content:
                        # Extract quality variants
                        streams = playlist_content.split("#EXT-X-STREAM-INF:")[1:]
                        
                        for stream in streams:
                            resolution = re.search(r"RESOLUTION=\d+x(\d+)", stream)
                            bandwidth = re.search(r"BANDWIDTH=(\d+)", stream)
                            
                            quality = "Unknown"
                            if resolution:
                                quality = f"{resolution.group(1)}p"
                            
                            stream_url = stream.split("\n")[1].strip()
                            
                            # Make sure URL is absolute
                            if not stream_url.startswith("http"):
                                base_url = "/".join(server['url'].split("/")[:-1])
                                stream_url = f"{base_url}/{stream_url}"
                            
                            video_sources.append({
                                'url': stream_url,
                                'quality': f"{server['name']} - {quality}",
                                'source': 'anizone',
                                'subtitles': server['subtitles']
                            })
                    else:
                        # Single quality stream
                        video_sources.append({
                            'url': server['url'],
                            'quality': f"{server['name']} - Direct",
                            'source': 'anizone',
                            'subtitles': server['subtitles']
                        })
                except Exception as e:
                    print(f"❌ Error processing m3u8 playlist: {e}")
                    continue
            
            # Sort videos based on preferences
            sorted_sources = self.sort_video_sources(video_sources)
            
            print(f"✅ Found {len(video_sources)} stream URLs and saved to urls.txt")
            return sorted_sources
            
        except Exception as e:
            print(f"❌ Failed to get video sources from AniZone: {e}")
            import traceback
            print(traceback.format_exc())
            return []
    
    def sort_video_sources(self, video_sources):
        """Sort video sources based on preferences"""
        def get_score(source):
            score = 0
            
            # Prioritize by quality
            if self.preferred_quality in source['quality']:
                score += 100
                
            return score
        
        return sorted(video_sources, key=get_score, reverse=True)
    
    # ============================= Utilities ==============================
    
    def get_predefined_snapshots(self, slug):
        """Get predefined snapshot for an anime if available"""
        if "/anime/uyyyn4kf" in slug:
            return """{"data":{"anime":[null,{"class":"anime","key":68,"s":"mdl"}],"title":null,"search":"","listSize":1104,"sort":"release-asc","sortOptions":[{"release-asc":"First Aired","release-desc":"Last Aired"},{"s":"arr"}],"view":"list","paginators":[{"page":1},{"s":"arr"}]},"memo":{"id":"GD1OiEMOJq6UQDQt1OBt","name":"pages.anime-detail","path":"anime\/uyyyn4kf","method":"GET","children":[],"scripts":[],"assets":[],"errors":[],"locale":"en"},"checksum":"5800932dd82e4862f34f6fd72d8098243b32643e8accb8da6a6a39cd0ee86acd"}"""
        return ""
    
    def get_html_from_livewire(self, response_data, map_key):
        """Extract HTML from a Livewire response"""
        if "components" not in response_data or not response_data["components"]:
            return BeautifulSoup("<html></html>", 'html.parser')
        
        component = response_data["components"][0]
        
        # Update snapshot from response
        if "snapshot" in component:
            self.snapshots[map_key] = component["snapshot"].replace('\\\"', '"')
        
        # Parse HTML from effects
        if "effects" in component and "html" in component["effects"]:
            html_content = component["effects"]["html"].replace('\\\"', '"').replace('\\n', '')
            return BeautifulSoup(html_content, 'html.parser')
        
        return BeautifulSoup("<html></html>", 'html.parser')
    
    def get_snapshot_from_document(self, document):
        """Extract snapshot from a document"""
        # First try the direct way
        snapshot_element = document.select_one('main > div[wire\\:snapshot]')
        if snapshot_element and 'wire:snapshot' in snapshot_element.attrs:
            return snapshot_element['wire:snapshot'].replace('&quot;', '"')
            
        # Try other div with snapshot attribute
        snapshot_element = document.select_one('div[wire\\:snapshot]')
        if snapshot_element and 'wire:snapshot' in snapshot_element.attrs:
            return snapshot_element['wire:snapshot'].replace('&quot;', '"')
        
        # If we can't find the snapshot attribute directly, try by raw HTML
        raw_html = str(document)
        match = re.search(r'wire:snapshot="([^"]+)"', raw_html)
        if match:
            return match.group(1).replace('&quot;', '"')
            
        # One more attempt with different attribute format
        match = re.search(r'wire\\:snapshot="([^"]+)"', raw_html)
        if match:
            return match.group(1).replace('&quot;', '"')
        
        print("⚠️ Could not find snapshot in document")
        return ""
    
    def create_livewire_request(self, map_key, updates, calls, initial_slug=None):
        """Create and execute a Livewire request"""
        # Implement rate limiting
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)
        self.last_request_time = time.time()
        
        initial_slug = initial_slug or "/anime"
        
        # Ensure initial_slug is just a path, not a full URL
        if initial_slug.startswith(self.base_url):
            initial_slug = initial_slug[len(self.base_url):]
        
        # Check if we need to initialize
        first_snapshot = self.snapshots[map_key]
        if not first_snapshot or not self.token:
            # Get the initial page to get token and snapshot
            try:
                print(f"🔄 Initializing connection to AniZone...")
                # Ensure proper URL construction
                if initial_slug.startswith('/') and self.base_url.endswith('/'):
                    initial_slug = initial_slug[1:]
                elif not initial_slug.startswith('/') and not self.base_url.endswith('/'):
                    initial_slug = '/' + initial_slug
                    
                response = self.session.get(f"{self.base_url}{initial_slug}", headers=self.headers)
                
                if response.status_code != 200:
                    print(f"❌ Failed to get initial page: Status code {response.status_code}")
                    return None
                
                document = BeautifulSoup(response.text, 'html.parser')
                
                # Get the snapshot
                self.snapshots[map_key] = self.get_snapshot_from_document(document)
                
                # Get the CSRF token
                token_script = document.select_one('script[data-csrf]')
                if token_script and 'data-csrf' in token_script.attrs:
                    self.token = token_script['data-csrf']
                else:
                    # Try another approach to find the token
                    meta_token = document.select_one('meta[name="csrf-token"]')
                    if meta_token:
                        self.token = meta_token.get('content', '')
                    else:
                        # Try by extracting from HTML
                        token_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', response.text)
                        if token_match:
                            self.token = token_match.group(1)
                        else:
                            print("❌ Failed to get CSRF token")
                            return None
            except Exception as e:
                print(f"❌ Error initializing Livewire connection: {e}")
                import traceback
                print(traceback.format_exc())
                return None
        
        # Prepare headers
        request_headers = self.headers.copy()
        request_headers['X-Livewire'] = "true"
        request_headers['Content-Type'] = "application/json"
        request_headers['X-CSRF-TOKEN'] = self.token
        
        # Prepare the request body - Properly merge snapshot if available
        if 'data' in updates and self.snapshots[map_key]:
            try:
                # Try to parse existing snapshot JSON and merge with updates
                snapshot_json = json.loads(self.snapshots[map_key])
                # Only merge data fields if snapshot has data
                if 'data' in snapshot_json:
                    # Keep provided updates fields, but fill missing ones from snapshot
                    for key, value in snapshot_json['data'].items():
                        if key not in updates['data']:
                            updates['data'][key] = value
            except json.JSONDecodeError:
                print(f"⚠️ Warning: Could not parse snapshot JSON for merging")
        
        request_body = {
            "_token": self.token,
            "components": [
                {
                    "calls": calls,
                    "snapshot": self.snapshots[map_key],
                    "updates": updates
                }
            ]
        }
        
        if not self.snapshots[map_key]:
            print(f"⚠️ Warning: Empty snapshot for key '{map_key}'")
        
        if not self.token:
            print(f"⚠️ Warning: Empty CSRF token")
        
        # Make the request
        try:
            # Fix URL construction by ensuring no double URL parts
            livewire_url = f"{self.base_url}/livewire/update"
            if self.base_url.endswith('/'):
                livewire_url = f"{self.base_url}livewire/update"
                
            print(f"🔄 Sending Livewire request to: {livewire_url}")
            print(f"Request body: {json.dumps(request_body)[:200]}...")
                
            response = self.session.post(
                livewire_url,
                headers=request_headers,
                json=request_body,
                timeout=15
            )
            
            if response.status_code != 200:
                print(f"❌ Response status code: {response.status_code}")
                try:
                    print(f"Response text preview: {response.text[:500]}")
                except:
                    print("Could not print response text")
            
            # Handle 500 errors gracefully
            if response.status_code == 500:
                print(f"❌ Server error (500) from AniZone. Attempting to recover...")
                
                # Retry with fresh token and snapshot
                self.token = ""
                self.snapshots[map_key] = ""
                
                # Get a fresh page with properly constructed URL
                retry_url = f"{self.base_url}{initial_slug}"
                print(f"🔄 Attempting to recover with URL: {retry_url}")
                retry_response = self.session.get(retry_url, headers=self.headers)
                if retry_response.status_code == 200:
                    retry_document = BeautifulSoup(retry_response.text, 'html.parser')
                    
                    # Get fresh snapshot
                    self.snapshots[map_key] = self.get_snapshot_from_document(retry_document)
                    
                    # Get fresh token
                    retry_token_script = retry_document.select_one('script[data-csrf]')
                    if retry_token_script and 'data-csrf' in retry_token_script.attrs:
                        self.token = retry_token_script['data-csrf']
                        
                        # Try the request again with fresh credentials
                        request_headers['X-CSRF-TOKEN'] = self.token
                        request_body["_token"] = self.token
                        request_body["components"][0]["snapshot"] = self.snapshots[map_key]
                        
                        response = self.session.post(
                            f"{self.base_url}/livewire/update",
                            headers=request_headers,
                            json=request_body,
                            timeout=15
                        )
            
            return response
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return None

def test_anizone():
    """Test the AniZone scraper"""
    print("Testing AniZone scraper...")
    
    anizone = AniZoneSearcher()
    
    # Search for anime
    results = anizone.search_anime("demon slayer")
    print(f"Found {len(results)} results")
    
    if results:
        # Get details for the first result
        details = anizone.get_anime_details(results[0]['url'])
        print(f"Got details for {details['title']}")
        
        # Get episodes
        episodes = anizone.get_episodes(details)
        print(f"Found {len(episodes)} episodes")
        
        if episodes:
            # Get video sources for the first episode
            sources = anizone.get_video_sources(episodes[0]['url'])
            print(f"Found {len(sources)} video sources")

if __name__ == "__main__":
    test_anizone()
