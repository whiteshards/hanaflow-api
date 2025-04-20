
import requests
from bs4 import BeautifulSoup
import sys
import time
import urllib.parse

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

    def search_anime(self, query):
        """Search for anime on HahoMoe by title"""
        try:
            print(f"🔍 Searching for '{query}' on HahoMoe...")
            
            # Encode the query for the URL
            encoded_query = urllib.parse.quote(query)
            
            # Create the search URL with params
            url = f"{self.search_url}?page=1&s=vdy-d&q={encoded_query}"
            
            response = self.session.get(url, headers=self.headers)
            
            if response.status_code != 200:
                print(f"❌ Search failed with status code: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            search_results = soup.select('ul.anime-loop.loop > li > a')
            
            if not search_results:
                print("No results found on HahoMoe. Try a different search term.")
                return []
            
            results = []
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
                    
                    # Add source identifier to differentiate from HiAnime results
                    results.append({
                        'title': f"{title} [HahoMoe]",
                        'url': full_url + "?s=srt-d",  # Add sort parameter
                        'poster': poster,
                        'type': anime_type,
                        'year': year,
                        'source': 'hahomoe'
                    })
                except Exception as e:
                    print(f"Error processing a HahoMoe result: {e}")
                    continue
            
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
                        #url_file.write(f"{quality}: {url}\n")
                
                # Sort video sources by quality (highest first)
                video_sources.sort(key=lambda x: {
                    "1080p": 4,
                    "720p": 3, 
                    "480p": 2, 
                    "360p": 1
                }.get(x['quality'], 0), reverse=True)
                
                #print(f"✅ Saved {len(video_sources)} stream URLs with all available qualities to urls.txt")
            
            return video_sources
            
        except Exception as e:
            print(f"❌ Failed to get video sources from HahoMoe: {e}")
            return []
