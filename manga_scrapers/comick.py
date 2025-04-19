
import json
import re
import time
import urllib.parse
import requests
import cloudscraper
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
import math
import random

class ComickScraper:
    # Constants
    PAGE_SIZE = 20
    CHAPTERS_LIMIT = 99999
    SLUG_SEARCH_PREFIX = "id:"
    
    # API URLs
    BASE_URL = "https://comick.io"
    API_URL = "https://api.comick.fun"
    
    def __init__(self, session: Optional[requests.Session] = None, lang: str = "en"):
        """Initialize ComickScraper with optional session and language preference."""
        self.session = session or cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )
        self.lang = lang
        self.comick_lang = lang
        self.headers = {
            "Referer": f"{self.BASE_URL}/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": self.BASE_URL,
            "Connection": "keep-alive",
            "sec-ch-ua": '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"'
        }
        
        # Preferences (default values)
        self.preferences = {
            "ignored_groups": set(),
            "ignored_tags": "",
            "show_alternative_titles": False,
            "include_mu_tags": False,
            "group_tags": False,
            "update_cover": True,
            "local_title": False, 
            "score_position": "top"
        }
        
        # Storage for search results
        self.search_results = []
    
    def set_preference(self, key: str, value: Any):
        """Set a preference value."""
        self.preferences[key] = value
    
    def get_preference(self, key: str, default: Any = None):
        """Get a preference value with fallback to default."""
        return self.preferences.get(key, default)
    
    def get_popular_manga(self, page: int = 1) -> List[Dict[str, Any]]:
        """Get popular manga list."""
        print(f"🔍 Getting popular manga (page {page})...")
        filters = {"sort": "follow"}
        return self.search_manga(page=page, query="", filters=filters)
    
    def get_latest_manga(self, page: int = 1) -> List[Dict[str, Any]]:
        """Get latest updated manga list."""
        print(f"🔍 Getting latest manga (page {page})...")
        filters = {"sort": "uploaded"}
        return self.search_manga(page=page, query="", filters=filters)
    
    def search_manga(self, query: str, page: int = 1, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search for manga with filters."""
        print(f"🔍 Searching for manga: '{query}'...")
        
        filters = filters or {}
        
        # Handle slug/id search
        if query.startswith(self.SLUG_SEARCH_PREFIX):
            slug_or_hid = query[len(self.SLUG_SEARCH_PREFIX):]
            manga_details = self.get_manga_details({"url": f"/comic/{slug_or_hid}#"})
            return [manga_details] if manga_details else []
        
        if query:
            # Text search
            url = f"{self.API_URL}/v1.0/search"
            params = {
                "q": query.strip(),
                "limit": 300,  # Use a higher limit for better results
                "page": 1,
                "tachiyomi": "true"
            }
            
            response = self._make_request(url, params=params)
            if not response:
                return []
            
            # Transform the results
            manga_list = []
            for item in response:
                manga = {
                    "id": item.get("hid", ""),
                    "title": item.get("title", "Unknown"),
                    "url": f"/comic/{item.get('hid')}#", 
                    "thumbnail_url": self._parse_cover(item.get("cover_url"), item.get("md_covers", []))
                }
                manga_list.append(manga)
            
            return manga_list
        
        # Filter search
        url = f"{self.API_URL}/v1.0/search"
        params = {
            "limit": 300,  # Use a higher limit
            "page": 1,
            "tachiyomi": "true"
        }
        
        # Apply filters
        self._apply_filters(params, filters)
        
        # Add ignored tags from preferences
        if self.preferences["ignored_tags"]:
            ignored_tags = self.preferences["ignored_tags"].split(",")
            for tag in ignored_tags:
                if tag.strip():
                    params.setdefault("excluded-tags", []).append(self._format_tag(tag.strip()))
        
        all_results = []
        current_page = 1
        has_next_page = True
        
        # Fetch multiple pages if needed for filter search
        while has_next_page and current_page <= 5:  # Limit to 5 pages
            params["page"] = current_page
            response = self._make_request(url, params=params)
            
            if not response or len(response) == 0:
                has_next_page = False
                break
                
            # Transform the results
            for item in response:
                manga = {
                    "id": item.get("hid", ""),
                    "title": item.get("title", "Unknown"),
                    "url": f"/comic/{item.get('hid')}#", 
                    "thumbnail_url": self._parse_cover(item.get("cover_url"), item.get("md_covers", [])),
                    "description": item.get("desc", ""),
                    "status": self._parse_status(item.get("status"), item.get("translation_completed"))
                }
                all_results.append(manga)
            
            # Check if we should continue to next page
            if len(response) < params["limit"]:
                has_next_page = False
            else:
                current_page += 1
        
        return all_results
    
    def _paginate_search_results(self, page: int) -> List[Dict[str, Any]]:
        """Paginate search results."""
        start = (page - 1) * self.PAGE_SIZE
        end = min(page * self.PAGE_SIZE, len(self.search_results))
        
        if start >= len(self.search_results):
            return []
        
        manga_list = []
        for item in self.search_results[start:end]:
            manga = {
                "id": item.get("hid", ""),
                "title": item.get("title", "Unknown"),
                "url": f"/comic/{item.get('hid')}#",
                "thumbnail_url": self._parse_cover(item.get("cover_url"), item.get("md_covers", []))
            }
            manga_list.append(manga)
        
        return manga_list
    
    def get_manga_details(self, manga: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about a manga."""
        print(f"🔍 Getting manga details for: {manga.get('title', manga.get('url', 'Unknown'))}")
        
        # Migration from slug based urls to hid based ones
        if not manga['url'].endswith("#"):
            raise Exception("URL format has changed, please update")
        
        manga_url = manga['url'].rstrip("#")
        url = f"{self.API_URL}{manga_url}"
        params = {"tachiyomi": "true"}
        
        response = self._make_request(url, params=params)
        if not response:
            return {}
        
        comic_data = response.get("comic", {})
        authors_data = response.get("authors", [])
        artists_data = response.get("artists", [])
        genres_data = response.get("genres", [])
        demographic = response.get("demographic")
        
        title_lang = self.comick_lang.lower() if self.preferences["local_title"] else "all"
        
        # Find appropriate title
        alt_titles = comic_data.get("md_titles", [])
        entry_title = comic_data.get("title", "Unknown")
        
        for alt in alt_titles:
            if (title_lang != "all" and 
                alt.get("lang") and 
                title_lang.startswith(alt.get("lang")) and
                alt.get("title")):
                entry_title = alt["title"]
                break
        
        # Cover handling
        cover_url = comic_data.get("cover_url")
        md_covers = comic_data.get("md_covers", [])
        
        if not self.preferences["update_cover"] and manga.get("thumbnail_url") != cover_url:
            # Get covers
            covers_url = f"{self.API_URL}/comic/{comic_data.get('slug') or comic_data.get('hid')}/covers"
            covers_params = {"tachiyomi": "true"}
            covers_response = self._make_request(covers_url, params=covers_params)
            
            if covers_response:
                all_covers = covers_response.get("md_covers", [])[::-1]  # Reverse to match Kotlin
                first_vol_covers = [c for c in all_covers if c.get("vol") == "1"]
                if not first_vol_covers:
                    first_vol_covers = all_covers
                
                iso_lang = comic_data.get("iso639_1", "")
                original_covers = [c for c in first_vol_covers if iso_lang and iso_lang.startswith(c.get("locale", ""))]
                local_covers = [c for c in first_vol_covers if self.comick_lang.startswith(c.get("locale", ""))]
                
                selected_covers = local_covers or original_covers or first_vol_covers
                md_covers = selected_covers
        
        # Build description
        score_position = self.preferences["score_position"]
        description = ""
        
        # Format score for description
        fancy_score = ""
        if comic_data.get("bayesian_rating"):
            score = float(comic_data["bayesian_rating"])
            stars = round(score / 2)
            fancy_score = "★" * stars + "☆" * (5 - stars) + f" {score}"
        
        # Add score at top if configured
        if score_position == "top" and fancy_score:
            description += fancy_score
        
        # Add main description
        if comic_data.get("desc"):
            desc = self._beautify_description(comic_data["desc"])
            if description:
                description += "\n\n"
            description += desc
        
        # Add score in middle if configured
        if score_position == "middle" and fancy_score:
            if description:
                description += "\n\n"
            description += fancy_score
        
        # Add alternative titles if configured
        if self.preferences["show_alternative_titles"] and alt_titles:
            # Collect all titles
            all_titles = [{"title": comic_data.get("title")}] + alt_titles
            alt_title_list = []
            
            for title in all_titles:
                if title.get("title") and title.get("title") != entry_title:
                    alt_title_list.append(f"• {title['title']}")
            
            if alt_title_list:
                if description:
                    description += "\n\n"
                description += "Alternative Titles:\n" + "\n".join(alt_title_list)
        
        # Add score at bottom if configured
        if score_position == "bottom" and fancy_score:
            if description:
                description += "\n\n"
            description += fancy_score
        
        # Get status
        status = self._parse_status(comic_data.get("status"), comic_data.get("translation_completed"))
        
        # Process genres
        genres = []
        
        # Add origination
        country = comic_data.get("country")
        if country == "jp":
            genres.append({"group": "Origination", "name": "Manga"})
        elif country == "kr":
            genres.append({"group": "Origination", "name": "Manhwa"})
        elif country == "cn":
            genres.append({"group": "Origination", "name": "Manhua"})
        
        # Add demographic
        if demographic:
            genres.append({"group": "Demographic", "name": demographic})
        
        # Add MD genres
        md_genres = comic_data.get("md_comic_md_genres", [])
        for genre in md_genres:
            md_genre = genre.get("md_genres")
            if md_genre and md_genre.get("name"):
                genres.append({
                    "group": md_genre.get("group", ""),
                    "name": md_genre.get("name", "")
                })
        
        # Add regular genres
        for genre in genres_data:
            if genre.get("name"):
                genres.append({
                    "group": genre.get("group", ""),
                    "name": genre.get("name", "")
                })
        
        # Add MU tags if configured
        if self.preferences["include_mu_tags"]:
            mu_comics = comic_data.get("mu_comics", {})
            mu_categories = mu_comics.get("mu_comic_categories", [])
            
            for category in mu_categories:
                if category and category.get("mu_categories") and category["mu_categories"].get("title"):
                    genres.append({
                        "group": "Category",
                        "name": category["mu_categories"]["title"]
                    })
        
        # Format genres
        formatted_genres = []
        genres = [g for g in genres if g.get("name") and g.get("group")]
        genres.sort(key=lambda x: (x.get("name", ""), x.get("group", "")))
        
        for genre in genres:
            if self.preferences["group_tags"]:
                formatted_genres.append(f"{genre['group']}:{genre['name'].strip()}")
            else:
                formatted_genres.append(genre['name'].strip())
        
        # Remove duplicates
        formatted_genres = list(dict.fromkeys(formatted_genres))
        
        # Collect authors and artists
        authors = [a.get("name", "").strip() for a in authors_data if a.get("name")]
        artists = [a.get("name", "").strip() for a in artists_data if a.get("name")]
        
        # Build final manga object
        result = {
            "id": comic_data.get("hid", ""),
            "url": manga_url + "#",
            "title": entry_title,
            "author": ", ".join(authors),
            "artist": ", ".join(artists),
            "description": description,
            "genres": formatted_genres,
            "status": status,
            "thumbnail_url": self._parse_cover(cover_url, md_covers),
            "hid": comic_data.get("hid", ""),
            "slug": comic_data.get("slug"),
        }
        
        return result
    
    def get_chapters(self, manga: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get chapters for a manga."""
        print(f"🔍 Getting chapters for: {manga.get('title', manga.get('url', 'Unknown'))}")
        
        # Migration from slug based urls to hid based ones
        if not manga['url'].endswith("#"):
            raise Exception("URL format has changed, please update")
        
        manga_url = manga['url'].rstrip("#")
        url = f"{self.API_URL}{manga_url}/chapters"
        
        params = {
            "tachiyomi": "true",
            "limit": str(self.CHAPTERS_LIMIT)
        }
        
        if self.comick_lang != "all":
            params["lang"] = self.comick_lang
        
        response = self._make_request(url, params=params)
        if not response:
            return []
        
        chapters_data = response.get("chapters", [])
        current_timestamp = int(time.time() * 1000)
        
        chapters = []
        for chapter in chapters_data:
            # Check if chapter is published
            publish_time = self._parse_date(chapter.get("publish_at", ""))
            if publish_time > current_timestamp:
                continue
            
            # Check if group is in ignored groups
            chapter_groups = [g.lower() for g in chapter.get("group_name", [])]
            if any(g in self.preferences["ignored_groups"] for g in chapter_groups):
                continue
            
            # Safely get chapter and volume numbers
            chap_str = chapter.get("chap", "0")
            vol_str = chapter.get("vol", "0")
            
            # Check if values are not None before using replace
            chap_is_digit = False
            if chap_str is not None:
                chap_is_digit = chap_str.replace(".", "", 1).isdigit()
            
            vol_is_digit = False
            if vol_str is not None:
                vol_is_digit = vol_str.replace(".", "", 1).isdigit()
            
            # Parse chapter data
            chapter_data = {
                "id": chapter.get("hid", ""),
                "url": f"{manga_url}/{chapter.get('hid', '')}-chapter-{chap_str or ''}-{chapter.get('lang', '')}",
                "name": self._beautify_chapter_name(
                    vol_str or "",
                    chap_str or "",
                    chapter.get("title", "")
                ),
                "uploaded": self._parse_date(chapter.get("created_at", "")),
                "scanlator": ", ".join(chapter.get("group_name", [])) or "Unknown",
                "chapter_number": float(chap_str) if chap_is_digit else 0,
                "volume": float(vol_str) if vol_is_digit else None,
            }
            
            chapters.append(chapter_data)
        
        # Sort by chapter number descending
        chapters.sort(key=lambda x: (x.get("volume", 0) or 0, x.get("chapter_number", 0) or 0), reverse=True)
        
        return chapters
    
    def get_pages(self, chapter: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get pages for a chapter."""
        print(f"🔍 Getting pages for chapter: {chapter.get('name', chapter.get('url', 'Unknown'))}")
        
        chapter_hid = chapter["url"].split("/")[-1].split("-")[0]
        url = f"{self.API_URL}/chapter/{chapter_hid}"
        params = {"tachiyomi": "true"}
        
        response = self._make_request(url, params=params)
        if not response:
            return []
        
        chapter_data = response.get("chapter", {})
        images = chapter_data.get("images", [])
        
        if not images:
            # Try cache busting
            params["_"] = str(int(time.time() * 1000))
            response = self._make_request(url, params=params)
            if response:
                chapter_data = response.get("chapter", {})
                images = chapter_data.get("images", [])
        
        pages = []
        for i, img in enumerate(images):
            if img.get("url"):
                pages.append({
                    "index": i,
                    "url": img["url"]
                })
        
        return pages
    
    def _make_request(self, url: str, params: Optional[Dict[str, Any]] = None, method: str = "GET", retries: int = 3) -> Any:
        """Make a request to the API with retry logic."""
        try:
            # Prepare params for GET request
            if method == "GET" and params:
                # Convert list params to multiple query params with same name
                query_params = []
                for key, value in params.items():
                    if isinstance(value, list):
                        for item in value:
                            query_params.append((key, item))
                    else:
                        query_params.append((key, value))
                
                # Build URL with query parameters
                url_parts = list(urllib.parse.urlparse(url))
                query = urllib.parse.urlencode(query_params, doseq=True)
                url_parts[4] = query
                url = urllib.parse.urlunparse(url_parts)
                params = None
            
            # Try the request with retries
            last_error = None
            for attempt in range(retries):
                try:
                    response = self.session.request(
                        method,
                        url,
                        params=params,
                        headers=self.headers,
                        timeout=30
                    )
                    response.raise_for_status()
                    
                    # Parse JSON response
                    data = response.json()
                    
                    # Check for API error
                    if isinstance(data, dict) and "statusCode" in data and "message" in data:
                        print(f"❌ API error: {data['statusCode']} - {data['message']}")
                        return None
                    
                    return data
                    
                except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
                    last_error = e
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"⚠️ Request attempt {attempt+1}/{retries} failed: {e}")
                    print(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
            
            # If we get here, all retries failed
            print(f"❌ All {retries} request attempts failed. Last error: {last_error}")
            return None
            
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return None
    
    def _apply_filters(self, params: Dict[str, Any], filters: Dict[str, Any]):
        """Apply filters to search parameters."""
        # Sort filter
        if "sort" in filters:
            params["sort"] = filters["sort"]
        
        # Country filter
        if "country" in filters:
            params["country"] = filters["country"]
        
        # Demographic filter
        if "demographic" in filters:
            params["demographic"] = filters["demographic"]
        
        # Status filter
        if "status" in filters:
            params["status"] = filters["status"]
        
        # Content rating filter
        if "content_rating" in filters:
            params["content_rating"] = filters["content_rating"]
        
        # Completed filter
        if "completed" in filters and filters["completed"]:
            params["completed"] = "true"
        
        # Created at filter
        if "time" in filters:
            params["time"] = filters["time"]
        
        # Minimum chapters filter
        if "minimum" in filters:
            params["minimum"] = filters["minimum"]
        
        # Year range filters
        if "from" in filters:
            params["from"] = filters["from"]
        if "to" in filters:
            params["to"] = filters["to"]
        
        # Genre filters
        if "genres" in filters:
            params["genres"] = filters["genres"]
        
        # Excluded genres
        if "excludes" in filters:
            params["excludes"] = filters["excludes"]
        
        # Tags
        if "tags" in filters:
            for tag in filters["tags"].split(","):
                tag = tag.strip()
                if tag:
                    params.setdefault("tags", []).append(self._format_tag(tag))
        
        # Excluded tags
        if "excluded_tags" in filters:
            for tag in filters["excluded_tags"].split(","):
                tag = tag.strip()
                if tag:
                    params.setdefault("excluded-tags", []).append(self._format_tag(tag))
    
    def _format_tag(self, tag: str) -> str:
        """Format a tag for API request."""
        formatted = tag.lower().replace(" ", "-").replace("/", "-")
        formatted = formatted.replace("'-", "-and-039-").replace("'", "-and-039-")
        return formatted
    
    def _parse_cover(self, thumbnail_url: Optional[str], md_covers: List[Dict[str, Any]]) -> Optional[str]:
        """Parse cover URL from data."""
        b2key = None
        vol = ""
        
        for cover in md_covers:
            if cover.get("b2key"):
                b2key = cover["b2key"]
                vol = cover.get("vol", "")
                break
        
        if not b2key or not thumbnail_url:
            return thumbnail_url
        
        return f"{thumbnail_url.rsplit('/', 1)[0]}/{b2key}#{vol}"
    
    def _beautify_description(self, description: str) -> str:
        """Clean up manga description."""
        # Remove entities
        description = description.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
        
        # Remove content after "---"
        if "---" in description:
            description = description.split("---")[0]
        
        # Remove Markdown links
        description = re.sub(r'\[([^]]+)]\(([^)]+)\)', r'\1', description)
        
        # Remove Markdown italic/bold
        description = re.sub(r'\*+\s*([^*]*)\s*\*+', r'\1', description)
        description = re.sub(r'_+\s*([^_]*)\s*_+', r'\1', description)
        
        return description.strip()
    
    def _parse_status(self, status: Optional[int], translation_complete: Optional[bool]) -> str:
        """Parse manga status."""
        if status == 1:
            return "Ongoing"
        elif status == 2:
            if translation_complete:
                return "Completed"
            else:
                return "Publication Complete"
        elif status == 3:
            return "Cancelled"
        elif status == 4:
            return "On Hiatus"
        else:
            return "Unknown"
    
    def _beautify_chapter_name(self, vol: str, chap: str, title: str) -> str:
        """Format chapter name."""
        result = []
        
        if vol:
            if not chap:
                result.append(f"Volume {vol}")
            else:
                result.append(f"Vol. {vol}")
        
        if chap:
            if not vol:
                result.append(f"Chapter {chap}")
            else:
                result.append(f"Ch. {chap}")
        
        if title:
            if not chap:
                result.append(title)
            else:
                result.append(f": {title}")
        
        return "".join(result)
    
    def _parse_date(self, date_string: str) -> int:
        """Parse date string to timestamp."""
        if not date_string:
            return 0
        
        try:
            dt_format = "%Y-%m-%dT%H:%M:%S.%fZ"
            if "." not in date_string:
                dt_format = "%Y-%m-%dT%H:%M:%SZ"
            
            dt = datetime.strptime(date_string, dt_format)
            return int(dt.timestamp() * 1000)
        except Exception:
            return 0

# Filter definitions for Comick
class ComickFilters:
    @staticmethod
    def get_filters():
        """Get filter definitions for ComicK."""
        return {
            "genres": ComickFilters.get_genres_list(),
            "demographics": ComickFilters.get_demographic_list(),
            "types": ComickFilters.get_type_list(),
            "created_at": ComickFilters.get_created_at_list(),
            "sorts": ComickFilters.get_sorts_list(),
            "statuses": ComickFilters.get_status_list(),
            "content_ratings": ComickFilters.get_content_rating_list(),
        }
    
    @staticmethod
    def get_genres_list():
        return [
            {"title": "4-Koma", "value": "4-koma"},
            {"title": "Action", "value": "action"},
            {"title": "Adaptation", "value": "adaptation"},
            {"title": "Adult", "value": "adult"},
            {"title": "Adventure", "value": "adventure"},
            {"title": "Aliens", "value": "aliens"},
            {"title": "Animals", "value": "animals"},
            {"title": "Anthology", "value": "anthology"},
            {"title": "Award Winning", "value": "award-winning"},
            {"title": "Comedy", "value": "comedy"},
            {"title": "Cooking", "value": "cooking"},
            {"title": "Crime", "value": "crime"},
            {"title": "Crossdressing", "value": "crossdressing"},
            {"title": "Delinquents", "value": "delinquents"},
            {"title": "Demons", "value": "demons"},
            {"title": "Doujinshi", "value": "doujinshi"},
            {"title": "Drama", "value": "drama"},
            {"title": "Ecchi", "value": "ecchi"},
            {"title": "Fan Colored", "value": "fan-colored"},
            {"title": "Fantasy", "value": "fantasy"},
            {"title": "Full Color", "value": "full-color"},
            {"title": "Gender Bender", "value": "gender-bender"},
            {"title": "Genderswap", "value": "genderswap"},
            {"title": "Ghosts", "value": "ghosts"},
            {"title": "Gore", "value": "gore"},
            {"title": "Gyaru", "value": "gyaru"},
            {"title": "Harem", "value": "harem"},
            {"title": "Historical", "value": "historical"},
            {"title": "Horror", "value": "horror"},
            {"title": "Incest", "value": "incest"},
            {"title": "Isekai", "value": "isekai"},
            {"title": "Loli", "value": "loli"},
            {"title": "Long Strip", "value": "long-strip"},
            {"title": "Mafia", "value": "mafia"},
            {"title": "Magic", "value": "magic"},
            {"title": "Magical Girls", "value": "magical-girls"},
            {"title": "Martial Arts", "value": "martial-arts"},
            {"title": "Mature", "value": "mature"},
            {"title": "Mecha", "value": "mecha"},
            {"title": "Medical", "value": "medical"},
            {"title": "Military", "value": "military"},
            {"title": "Monster Girls", "value": "monster-girls"},
            {"title": "Monsters", "value": "monsters"},
            {"title": "Music", "value": "music"},
            {"title": "Mystery", "value": "mystery"},
            {"title": "Ninja", "value": "ninja"},
            {"title": "Office Workers", "value": "office-workers"},
            {"title": "Official Colored", "value": "official-colored"},
            {"title": "Oneshot", "value": "oneshot"},
            {"title": "Philosophical", "value": "philosophical"},
            {"title": "Police", "value": "police"},
            {"title": "Post-Apocalyptic", "value": "post-apocalyptic"},
            {"title": "Psychological", "value": "psychological"},
            {"title": "Reincarnation", "value": "reincarnation"},
            {"title": "Reverse Harem", "value": "reverse-harem"},
            {"title": "Romance", "value": "romance"},
            {"title": "Samurai", "value": "samurai"},
            {"title": "School Life", "value": "school-life"},
            {"title": "Sci-Fi", "value": "sci-fi"},
            {"title": "Sexual Violence", "value": "sexual-violence"},
            {"title": "Shota", "value": "shota"},
            {"title": "Shoujo Ai", "value": "shoujo-ai"},
            {"title": "Shounen Ai", "value": "shounen-ai"},
            {"title": "Slice of Life", "value": "slice-of-life"},
            {"title": "Smut", "value": "smut"},
            {"title": "Sports", "value": "sports"},
            {"title": "Superhero", "value": "superhero"},
            {"title": "Supernatural", "value": "supernatural"},
            {"title": "Survival", "value": "survival"},
            {"title": "Thriller", "value": "thriller"},
            {"title": "Time Travel", "value": "time-travel"},
            {"title": "Traditional Games", "value": "traditional-games"},
            {"title": "Tragedy", "value": "tragedy"},
            {"title": "User Created", "value": "user-created"},
            {"title": "Vampires", "value": "vampires"},
            {"title": "Video Games", "value": "video-games"},
            {"title": "Villainess", "value": "villainess"},
            {"title": "Virtual Reality", "value": "virtual-reality"},
            {"title": "Web Comic", "value": "web-comic"},
            {"title": "Wuxia", "value": "wuxia"},
            {"title": "Yaoi", "value": "yaoi"},
            {"title": "Yuri", "value": "yuri"},
            {"title": "Zombies", "value": "zombies"},
        ]
    
    @staticmethod
    def get_demographic_list():
        return [
            {"title": "Shounen", "value": "1"},
            {"title": "Shoujo", "value": "2"},
            {"title": "Seinen", "value": "3"},
            {"title": "Josei", "value": "4"},
            {"title": "None", "value": "5"},
        ]
    
    @staticmethod
    def get_type_list():
        return [
            {"title": "Manga", "value": "jp"},
            {"title": "Manhwa", "value": "kr"},
            {"title": "Manhua", "value": "cn"},
            {"title": "Others", "value": "others"},
        ]
    
    @staticmethod
    def get_created_at_list():
        return [
            {"title": "Any time", "value": ""},
            {"title": "3 days", "value": "3"},
            {"title": "7 days", "value": "7"},
            {"title": "30 days", "value": "30"},
            {"title": "3 months", "value": "90"},
            {"title": "6 months", "value": "180"},
            {"title": "1 year", "value": "365"},
        ]
    
    @staticmethod
    def get_sorts_list():
        return [
            {"title": "Most popular", "value": "follow"},
            {"title": "Most follows", "value": "user_follow_count"},
            {"title": "Most views", "value": "view"},
            {"title": "High rating", "value": "rating"},
            {"title": "Last updated", "value": "uploaded"},
            {"title": "Newest", "value": "created_at"},
        ]
    
    @staticmethod
    def get_status_list():
        return [
            {"title": "All", "value": "0"},
            {"title": "Ongoing", "value": "1"},
            {"title": "Completed", "value": "2"},
            {"title": "Cancelled", "value": "3"},
            {"title": "Hiatus", "value": "4"},
        ]
    
    @staticmethod
    def get_content_rating_list():
        return [
            {"title": "All", "value": ""},
            {"title": "Safe", "value": "safe"},
            {"title": "Suggestive", "value": "suggestive"},
            {"title": "Erotica", "value": "erotica"},
        ]
