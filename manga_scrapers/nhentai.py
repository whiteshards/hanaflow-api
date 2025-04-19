
import json
import re
import time
import requests
import cloudscraper
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from datetime import datetime

class NHentaiScraper:
    """Scraper for nhentai based on the Kotlin implementation"""
    
    # Constants
    BASE_URL = "https://nhentai.net"
    API_URL = "https://nhentai.net/api"
    ID_SEARCH_PREFIX = "id:"
    
    # Image type mapping
    IMAGE_TYPES = {
        "j": "jpg",
        "p": "png",
        "g": "gif",
        "w": "webp"
    }
    
    def __init__(self, language: str = "all"):
        """Initialize NHentaiScraper with optional language preference."""
        self.language = language
        self.session = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Referer": self.BASE_URL,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "sec-ch-ua": '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
            "sec-ch-ua-mobile": "?0"
        }
        
        # Preferences (you can extend these)
        self.preferences = {
            "display_full_title": True,
            "media_server": 1
        }
    
    def search_manga(self, query: str, page: int = 1, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search for manga with filters."""
        print(f"🔍 Searching for doujin: '{query}' (page {page})...")
        
        filters = filters or {}
        
        # Handle ID search
        if query.startswith(self.ID_SEARCH_PREFIX):
            id_value = query[len(self.ID_SEARCH_PREFIX):]
            manga_details = self.get_manga_details({"id": id_value, "url": f"/g/{id_value}/"})
            return [manga_details] if manga_details else []
        
        # Handle direct numeric ID
        if query.isdigit():
            manga_details = self.get_manga_details({"id": query, "url": f"/g/{query}/"})
            return [manga_details] if manga_details else []
        
        # Process search URL
        base_search_url = f"{self.BASE_URL}/search"
        url_params = {
            "q": self._build_search_query(query, filters),
            "page": page
        }
        
        # Add sort parameter if present
        if "sort" in filters:
            url_params["sort"] = filters["sort"]
        
        # Handle favorites
        if filters.get("favorites_only", False):
            base_search_url = f"{self.BASE_URL}/favorites"
        
        # Make the request
        try:
            response = self.session.get(
                base_search_url, 
                params=url_params, 
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            return self._parse_search_results(soup)
            
        except Exception as e:
            print(f"❌ Error searching nhentai: {e}")
            return []
    
    def _build_search_query(self, query: str, filters: Dict[str, Any]) -> str:
        """Build search query with filters."""
        search_parts = [query] if query else []
        
        # Add language filter if not 'all'
        if self.language != "all" and self.language:
            search_parts.append(f"language:{self.language}")
        
        # Process advanced search filters
        for filter_type in ["tag", "category", "artist", "group", "parody", "character"]:
            if filter_type in filters:
                tags = filters[filter_type].split(",")
                for tag in tags:
                    tag = tag.strip()
                    if tag:
                        prefix = "-" if tag.startswith("-") else ""
                        clean_tag = tag[1:] if prefix else tag
                        search_parts.append(f"{prefix}{filter_type}:\"{clean_tag}\"")
        
        # Process numeric filters (pages, uploaded)
        if "pages" in filters and filters["pages"]:
            search_parts.append(f"pages:{filters['pages']}")
            
        if "uploaded" in filters and filters["uploaded"]:
            search_parts.append(f"uploaded:{filters['uploaded']}")
        
        return " ".join(search_parts)
    
    def _parse_search_results(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Parse search results page."""
        results = []
        gallery_elements = soup.select(".gallery")
        
        for element in gallery_elements:
            try:
                # Get the URL and ID
                url_element = element.select_one("a")
                if not url_element:
                    continue
                    
                relative_url = url_element.get("href", "")
                manga_id = relative_url.split("/")[-2] if relative_url else ""
                
                # Get the title
                title_element = element.select_one("a > div.caption")
                title = title_element.text.strip() if title_element else "Unknown Title"
                
                # Get thumbnail
                thumb_element = element.select_one(".cover img")
                thumbnail_url = None
                if thumb_element:
                    thumbnail_url = thumb_element.get("data-src") or thumb_element.get("src")
                
                # Process title based on preference
                if not self.preferences["display_full_title"]:
                    title = self._shorten_title(title)
                
                # Create manga item
                manga = {
                    "id": manga_id,
                    "title": title,
                    "url": relative_url,
                    "thumbnail_url": thumbnail_url,
                    "source": "nhentai"
                }
                results.append(manga)
                
            except Exception as e:
                print(f"Error processing a search result: {e}")
                continue
        
        return results
    
    def _shorten_title(self, title: str) -> str:
        """Shorten title by removing bracketed/parenthesized text."""
        pattern = r"(\[[^\]]*\]|\([^)]*\)|\{[^}]*\})"
        return re.sub(pattern, "", title).strip()
    
    def get_popular_manga(self, page: int = 1) -> List[Dict[str, Any]]:
        """Get popular manga list."""
        print(f"🔍 Getting popular doujinshi (page {page})...")
        
        filters = {"sort": "popular"}
        return self.search_manga("", page, filters)
    
    def get_latest_manga(self, page: int = 1) -> List[Dict[str, Any]]:
        """Get latest manga list."""
        print(f"🔍 Getting latest doujinshi (page {page})...")
        
        # For latest, we don't need a sort parameter as date is default
        return self.search_manga("", page)
    
    def get_manga_details(self, manga: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about a manga."""
        manga_id = manga.get("id", "")
        if not manga_id:
            # Try to extract from URL
            url = manga.get("url", "")
            manga_id = url.split("/")[-2] if url else ""
            
        if not manga_id:
            print("❌ No manga ID found")
            return {}
            
        print(f"🔍 Getting doujin details for ID: {manga_id}")
        
        try:
            response = self.session.get(
                f"{self.BASE_URL}/g/{manga_id}/",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract JSON data from script
            script_data = soup.select_one("#__nuxt")
            if not script_data:
                script_data = soup.select_one("script:contains(JSON.parse)")
            
            if not script_data:
                return self._parse_manga_details_html(soup, manga_id)
            
            # Try to extract JSON data using regex
            json_match = re.search(r'JSON\.parse\(\s*"(.*)"\s*\)', script_data.string)
            if not json_match:
                return self._parse_manga_details_html(soup, manga_id)
            
            # Parse the JSON data
            json_str = json_match.group(1)
            # Unescape unicode
            json_str = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), json_str)
            # Unescape other escape sequences
            json_str = json_str.replace('\\"', '"').replace('\\\\', '\\')
            
            data = json.loads(json_str)
            return self._parse_manga_details_json(data, manga_id)
            
        except Exception as e:
            print(f"❌ Error getting manga details: {e}")
            # Try fallback to HTML parsing
            return self._parse_manga_details_html(soup, manga_id)
    
    def _parse_manga_details_json(self, data: Dict[str, Any], manga_id: str) -> Dict[str, Any]:
        """Parse manga details from JSON data."""
        # Extract information
        titles = data.get("title", {})
        english_title = titles.get("english")
        japanese_title = titles.get("japanese")
        pretty_title = titles.get("pretty")
        
        # Select display title based on preference
        if self.preferences["display_full_title"]:
            display_title = english_title or japanese_title or pretty_title or f"Gallery #{manga_id}"
        else:
            display_title = pretty_title or self._shorten_title(english_title or japanese_title or f"Gallery #{manga_id}")
        
        # Extract cover image
        cover_url = None
        media_id = data.get("media_id", "")
        if media_id:
            cover_url = f"https://t.nhentai.net/galleries/{media_id}/cover.jpg"
        
        # Process tags
        tags = data.get("tags", [])
        artist_tags = [tag.get("name") for tag in tags if tag.get("type") == "artist"]
        group_tags = [tag.get("name") for tag in tags if tag.get("type") == "group"]
        category_tags = [tag.get("name") for tag in tags if tag.get("type") == "category"]
        parody_tags = [tag.get("name") for tag in tags if tag.get("type") == "parody"]
        character_tags = [tag.get("name") for tag in tags if tag.get("type") == "character"]
        general_tags = [tag.get("name") for tag in tags if tag.get("type") == "tag"]
        
        # Build manga details
        manga_details = {
            "id": manga_id,
            "url": f"/g/{manga_id}/",
            "title": display_title,
            "cover_url": cover_url,
            "author": ", ".join(artist_tags),
            "artist": ", ".join(artist_tags),
            "groups": ", ".join(group_tags),
            "pages": len(data.get("images", {}).get("pages", [])),
            "favorites": data.get("num_favorites", 0),
            "upload_date": data.get("upload_date", 0),
            "description": "",
            "genres": ", ".join(general_tags),
            "parodies": ", ".join(parody_tags),
            "characters": ", ".join(character_tags),
            "categories": ", ".join(category_tags),
            "source": "nhentai",
            # Store raw data for chapter list and page list
            "_raw_data": data
        }
        
        # Build detailed description
        description = f"Full English and Japanese titles:\n"
        if english_title:
            description += f"{english_title}\n"
        if japanese_title:
            description += f"{japanese_title}\n"
        
        description += f"\nPages: {manga_details['pages']}\n"
        description += f"Favorited by: {manga_details['favorites']}\n"
        
        if category_tags:
            description += f"\nCategories: {', '.join(category_tags)}\n"
        if parody_tags:
            description += f"Parodies: {', '.join(parody_tags)}\n"
        if character_tags:
            description += f"Characters: {', '.join(character_tags)}\n"
        
        manga_details["description"] = description
        
        return manga_details
    
    def _parse_manga_details_html(self, soup: BeautifulSoup, manga_id: str) -> Dict[str, Any]:
        """Parse manga details from HTML as fallback."""
        try:
            # Get title
            title_element = soup.select_one("#info > h1")
            title = title_element.text.strip() if title_element else f"Gallery #{manga_id}"
            
            # Get cover image
            cover_element = soup.select_one("#cover > a > img")
            cover_url = cover_element.get("data-src") if cover_element else None
            
            # Get tags
            tag_containers = soup.select("#tags > .tag-container")
            
            artist_tags = []
            group_tags = []
            category_tags = []
            parody_tags = []
            character_tags = []
            general_tags = []
            
            for container in tag_containers:
                tag_type_element = container.select_one(".tag-container > span.tags")
                if not tag_type_element:
                    continue
                    
                tag_type = tag_type_element.text.strip().lower()
                tags = [tag.text.strip() for tag in container.select("a.tag > span.name")]
                
                if "artist" in tag_type:
                    artist_tags = tags
                elif "group" in tag_type:
                    group_tags = tags
                elif "categor" in tag_type:
                    category_tags = tags
                elif "parody" in tag_type:
                    parody_tags = tags
                elif "character" in tag_type:
                    character_tags = tags
                elif "tag" in tag_type:
                    general_tags = tags
            
            # Get page count
            pages_element = soup.select_one("#info > div")
            pages_text = pages_element.text if pages_element else ""
            pages_match = re.search(r'(\d+) pages', pages_text)
            pages = int(pages_match.group(1)) if pages_match else 0
            
            # Build manga details
            manga_details = {
                "id": manga_id,
                "url": f"/g/{manga_id}/",
                "title": title if self.preferences["display_full_title"] else self._shorten_title(title),
                "cover_url": cover_url,
                "author": ", ".join(artist_tags),
                "artist": ", ".join(artist_tags),
                "groups": ", ".join(group_tags),
                "pages": pages,
                "favorites": 0,  # Can't reliably get this from HTML
                "upload_date": 0,  # Can't reliably get this from HTML
                "description": "",
                "genres": ", ".join(general_tags),
                "parodies": ", ".join(parody_tags),
                "characters": ", ".join(character_tags),
                "categories": ", ".join(category_tags),
                "source": "nhentai"
            }
            
            # Build description
            description = f"Title: {title}\n\n"
            description += f"Pages: {pages}\n"
            
            if category_tags:
                description += f"\nCategories: {', '.join(category_tags)}\n"
            if parody_tags:
                description += f"Parodies: {', '.join(parody_tags)}\n"
            if character_tags:
                description += f"Characters: {', '.join(character_tags)}\n"
            
            manga_details["description"] = description
            
            return manga_details
            
        except Exception as e:
            print(f"❌ Error parsing HTML details: {e}")
            return {
                "id": manga_id,
                "url": f"/g/{manga_id}/",
                "title": f"Gallery #{manga_id}",
                "description": "Error loading details",
                "source": "nhentai"
            }
    
    def get_chapters(self, manga: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get chapters for a manga (doujins are single chapter)."""
        print(f"🔍 Getting chapters for: {manga.get('title', manga.get('id', 'Unknown'))}")
        
        # Doujinshi are single chapter
        manga_id = manga.get("id", "")
        if not manga_id:
            url = manga.get("url", "")
            manga_id = url.split("/")[-2] if url else ""
        
        upload_date = manga.get("upload_date", 0)
        if not upload_date:
            # Try to get it from _raw_data
            raw_data = manga.get("_raw_data", {})
            upload_date = raw_data.get("upload_date", int(time.time()))
        
        return [{
            "id": manga_id,
            "url": f"/g/{manga_id}/",
            "name": "Chapter",
            "title": manga.get("title", f"Gallery #{manga_id}"),
            "scanlator": manga.get("groups", ""),
            "date_upload": upload_date * 1000 if upload_date < 9999999999 else upload_date,
            "chapter_number": 1,
            "source": "nhentai"
        }]
    
    def get_pages(self, chapter: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get pages for a chapter."""
        print(f"🔍 Getting pages for chapter: {chapter.get('name', chapter.get('url', 'Unknown'))}")
        
        manga_id = chapter.get("id", "")
        if not manga_id:
            url = chapter.get("url", "")
            manga_id = url.split("/")[-2] if url else ""
        
        if not manga_id:
            print("❌ No manga ID found for pages")
            return []
        
        try:
            response = self.session.get(
                f"{self.BASE_URL}/g/{manga_id}/",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # First try to extract from script
            media_id = None
            pages_data = []
            
            # Try to find media server
            media_server = self.preferences["media_server"]
            media_server_match = re.search(r'media_server\s*:\s*(\d+)', response.text)
            if media_server_match:
                media_server = int(media_server_match.group(1))
            
            # Try to extract JSON data
            script_data = None
            for script in soup.select("script"):
                if script.string and "JSON.parse" in script.string:
                    script_data = script
                    break
                    
            if script_data:
                json_match = re.search(r'JSON\.parse\(\s*"(.*)"\s*\)', script_data.string)
                if json_match:
                    json_str = json_match.group(1)
                    json_str = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), json_str)
                    json_str = json_str.replace('\\"', '"').replace('\\\\', '\\')
                    
                    try:
                        data = json.loads(json_str)
                        media_id = data.get("media_id", "")
                        
                        # Extract image data
                        images = data.get("images", {})
                        pages = images.get("pages", [])
                        
                        for i, page in enumerate(pages):
                            page_type = page.get("t", "j")
                            extension = self.IMAGE_TYPES.get(page_type, "jpg")
                            pages_data.append({
                                "index": i,
                                "url": f"https://i{media_server}.nhentai.net/galleries/{media_id}/{i + 1}.{extension}"
                            })
                    except json.JSONDecodeError:
                        print(f"Error parsing JSON data: {json_str[:100]}...")
                    except Exception as e:
                        print(f"Error processing JSON data: {e}")
            
            # If we couldn't extract from JSON, try HTML
            if not pages_data:
                print("Falling back to HTML parsing for pages...")
                # Try to get media ID from thumbnail
                thumb_element = soup.select_one("#cover img")
                if thumb_element:
                    thumb_url = thumb_element.get("data-src") or thumb_element.get("src") or ""
                    print(f"Thumbnail URL: {thumb_url}")
                    media_id_match = re.search(r'/galleries/(\d+)/', thumb_url)
                    if media_id_match:
                        media_id = media_id_match.group(1)
                        print(f"Found media ID: {media_id}")
                
                # Try to get media ID from other image elements if not found
                if not media_id:
                    thumb_elements = soup.select(".gallerythumb img")
                    for element in thumb_elements:
                        thumb_url = element.get("data-src") or element.get("src") or ""
                        media_id_match = re.search(r'/galleries/(\d+)/', thumb_url)
                        if media_id_match:
                            media_id = media_id_match.group(1)
                            print(f"Found media ID from thumbnails: {media_id}")
                            break
                
                # Get page count from info
                pages_element = soup.select_one("#info > div")
                pages_text = pages_element.text if pages_element else ""
                pages_match = re.search(r'(\d+) pages', pages_text)
                page_count = int(pages_match.group(1)) if pages_match else 0
                print(f"Detected page count: {page_count}")
                
                # Try to also find page count by counting thumbnails
                if not page_count:
                    page_count = len(soup.select(".gallerythumb"))
                    print(f"Counted thumbnails: {page_count}")
                
                if media_id and page_count:
                    # We don't know file extensions, so default to jpg
                    for i in range(page_count):
                        pages_data.append({
                            "index": i,
                            "url": f"https://i{media_server}.nhentai.net/galleries/{media_id}/{i + 1}.jpg"
                        })
                        
                # If still no pages, try alternative methods
                if not pages_data:
                    print("Trying alternative page extraction...")
                    # Look for direct image URLs in the page
                    img_elements = soup.select("#image-container img")
                    for i, img in enumerate(img_elements):
                        img_url = img.get("src") or img.get("data-src") or ""
                        if img_url:
                            pages_data.append({
                                "index": i,
                                "url": img_url
                            })
            
            # Write URLs to file for convenience
            with open('urls.txt', 'a', encoding='utf-8') as f:
                f.write(f"\n==== NHentai: {chapter.get('title', f'Gallery #{manga_id}')} ====\n")
                for i, page in enumerate(pages_data, 1):
                    f.write(f"Page {i}: {page.get('url', 'No URL')}\n")
            
            return pages_data
            
        except Exception as e:
            print(f"❌ Error getting pages: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_filters(self) -> Dict[str, Any]:
        """Get available filters for search."""
        return {
            "sort_options": [
                {"name": "Recent", "value": "date"},
                {"name": "Popular: All Time", "value": "popular"},
                {"name": "Popular: Month", "value": "popular-month"},
                {"name": "Popular: Week", "value": "popular-week"},
                {"name": "Popular: Today", "value": "popular-today"}
            ],
            "category_suggestions": [
                "doujinshi", "manga", "artistcg", "gamecg", "western",
                "non-h", "imageset", "cosplay", "asianporn", "misc"
            ],
            "tag_suggestions": [
                # Common tags, can be expanded
                "anal", "big breasts", "sole female", "sole male", "group",
                "nakadashi", "blowjob", "ahegao", "incest", "futanari",
                "shotacon", "lolicon", "femdom", "yaoi", "yuri",
                "monster", "netorare", "monster girl", "tentacles"
            ]
        }
