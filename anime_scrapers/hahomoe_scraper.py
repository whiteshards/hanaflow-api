import requests
from bs4 import BeautifulSoup
import sys
import time
import urllib.parse
import re
from typing import Dict, Any, List, Optional

class HahoMoeSearcher:
    def __init__(self):
        self.base_url = "https://haho.moe"
        self.search_url = f"{self.base_url}/anime"
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }

        # Set cookie for thumbnails
        self.session.cookies.set('loop-view', 'thumb', domain='haho.moe')

        # Set up filters (similar to HanimeScraper)
        self.active_filters = {
            "included_tags": [],
            "excluded_tags": [],
            "order_by": "vdy",  # Default to popularity (views)
            "ordering": "-d"    # Descending order
        }

        # Preferences for quality
        self.preferences = {
            "preferred_quality": "720p"  # Default preferred quality
        }

        # Quality options
        self.quality_list = ["1080p", "720p", "480p", "360p"]

    def search_anime(self, query, max_pages=5):
        """Search for anime on HahoMoe by title"""
        try:
            print(f"🔍 Searching for '{query}' on HahoMoe...")

            # Build search parameters from active filters
            search_params = self._get_search_parameters()
            order_by, ordering = search_params[2], search_params[3]
            sort_param = f"{order_by}{ordering}"

            # Encode the query for the URL
            encoded_query = urllib.parse.quote(query)

            # Prepare tag filters
            http_query = ""
            if self.active_filters["included_tags"]:
                included_tags = " ".join([f'genre:{tag}' for tag in self.active_filters["included_tags"]])
                http_query += f" {included_tags}"

            if self.active_filters["excluded_tags"]:
                excluded_tags = " ".join([f'-genre:{tag}' for tag in self.active_filters["excluded_tags"]])
                http_query += f" {excluded_tags}"

            results = []
            current_page = 1
            has_next_page = True

            while has_next_page and current_page <= max_pages:
                # Create the search URL with params for current page
                url = f"{self.search_url}?page={current_page}&s={sort_param}&q={encoded_query}"

                # Add tag filters if present
                if http_query:
                    url += f"&q={urllib.parse.quote(http_query.strip())}"

                print(f"Fetching HahoMoe search results page {current_page}...")
                response = self.session.get(url, headers=self.headers)

                if response.status_code != 200:
                    print(f"❌ Search failed with status code: {response.status_code}")
                    break

                soup = BeautifulSoup(response.text, 'html.parser')
                search_results = soup.select('ul.anime-loop.loop > li > a')

                if not search_results:
                    print(f"No results found on page {current_page}.")
                    break

                # Process results on this page
                page_results_count = 0
                for result in search_results:
                    try:
                        title_elem = result.select_one('div.label > span, div span.thumb-title')
                        title = title_elem.text.strip() if title_elem else "Unknown Title"
                        url = result.get('href')
                        full_url = self.base_url + url if not url.startswith('http') else url

                        # Get the poster image
                        poster_elem = result.select_one('img')
                        poster = poster_elem.get('src') if poster_elem else "No poster available"

                        # Try to get type and year if available
                        additional_info = result.select_one('div.fd-infor')
                        anime_type = "Unknown"
                        year = "Unknown"

                        if additional_info:
                            type_elem = additional_info.select_one('.fdi-item:nth-child(1)')
                            year_elem = additional_info.select_one('.fdi-item:nth-child(2)')

                            if type_elem:
                                anime_type = type_elem.text.strip()
                            if year_elem:
                                year = year_elem.text.strip()

                        # Add source identifier to differentiate from other results
                        results.append({
                            'id': url.split('/')[-1],
                            'title': f"{title} [HahoMoe]",
                            'url': full_url + "?s=srt-d",  # Add sort parameter
                            'poster': poster,
                            'type': anime_type,
                            'year': year,
                            'source': 'hahomoe'
                        })
                        page_results_count += 1
                    except Exception as e:
                        print(f"Error processing a HahoMoe result: {e}")
                        continue

                print(f"Found {page_results_count} results on page {current_page}")

                # Check if there's a next page
                next_page_link = soup.select_one('ul.pagination li.page-item a[rel=next]')
                if next_page_link:
                    current_page += 1
                else:
                    has_next_page = False

            print(f"Total results found: {len(results)}")
            return results

        except Exception as e:
            print(f"❌ HahoMoe search failed: {e}")
            return []

    def get_anime_details(self, url):
        """Get detailed information about an anime"""
        try:
            print(f"📝 Getting details for {url} from HahoMoe...")
            response = self.session.get(url, headers=self.headers)

            if response.status_code != 200:
                print(f"❌ Failed to get anime details: Status code {response.status_code}")
                return None

            soup = BeautifulSoup(response.text, 'html.parser')

            # Get anime ID from URL
            anime_id = url.split("/")[-1].split("?")[0]

            # Get poster image
            poster = soup.select_one('img.cover-image.img-thumbnail')
            poster_url = poster.get('src') if poster else "No poster available"

            # Get anime title
            title = soup.select_one('li.breadcrumb-item.active')
            title_text = title.text.strip() if title else "Unknown Title"

            # Get synopsis/description
            description = soup.select_one('div.card-body')
            description_text = description.text.strip() if description else "No description available"

            # Get additional info
            info_div = soup.select_one('div.anisc-info')
            info = {}
            if info_div:
                for item in info_div.select('div.item'):
                    label = item.select_one('span.item-head')
                    value = item.select_one('span.name') or item.select_one('div.text')
                    if label and value:
                        info[label.text.strip()] = value.text.strip()

            # Get genres
            genres = []
            genre_elements = soup.select('li.genre span.value, div.genre-tree ul > li > a')
            for genre_elem in genre_elements:
                genres.append(genre_elem.text.strip())

            return {
                'id': anime_id,
                'url': url,
                'title': f"{title_text} [HahoMoe]",
                'poster': poster_url,
                'description': description_text,
                'info': info,
                'genres': ", ".join(genres),
                'source': 'hahomoe'
            }

        except Exception as e:
            print(f"❌ Failed to get anime details from HahoMoe: {e}")
            return None

    def get_episodes(self, anime_details):
        """Get episode list for an anime"""
        if not anime_details or 'url' not in anime_details:
            print("❌ Invalid anime details. Cannot get episodes.")
            return []

        anime_url = anime_details['url']
        episodes = []

        try:
            print(f"🎬 Getting episodes for anime from HahoMoe...")

            # First, get the page content
            response = self.session.get(anime_url, headers=self.headers)

            if response.status_code != 200:
                print(f"❌ Failed to get anime page: Status code {response.status_code}")
                return []

            # Process the first page
            soup = BeautifulSoup(response.text, 'html.parser')
            has_more_pages = True
            current_page = 1

            while has_more_pages:
                # Get all episodes on current page
                ep_elements = soup.select('ul.episode-loop > li > a')

                for ep in ep_elements:
                    try:
                        ep_url = ep.get('href', '')
                        if ep_url and not ep_url.startswith(('http://', 'https://')):
                            ep_url = self.base_url + ep_url

                        # Extract episode number
                        ep_num_elem = ep.select_one('div.episode-number, div.episode-slug')
                        ep_num_str = ep_num_elem.text.strip() if ep_num_elem else "Episode"
                        ep_num = ep_num_str.replace("Episode ", "").strip()

                        # Extract episode title
                        ep_title_elem = ep.select_one('div.episode-label, div.episode-title')
                        ep_title = ep_title_elem.text.strip() if ep_title_elem else ""

                        if ep_title.lower() == "no title":
                            ep_title = ""

                        # Extract thumbnail if available
                        thumbnail = ""
                        if 'data-thumbnail' in ep.attrs:
                            thumbnail = ep.get('data-thumbnail')

                        # Extract date
                        date_elem = ep.select_one('div.date')
                        date = date_elem.text.strip() if date_elem else ""

                        # Format the episode title
                        full_title = f"Ep. {ep_num}"
                        if ep_title:
                            full_title += f": {ep_title}"

                        episodes.append({
                            'number': ep_num,
                            'title': full_title,
                            'url': ep_url,
                            'thumbnail': thumbnail,
                            'date': date,
                            'source': 'hahomoe'
                        })
                    except Exception as e:
                        print(f"Error processing an episode from HahoMoe: {e}")
                        continue

                # Check if there's a next page
                next_page_link = soup.select_one('ul.pagination li.page-item a[rel=next]')

                if next_page_link:
                    next_page_url = next_page_link.get('href')
                    if not next_page_url.startswith(('http://', 'https://')):
                        next_page_url = self.base_url + next_page_url

                    # Get the next page
                    current_page += 1
                    print(f"Loading episode page {current_page}...")

                    response = self.session.get(next_page_url, headers=self.headers)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                    else:
                        print(f"Failed to get next episode page: Status code {response.status_code}")
                        has_more_pages = False
                else:
                    has_more_pages = False

            # Sort episodes by number (descending)
            episodes.sort(key=lambda x: float(x['number']) if x['number'].replace('.', '', 1).isdigit() else 0, reverse=True)

            return episodes

        except Exception as e:
            print(f"❌ Failed to get episodes from HahoMoe: {e}")
            return []

    def get_video_sources(self, episode_url):
        """Get video sources for a specific episode"""
        try:
            print(f"🎥 Extracting video sources from HahoMoe episode...")

            # Get the episode page content
            response = self.session.get(episode_url, headers=self.headers)

            if response.status_code != 200:
                print(f"❌ Failed to get episode page: Status code {response.status_code}")
                return []

            # Parse the page to find the iframe
            soup = BeautifulSoup(response.text, 'html.parser')
            iframe = soup.select_one('iframe')

            if not iframe or not iframe.get('src'):
                print("❌ No iframe found on episode page")
                return []

            iframe_url = iframe.get('src')

            # Add referer header for the iframe request
            iframe_headers = self.headers.copy()
            iframe_headers['Referer'] = episode_url

            # Get the iframe content
            iframe_response = self.session.get(iframe_url, headers=iframe_headers)

            if iframe_response.status_code != 200:
                print(f"❌ Failed to get iframe content: Status code {iframe_response.status_code}")
                return []

            # Parse the iframe to find video sources
            iframe_soup = BeautifulSoup(iframe_response.text, 'html.parser')
            sources = iframe_soup.select('source')

            if not sources:
                print("❌ No video sources found in iframe")
                return []

            video_sources = []
            # Extract episode title from the URL to use in the file
            episode_info = episode_url.split('/')[-1].split('?')[0]

            # Store all available qualities
            available_qualities = {
                "1080p": None,
                "720p": None,
                "480p": None,
                "360p": None
            }

            # First pass to collect all available qualities
            for source in sources:
                src = source.get('src')
                title = source.get('title', 'Unknown')

                if src and title in available_qualities:
                    available_qualities[title] = src

            # Open urls.txt file to append the stream URLs
            with open('urls.txt', 'a') as url_file:
                url_file.write(f"\n==== HahoMoe: {episode_info} ====\n")

                # Add all available qualities to the video sources
                for quality, url in available_qualities.items():
                    if url:
                        video_sources.append({
                            'url': url,
                            'quality': quality,
                            'source': 'hahomoe'
                        })

                        # Write to the urls.txt file
                        url_file.write(f"{quality}: {url}\n")

                # Sort video sources by quality (highest first)
                video_sources.sort(key=lambda x: {
                    "1080p": 4,
                    "720p": 3, 
                    "480p": 2, 
                    "360p": 1
                }.get(x['quality'], 0), reverse=True)

                print(f"✅ Saved {len(video_sources)} stream URLs with all available qualities to urls.txt")

            return video_sources

        except Exception as e:
            print(f"❌ Failed to get video sources from HahoMoe: {e}")
            return []

    # === New methods for filtering and sorting ===

    def _get_search_parameters(self, filters=None):
        """Extract search parameters from filters, similar to HanimeScraper"""
        # Use active filters if no filters are provided
        if not filters:
            return (
                self.active_filters["included_tags"],
                self.active_filters["excluded_tags"],
                self.active_filters["order_by"],
                self.active_filters["ordering"]
            )

        # Otherwise process the provided filters
        included_tags = []
        excluded_tags = []
        order_by = self.active_filters["order_by"]
        ordering = self.active_filters["ordering"]

        # Process filter dict
        if isinstance(filters, dict):
            # Process tags
            if "included_tags" in filters:
                included_tags = filters["included_tags"]

            # Process excluded tags
            if "excluded_tags" in filters:
                excluded_tags = filters["excluded_tags"]

            # Process ordering
            if "order_by" in filters:
                order_by = filters["order_by"]

            if "ordering" in filters:
                ordering = filters["ordering"]

        return (included_tags, excluded_tags, order_by, ordering)

    def set_tag_filter(self, tag_name, state):
        """
        Set a tag filter with one of three states:
        - 1: include the tag
        - 0: neutral (default)
        - -1: exclude/blacklist the tag
        """
        # First remove the tag from both lists to avoid duplication
        if tag_name in self.active_filters["included_tags"]:
            self.active_filters["included_tags"].remove(tag_name)

        if tag_name in self.active_filters["excluded_tags"]:
            self.active_filters["excluded_tags"].remove(tag_name)

        # Then add it to the appropriate list based on state
        if state == 1:
            self.active_filters["included_tags"].append(tag_name)
        elif state == -1:
            self.active_filters["excluded_tags"].append(tag_name)

        print(f"Tag '{tag_name}' filter set to state: {state}")
        return True

    def set_sort_order(self, order_by, ascending=False):
        """Set sort order for results"""
        valid_options = {"vdy": "Views", "rel": "Release date", "srt": "Sort"}

        if order_by in valid_options:
            self.active_filters["order_by"] = order_by
            self.active_filters["ordering"] = "-a" if ascending else "-d"
            sort_description = valid_options.get(order_by, order_by)
            order_description = "ascending" if ascending else "descending"
            print(f"Sort order set to: {sort_description} ({order_description})")
            return True
        return False

    def clear_filters(self):
        """Reset all filters to default values"""
        self.active_filters = {
            "included_tags": [],
            "excluded_tags": [],
            "order_by": "vdy",
            "ordering": "-d"
        }
        print("All filters have been reset")
        return True

    def set_quality(self, quality):
        """Set preferred video quality"""
        if quality in self.quality_list:
            self.preferences["preferred_quality"] = quality
            print(f"Quality preference set to: {quality}")
            return True
        else:
            print(f"Invalid quality. Available options: {', '.join(self.quality_list)}")
            return False

    def get_popular_anime(self, page=1, max_pages=5):
        """Get popular anime (sorted by views)"""
        print(f"💫 Getting popular anime from HahoMoe starting from page {page}...")

        all_results = []

        try:
            # Use views descending for popular
            self.active_filters["order_by"] = "vdy"
            self.active_filters["ordering"] = "-d"

            current_page = page
            has_next_page = True

            while has_next_page and current_page < page + max_pages:
                # Popular anime URL
                url = f"{self.base_url}/anime?s=vdy-d&page={current_page}"

                print(f"Fetching popular anime page {current_page}...")
                response = self.session.get(url, headers=self.headers)

                if response.status_code != 200:
                    print(f"❌ Failed to get popular anime: Status code {response.status_code}")
                    break

                soup = BeautifulSoup(response.text, 'html.parser')
                anime_elements = soup.select('ul.anime-loop.loop > li > a')

                if not anime_elements:
                    print(f"No anime found on page {current_page}")
                    break

                page_results_count = 0
                for anime in anime_elements:
                    try:
                        title_elem = anime.select_one('div.label > span, div span.thumb-title')
                        title = title_elem.text.strip() if title_elem else "Unknown Title"
                        url = anime.get('href')
                        full_url = self.base_url + url if not url.startswith('http') else url

                        # Get the poster image
                        poster_elem = anime.select_one('img')
                        poster = poster_elem.get('src') if poster_elem else "No poster available"

                        # Try to get type and year if available
                        additional_info = anime.select_one('div.fd-infor')
                        anime_type = "Unknown"
                        year = "Unknown"

                        if additional_info:
                            type_elem = additional_info.select_one('.fdi-item:nth-child(1)')
                            year_elem = additional_info.select_one('.fdi-item:nth-child(2)')

                            if type_elem:
                                anime_type = type_elem.text.strip()
                            if year_elem:
                                year = year_elem.text.strip()

                        all_results.append({
                            'id': url.split('/')[-1],
                            'title': f"{title} [HahoMoe]",
                            'url': full_url + "?s=srt-d",
                            'poster': poster,
                            'type': anime_type,
                            'year': year,
                            'source': 'hahomoe'
                        })
                        page_results_count += 1
                    except Exception as e:
                        print(f"Error processing popular anime result: {e}")
                        continue

                print(f"Found {page_results_count} popular anime on page {current_page}")

                # Check if there's a next page
                next_page_link = soup.select_one('ul.pagination li.page-item a[rel=next]')
                if next_page_link:
                    current_page += 1
                else:
                    has_next_page = False

            print(f"Total popular anime found: {len(all_results)}")
            return all_results

        except Exception as e:
            print(f"❌ Error getting popular anime from HahoMoe: {e}")
            return []

    def get_latest_anime(self, page=1, max_pages=5):
        """Get latest anime (sorted by release date)"""
        print(f"🆕 Getting latest anime from HahoMoe starting from page {page}...")

        all_results = []

        try:
            current_page = page
            has_next_page = True

            while has_next_page and current_page < page + max_pages:
                # Latest anime URL (sorted by release date)
                url = f"{self.base_url}/anime?s=rel-d&page={current_page}"

                print(f"Fetching latest anime page {current_page}...")
                response = self.session.get(url, headers=self.headers)

                if response.status_code != 200:
                    print(f"❌ Failed to get latest anime: Status code {response.status_code}")
                    break

                soup = BeautifulSoup(response.text, 'html.parser')
                anime_elements = soup.select('ul.anime-loop.loop > li > a')

                if not anime_elements:
                    print(f"No anime found on page {current_page}")
                    break

                page_results_count = 0
                for anime in anime_elements:
                    try:
                        title_elem = anime.select_one('div.label > span, div span.thumb-title')
                        title = title_elem.text.strip() if title_elem else "Unknown Title"
                        url = anime.get('href')
                        full_url = self.base_url + url if not url.startswith('http') else url

                        # Get the poster image
                        poster_elem = anime.select_one('img')
                        poster = poster_elem.get('src') if poster_elem else "No poster available"

                        # Try to get type and year if available
                        additional_info = anime.select_one('div.fd-infor')
                        anime_type = "Unknown"
                        year = "Unknown"

                        if additional_info:
                            type_elem = additional_info.select_one('.fdi-item:nth-child(1)')
                            year_elem = additional_info.select_one('.fdi-item:nth-child(2)')

                            if type_elem:
                                anime_type = type_elem.text.strip()
                            if year_elem:
                                year = year_elem.text.strip()

                        all_results.append({
                            'id': url.split('/')[-1],
                            'title': f"{title} [HahoMoe]",
                            'url': full_url + "?s=srt-d",
                            'poster': poster,
                            'type': anime_type,
                            'year': year,
                            'source': 'hahomoe'
                        })
                        page_results_count += 1
                    except Exception as e:
                        print(f"Error processing latest anime result: {e}")
                        continue

                print(f"Found {page_results_count} latest anime on page {current_page}")

                # Check if there's a next page
                next_page_link = soup.select_one('ul.pagination li.page-item a[rel=next]')
                if next_page_link:
                    current_page += 1
                else:
                    has_next_page = False

            print(f"Total latest anime found: {len(all_results)}")
            return all_results

        except Exception as e:
            print(f"❌ Error getting latest anime from HahoMoe: {e}")
            return []

    def get_tags(self):
        """Get available tags/genres from HahoMoe"""
        # Note: Would need to be implemented by scraping the site
        # This is a simplified placeholder version
        return [
            {"id": "action", "name": "Action"},
            {"id": "adventure", "name": "Adventure"},
            {"id": "comedy", "name": "Comedy"},
            {"id": "drama", "name": "Drama"},
            {"id": "ecchi", "name": "Ecchi"},
            {"id": "fantasy", "name": "Fantasy"},
            {"id": "horror", "name": "Horror"},
            {"id": "magic", "name": "Magic"},
            {"id": "mystery", "name": "Mystery"},
            {"id": "psychological", "name": "Psychological"},
            {"id": "romance", "name": "Romance"},
            {"id": "sci-fi", "name": "Sci-Fi"},
            {"id": "slice-of-life", "name": "Slice of Life"},
            {"id": "supernatural", "name": "Supernatural"},
            {"id": "thriller", "name": "Thriller"}
        ]

    def get_sortable_list(self):
        """Get sortable options"""
        return [
            ("Views", "vdy"),
            ("Release Date", "rel"),
            ("Sort", "srt")
        ]