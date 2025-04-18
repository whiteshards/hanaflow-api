
import json
import re
import requests
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup

class Track:
    def __init__(self, url: str, lang: str):
        self.url = url
        self.lang = lang

class Video:
    def __init__(self, videoUrl: str, videoTitle: str, videoPageUrl: str = "", headers: Dict[str, str] = None, subtitleTracks: List[Track] = None, audioTracks: List[Track] = None):
        self.videoUrl = videoUrl
        self.videoTitle = videoTitle
        self.videoPageUrl = videoPageUrl
        self.headers = headers if headers is not None else {}
        self.subtitleTracks = subtitleTracks if subtitleTracks is not None else []
        self.audioTracks = audioTracks if audioTracks is not None else []

class HanimeScraper:
    """Scraper for hanime.tv based on the Kotlin implementation"""

    # Constants
    PAGE_SIZE = 26
    SEARCH_URL = "https://search.htv-services.com/"
    BASE_URL = "https://hanime.tv"
    
    # Preferences
    QUALITY_LIST = ["1080p", "720p", "480p", "360p"]
    PREF_QUALITY_DEFAULT = "1080p"
    
    def __init__(self):
        self.session = requests.Session()
        self.auth_cookie = None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        }
        self.search_headers = {
            "authority": "search.htv-services.com",
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json;charset=UTF-8",
        }
        # Mimicking the preferences from the Kotlin code
        self.preferences = {
            "preferred_quality": self.PREF_QUALITY_DEFAULT
        }

    def _get_preference(self, key, default=None):
        """Get a preference value with fallback to default."""
        return self.preferences.get(key, default)

    def _set_auth_cookie(self):
        """Set authentication cookie if available."""
        if self.auth_cookie is None:
            # In Python we'd typically use the session's cookies
            # This is a simplified version of the Kotlin implementation
            cookies = self.session.cookies.get_dict()
            if "htv3session" in cookies:
                self.auth_cookie = f"htv3session={cookies['htv3session']}"

    def search_request_body(self, query: str, page: int, filters=None):
        """Create search request body similar to Kotlin implementation."""
        # If filters are implemented, extract parameters here
        search_params = self._get_search_parameters(filters)
        included_tags, blacklisted_tags, brands, tags_mode, order_by, ordering = search_params
        
        return {
            "search_text": query,
            "tags": included_tags,
            "tags_mode": tags_mode,
            "brands": brands,
            "blacklist": blacklisted_tags,
            "order_by": order_by,
            "ordering": ordering,
            "page": page - 1
        }

    def _get_search_parameters(self, filters=None):
        """Extract search parameters from filters, similar to Kotlin."""
        # Default values
        included_tags = []
        blacklisted_tags = []
        brands = []
        tags_mode = "AND"
        order_by = "likes"
        ordering = "desc"
        
        # If filter handling is implemented, process them here
        if filters:
            # Process filters similar to Kotlin implementation
            pass
            
        return (included_tags, blacklisted_tags, brands, tags_mode, order_by, ordering)

    def _is_number(self, text):
        """Check if text is a number, similar to Kotlin's isNumber."""
        try:
            int(text)
            return True
        except ValueError:
            return False

    def _get_title(self, title):
        """Extract clean title similar to Kotlin's getTitle."""
        if " Ep " in title:
            return title.split(" Ep ")[0].strip()
        else:
            # Check if the last word is a number
            parts = title.strip().split(" ")
            if self._is_number(parts[-1]):
                return " ".join(parts[:-1]).strip()
            else:
                return title.strip()

    def search_anime(self, query="", page=1, filters=None):
        """Search for anime, similar to Kotlin's searchAnime."""
        print(f"🔍 Searching hanime for: '{query}'")
        
        results = []
        try:
            data = {
                "variables": {},
                "query": ""
            }
            data = self.search_request_body(query, page, filters)
            
            response = self.session.post(
                self.SEARCH_URL,
                headers=self.search_headers,
                json=data,
                timeout=15
            )
            response.raise_for_status()
            
            # Parse search results into anime list
            results = self._parse_search_json(response.json())
            
            print(f"Found {len(results)} results from hanime")
            return results
            
        except Exception as e:
            print(f"❌ Error searching hanime: {e}")
            return []

    def _parse_search_json(self, response_data):
        """Parse search JSON response similar to Kotlin's parseSearchJson."""
        anime_list = []
        
        if not response_data:
            return anime_list
            
        response = response_data
        array = json.loads(response.get('hits', '[]'))
        
        # Group by title and take first item of each group
        grouped_items = {}
        for item in array:
            title = self._get_title(item.get('name', ''))
            if title not in grouped_items:
                grouped_items[title] = item
                
        for item in grouped_items.values():
            title = self._get_title(item.get('name', ''))
            thumbnail_url = item.get('coverUrl')
            author = item.get('brand')
            description = item.get('description', '')
            if description:
                # Remove HTML tags
                description = re.sub(r'<[^>]*>', '', description)
                
            genres = item.get('tags', [])
            genre_text = ", ".join(genres) if genres else ""
            
            slug = item.get('slug', '')
            url = f"/videos/hentai/{slug}"
            
            anime_list.append({
                'title': f"{title} [Hanime]",
                'url': url,
                'poster': thumbnail_url,
                'description': description,
                'author': author,
                'genres': genre_text,
                'source': 'hanime',
            })
            
        # Check for pagination
        has_next_page = response.get('page', 0) < response.get('nbPages', 1) - 1
        
        return anime_list

    def get_anime_details(self, url):
        """Get anime details, similar to Kotlin's animeDetailsParse."""
        print(f"📊 Getting anime details from hanime for URL: {url}")
        
        try:
            full_url = f"{self.BASE_URL}{url}"
            response = self.session.get(full_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            title = self._get_title(soup.select_one("h1.tv-title").text)
            thumbnail_url = soup.select_one("img.hvpi-cover").get("src")
            author = soup.select_one("a.hvpimbc-text").text if soup.select_one("a.hvpimbc-text") else ""
            
            # Get description
            description_elements = soup.select("div.hvpist-description p")
            description = "\n\n".join([el.text for el in description_elements]) if description_elements else ""
            
            # Get genres
            genre_elements = soup.select("div.hvpis-text div.btn__content")
            genres = ", ".join([el.text for el in genre_elements]) if genre_elements else ""
            
            return {
                'title': title,
                'url': url,
                'poster': thumbnail_url,
                'description': description,
                'author': author,
                'genres': genres,
                'info': {
                    'Studio': author
                },
                'source': 'hanime'
            }
            
        except Exception as e:
            print(f"❌ Error getting anime details from hanime: {e}")
            return None

    def get_episodes(self, anime_details):
        """Get episode list, similar to Kotlin's episodeListParse."""
        if not anime_details or 'url' not in anime_details:
            print("❌ Invalid anime details. Cannot get episodes.")
            return []
            
        print(f"🎬 Getting episodes for {anime_details.get('title', 'anime')} from hanime...")
        
        try:
            slug = anime_details['url'].split('/')[-1]
            api_url = f"{self.BASE_URL}/api/v8/video?id={slug}"
            
            response = self.session.get(api_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            response_data = response.json()
            episodes = []
            
            # Extract franchise videos if any
            franchise_videos = response_data.get('hentai_franchise_hentai_videos', [])
            
            if franchise_videos:
                for idx, video in enumerate(reversed(franchise_videos)):
                    episode_number = idx + 1
                    timestamp = (video.get('releasedAtUnix', 0) or 0) * 1000
                    video_id = video.get('id')
                    
                    episodes.append({
                        'title': f"Episode {episode_number}",
                        'episode': episode_number,
                        'url': f"{self.BASE_URL}/api/v8/video?id={video_id}",
                        'date': timestamp,
                        'source': 'hanime'
                    })
            else:
                # If no franchise videos, use the current video as episode 1
                episodes.append({
                    'title': "Episode 1",
                    'episode': 1,
                    'url': api_url,
                    'date': 0,
                    'source': 'hanime'
                })
                
            return episodes
            
        except Exception as e:
            print(f"❌ Error getting episodes from hanime: {e}")
            return []

    def get_video_streams(self, episode_url):
        """Get video streams, similar to Kotlin's videoListParse."""
        print(f"🎥 Getting video streams from hanime: {episode_url}")
        
        try:
            # Check for auth cookie
            self._set_auth_cookie()
            
            if self.auth_cookie:
                return self._fetch_premium_videos(episode_url)
            
            # Regular video fetching
            response = self.session.get(episode_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            response_data = response.json()
            
            # Extract videos from manifest
            videos_manifest = response_data.get('videos_manifest', {})
            servers = videos_manifest.get('servers', [])
            
            if not servers or len(servers) == 0:
                print("❌ No servers found in the manifest.")
                return []
                
            # Get streams from first server
            streams = servers[0].get('streams', [])
            
            # Filter out premium alert streams
            streams = [s for s in streams if s.get('kind') != 'premium_alert']
            
            videos = []
            for stream in streams:
                url = stream.get('url', '')
                height = stream.get('height', '')
                quality = f"{height}p"
                
                videos.append(Video(url, quality, url))
                
            # Sort videos by quality preference
            return self._sort_videos(videos)
            
        except Exception as e:
            print(f"❌ Error getting video streams from hanime: {e}")
            return []

    def _fetch_premium_videos(self, episode_url):
        """Fetch premium videos if auth cookie is available."""
        try:
            custom_headers = self.headers.copy()
            custom_headers['cookie'] = self.auth_cookie
            
            # Extract video ID
            video_id = episode_url.split('id=')[-1]
            video_url = f"{self.BASE_URL}/videos/hentai/{video_id}"
            
            response = self.session.get(video_url, headers=custom_headers, timeout=15)
            response.raise_for_status()
            
            # Extract data from the script tag containing __NUXT__
            nuxt_pattern = r'__NUXT__=(.*?);\s*</script>'
            nuxt_match = re.search(nuxt_pattern, response.text)
            
            if not nuxt_match:
                print("❌ Could not find __NUXT__ data.")
                return []
                
            nuxt_data = json.loads(nuxt_match.group(1))
            
            # Navigate to video data
            state_data = nuxt_data.get('state', {}).get('data', {})
            video_data = state_data.get('video', {})
            manifest = video_data.get('videos_manifest', {})
            servers = manifest.get('servers', [])
            
            videos = []
            for server in servers:
                streams = server.get('streams', [])
                for stream in streams:
                    url = stream.get('url', '')
                    height = stream.get('height', '')
                    quality = f"{height}p"
                    
                    videos.append(Video(url, quality, url))
                    
            return self._sort_videos(videos)
            
        except Exception as e:
            print(f"❌ Error fetching premium videos: {e}")
            return []

    def _sort_videos(self, videos):
        """Sort videos by quality preference, similar to Kotlin's sort method."""
        preferred_quality = self._get_preference('preferred_quality', self.PREF_QUALITY_DEFAULT)
        
        # Define the sort key function
        def sort_key(video):
            # First priority: matches preferred quality
            preferred_priority = 1 if preferred_quality in video.videoTitle else 0
            
            # Second priority: resolution value
            resolution = 0
            match = re.search(r'(\d+)p', video.videoTitle)
            if match:
                resolution = int(match.group(1))
                
            return (-preferred_priority, -resolution)
            
        # Sort the videos
        return sorted(videos, key=sort_key)

    def get_tags(self):
        """Get all available tags, similar to Kotlin's getTags."""
        return [
            {"id": "3D", "name": "3D"},
            {"id": "AHEGAO", "name": "AHEGAO"},
            {"id": "ANAL", "name": "ANAL"},
            {"id": "BDSM", "name": "BDSM"},
            {"id": "BIG BOOBS", "name": "BIG BOOBS"},
            {"id": "BLOW JOB", "name": "BLOW JOB"},
            {"id": "BONDAGE", "name": "BONDAGE"},
            {"id": "BOOB JOB", "name": "BOOB JOB"},
            {"id": "CENSORED", "name": "CENSORED"},
            {"id": "COMEDY", "name": "COMEDY"},
            {"id": "COSPLAY", "name": "COSPLAY"},
            {"id": "CREAMPIE", "name": "CREAMPIE"},
            {"id": "DARK SKIN", "name": "DARK SKIN"},
            {"id": "FACIAL", "name": "FACIAL"},
            {"id": "FANTASY", "name": "FANTASY"},
            {"id": "FILMED", "name": "FILMED"},
            {"id": "FOOT JOB", "name": "FOOT JOB"},
            {"id": "FUTANARI", "name": "FUTANARI"},
            {"id": "GANGBANG", "name": "GANGBANG"},
            {"id": "GLASSES", "name": "GLASSES"},
            {"id": "HAND JOB", "name": "HAND JOB"},
            {"id": "HAREM", "name": "HAREM"},
            {"id": "HD", "name": "HD"},
            {"id": "HORROR", "name": "HORROR"},
            {"id": "INCEST", "name": "INCEST"},
            {"id": "INFLATION", "name": "INFLATION"},
            {"id": "LACTATION", "name": "LACTATION"},
            {"id": "LOLI", "name": "LOLI"},
            {"id": "MAID", "name": "MAID"},
            {"id": "MASTURBATION", "name": "MASTURBATION"},
            {"id": "MILF", "name": "MILF"},
            {"id": "MIND BREAK", "name": "MIND BREAK"},
            {"id": "MIND CONTROL", "name": "MIND CONTROL"},
            {"id": "MONSTER", "name": "MONSTER"},
            {"id": "NEKOMIMI", "name": "NEKOMIMI"},
            {"id": "NTR", "name": "NTR"},
            {"id": "NURSE", "name": "NURSE"},
            {"id": "ORGY", "name": "ORGY"},
            {"id": "PLOT", "name": "PLOT"},
            {"id": "POV", "name": "POV"},
            {"id": "PREGNANT", "name": "PREGNANT"},
            {"id": "PUBLIC SEX", "name": "PUBLIC SEX"},
            {"id": "RAPE", "name": "RAPE"},
            {"id": "REVERSE RAPE", "name": "REVERSE RAPE"},
            {"id": "RIMJOB", "name": "RIMJOB"},
            {"id": "SCAT", "name": "SCAT"},
            {"id": "SCHOOL GIRL", "name": "SCHOOL GIRL"},
            {"id": "SHOTA", "name": "SHOTA"},
            {"id": "SOFTCORE", "name": "SOFTCORE"},
            {"id": "SWIMSUIT", "name": "SWIMSUIT"},
            {"id": "TEACHER", "name": "TEACHER"},
            {"id": "TENTACLE", "name": "TENTACLE"},
            {"id": "THREESOME", "name": "THREESOME"},
            {"id": "TOYS", "name": "TOYS"},
            {"id": "TRAP", "name": "TRAP"},
            {"id": "TSUNDERE", "name": "TSUNDERE"},
            {"id": "UGLY BASTARD", "name": "UGLY BASTARD"},
            {"id": "UNCENSORED", "name": "UNCENSORED"},
            {"id": "VANILLA", "name": "VANILLA"},
            {"id": "VIRGIN", "name": "VIRGIN"},
            {"id": "WATERSPORTS", "name": "WATERSPORTS"},
            {"id": "X-RAY", "name": "X-RAY"},
            {"id": "YAOI", "name": "YAOI"},
            {"id": "YURI", "name": "YURI"},
        ]

    def get_brands(self):
        """Get all available brands, similar to Kotlin's getBrands."""
        return [
            {"id": "37c-Binetsu", "name": "37c-binetsu"},
            {"id": "Adult Source Media", "name": "adult-source-media"},
            {"id": "Ajia-Do", "name": "ajia-do"},
            # Many more brands would be listed here, omitted for brevity
            # The full list is in the Kotlin reference
        ]

    def get_sortable_list(self):
        """Get sortable options, similar to Kotlin's sortableList."""
        return [
            ("Uploads", "created_at_unix"),
            ("Views", "views"),
            ("Likes", "likes"),
            ("Release", "released_at_unix"),
            ("Alphabetical", "title_sortable"),
        ]

    def set_preferred_quality(self, quality):
        """Set preferred video quality."""
        if quality in self.QUALITY_LIST:
            self.preferences["preferred_quality"] = quality
            return True
        return False
