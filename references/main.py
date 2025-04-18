
import requests
from bs4 import BeautifulSoup
import cloudscraper
import sys
import time

class HiAnimeSearcher:
    def __init__(self):
        self.base_url = "https://hianimez.to"
        self.search_url = f"{self.base_url}/search"
        self.scraper = cloudscraper.create_scraper()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }

    def search_anime(self, query):
        """Search for anime on HiAnime by title"""
        try:
            print(f"🔍 Searching for '{query}' on HiAnime...")
            
            params = {
                'keyword': query
            }
            
            response = self.scraper.get(self.search_url, params=params, headers=self.headers)
            
            if response.status_code != 200:
                print(f"❌ Search failed with status code: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            search_results = soup.select('div.film_list-wrap div.flw-item')
            
            if not search_results:
                print("No results found. Try a different search term.")
                return []
            
            results = []
            for result in search_results:
                try:
                    title_elem = result.select_one('div.film-detail h3.film-name a')
                    title = title_elem.text.strip()
                    url = title_elem['href']
                    full_url = self.base_url + url if not url.startswith('http') else url
                    
                    # Get the poster image
                    poster_elem = result.select_one('div.film-poster img')
                    poster = poster_elem['data-src'] if poster_elem and 'data-src' in poster_elem.attrs else "No poster available"
                    
                    # Get additional info: type (TV, Movie, etc) and year if available
                    additional_info = result.select_one('div.fd-infor')
                    anime_type = additional_info.select_one('.fdi-item:nth-child(1)').text.strip() if additional_info and additional_info.select_one('.fdi-item:nth-child(1)') else "Unknown"
                    year = additional_info.select_one('.fdi-item:nth-child(2)').text.strip() if additional_info and additional_info.select_one('.fdi-item:nth-child(2)') else "Unknown"
                    
                    results.append({
                        'title': title,
                        'url': full_url,
                        'poster': poster,
                        'type': anime_type,
                        'year': year
                    })
                except Exception as e:
                    print(f"Error processing a result: {e}")
                    continue
            
            return results
            
        except Exception as e:
            print(f"❌ Search failed: {e}")
            return []
            
    def get_anime_details(self, url):
        """Get detailed information about an anime"""
        try:
            print(f"📝 Getting details for {url}...")
            response = self.scraper.get(url, headers=self.headers)
            
            if response.status_code != 200:
                print(f"❌ Failed to get anime details: Status code {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Get the anime ID for episode list
            anime_id = url.split("-")[-1]
            
            # Get poster image
            poster = soup.select_one('div.anisc-poster img')
            poster_url = poster['src'] if poster else "No poster available"
            
            # Get anime title
            title = soup.select_one('h2.film-name')
            title_text = title.text.strip() if title else "Unknown Title"
            
            # Get synopsis/description
            description = soup.select_one('div.film-description div.text')
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
            
            return {
                'id': anime_id,
                'url': url,
                'title': title_text,
                'poster': poster_url,
                'description': description_text,
                'info': info
            }
            
        except Exception as e:
            print(f"❌ Failed to get anime details: {e}")
            return None
    
    def get_episodes(self, anime_details):
        """Get episode list for an anime using its ID"""
        if not anime_details or 'id' not in anime_details:
            print("❌ Invalid anime details. Cannot get episodes.")
            return []
        
        anime_id = anime_details['id']
        referer = anime_details['url']
        
        try:
            print(f"🎬 Getting episodes for anime ID: {anime_id}...")
            
            # Prepare headers with referer
            ajax_headers = self.headers.copy()
            ajax_headers['Accept'] = '*/*'
            ajax_headers['Referer'] = referer
            ajax_headers['X-Requested-With'] = 'XMLHttpRequest'
            
            # Get the episode list using the AJAX endpoint (similar to Aniyomi extension)
            episode_list_url = f"{self.base_url}/ajax/v2/episode/list/{anime_id}"
            ep_response = self.scraper.get(episode_list_url, headers=ajax_headers)
            
            if ep_response.status_code != 200:
                print(f"❌ Failed to get episode list: Status code {ep_response.status_code}")
                return []
            
            # Parse the HTML contained in the JSON response
            ep_data = ep_response.json()
            if 'html' not in ep_data:
                print("❌ Invalid episode list response format")
                return []
            
            # Parse the episode list HTML
            ep_soup = BeautifulSoup(ep_data['html'], 'html.parser')
            ep_items = ep_soup.select('a.ep-item')
            
            episodes = []
            for ep in ep_items:
                try:
                    ep_num = ep.get('data-number', '?')
                    ep_title = ep.get('title', f'Episode {ep_num}')
                    ep_url = ep.get('href', '')
                    
                    if ep_url and not ep_url.startswith(('http://', 'https://')):
                        ep_url = self.base_url + ep_url
                    
                    # Extract episode ID
                    episode_id = ep_url.split("?ep=")[-1] if "?ep=" in ep_url else None
                    
                    episode_data = {
                        'number': ep_num,
                        'title': f"Ep. {ep_num}: {ep_title}",
                        'url': ep_url,
                        'id': episode_id
                    }
                    
                    # Get thumbnail if available
                    if 'data-thumbnail' in ep.attrs:
                        episode_data['thumbnail'] = ep.get('data-thumbnail')
                    
                    episodes.append(episode_data)
                except Exception as e:
                    print(f"Error processing an episode: {e}")
                    continue
            
            # If we have episodes, get the streaming sources
            episodes_with_sources = []
            for episode in episodes[::-1]:  # Reverse to have newest first
                if 'id' in episode and episode['id']:
                    # Get servers for this episode
                    servers = self.get_servers(episode['id'], referer)
                    
                    if servers:
                        # Add server info to episodes
                        episode['servers'] = servers
                        
                        # Get streaming sources for HD servers
                        streaming_links = []
                        for server in servers:
                            if server['name'] in ['HD-1', 'HD-2', 'StreamTape']:
                                # Add server type to the data
                                streaming_links.append({
                                    'name': server['name'],
                                    'type': server['category'],
                                    'id': server['id']
                                })
                        
                        if streaming_links:
                            episode['streaming_links'] = streaming_links
                
                episodes_with_sources.append(episode)
            
            return episodes_with_sources
            
        except Exception as e:
            print(f"❌ Failed to get episodes: {e}")
            return []
            
    def get_servers(self, episode_id, referer):
        """Get servers for a specific episode"""
        try:
            # Prepare headers with referer
            ajax_headers = self.headers.copy()
            ajax_headers['Accept'] = '*/*'
            ajax_headers['Referer'] = referer
            ajax_headers['X-Requested-With'] = 'XMLHttpRequest'
            
            # Get the server list using the AJAX endpoint (similar to Aniyomi extension)
            servers_url = f"{self.base_url}/ajax/v2/episode/servers?episodeId={episode_id}"
            servers_response = self.scraper.get(servers_url, headers=ajax_headers)
            
            if servers_response.status_code != 200:
                print(f"❌ Failed to get servers: Status code {servers_response.status_code}")
                return []
            
            # Parse the HTML contained in the JSON response
            servers_data = servers_response.json()
            if 'html' not in servers_data:
                print("❌ Invalid servers response format")
                return []
            
            # Parse the servers HTML
            servers_soup = BeautifulSoup(servers_data['html'], 'html.parser')
            
            servers = []
            
            # Process each server type (sub, dub, mixed, raw) as in the Aniyomi extension
            for server_type in ['servers-sub', 'servers-dub', 'servers-mixed', 'servers-raw']:
                server_items = servers_soup.select(f'div.{server_type} div.item')
                
                for server in server_items:
                    try:
                        server_id = server.get('data-id')
                        server_name = server.text.strip()
                        server_type_value = server.get('data-type')
                        
                        servers.append({
                            'id': server_id,
                            'name': server_name,
                            'type': server_type_value,
                            'category': server_type.replace('servers-', '')
                        })
                    except Exception as e:
                        print(f"Error processing a server: {e}")
                        continue
            
            return servers
            
        except Exception as e:
            print(f"❌ Failed to get servers: {e}")
            return []
    
    def get_source_url(self, server_id, referer):
        """Get the source URL for a server"""
        try:
            # Prepare headers with referer
            ajax_headers = self.headers.copy()
            ajax_headers['Accept'] = '*/*'
            ajax_headers['Referer'] = referer
            ajax_headers['X-Requested-With'] = 'XMLHttpRequest'
            
            # Get the source URL using the AJAX endpoint
            source_url = f"{self.base_url}/ajax/v2/episode/sources?id={server_id}"
            source_response = self.scraper.get(source_url, headers=ajax_headers)
            
            if source_response.status_code != 200:
                print(f"❌ Failed to get source URL: Status code {source_response.status_code}")
                return None
            
            # Parse the JSON response
            source_data = source_response.json()
            if 'link' not in source_data:
                print("❌ Invalid source response format")
                return None
            
            return source_data['link']
            
        except Exception as e:
            print(f"❌ Failed to get source URL: {e}")
            return None

    def display_results(self, results):
        """Display the search results in a user-friendly format"""
        if not results:
            return
        
        print(f"\n{'=' * 50}")
        print(f"Found {len(results)} results:")
        print(f"{'=' * 50}")
        
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['title']}")
            print(f"   Type: {result['type']} | Year: {result['year']}")
            print(f"   URL: {result['url']}")
            if 'poster' in result and result['poster'] != "No poster available":
                print(f"   Poster: {result['poster']}")
            print(f"{'=' * 50}")
    
    def display_anime_details(self, anime_details):
        """Display detailed information about an anime"""
        if not anime_details:
            return
        
        print(f"\n{'=' * 50}")
        print(f"Anime Details: {anime_details.get('title', 'Unknown Title')}")
        print(f"{'=' * 50}")
        
        # Display poster
        if 'poster' in anime_details and anime_details['poster'] != "No poster available":
            print(f"Poster URL: {anime_details['poster']}")
        
        # Display description
        if 'description' in anime_details:
            print(f"\nDescription:")
            print(f"{anime_details['description'][:300]}...")  # Show first 300 chars
        
        # Display additional info
        if 'info' in anime_details and anime_details['info']:
            print("\nAdditional Information:")
            for key, value in anime_details['info'].items():
                print(f"   {key} {value}")
        
        print(f"{'=' * 50}")

    def display_episodes(self, episodes, limit=20):
        """Display episode list with thumbnails and streaming options"""
        if not episodes:
            return
        
        print(f"\n{'=' * 50}")
        print(f"Found {len(episodes)} episodes:")
        print(f"{'=' * 50}")
        
        for i, episode in enumerate(episodes[:limit], 1):
            print(f"{i}. {episode['title']}")
            
            # Show thumbnail if available
            if 'thumbnail' in episode and episode['thumbnail']:
                print(f"   Thumbnail: {episode['thumbnail']}")
            
            # Show available streaming options
            if 'streaming_links' in episode and episode['streaming_links']:
                print(f"   Available Streams:")
                for stream in episode['streaming_links']:
                    print(f"   → {stream['name']} ({stream['type'].upper()})")
        
        if len(episodes) > limit:
            print(f"... and {len(episodes) - limit} more episodes")
        
        print(f"{'=' * 50}")
        
        # Display available audio types
        if episodes and 'servers' in episodes[0]:
            print("Available Audio Types:")
            for server_type in ['sub', 'dub', 'mixed', 'raw']:
                if any(server['category'] == server_type for server in episodes[0].get('servers', [])):
                    print(f"✓ {server_type.upper()} available")
        
        print(f"{'=' * 50}")

def main_menu():
    """Display the main menu and handle user interaction"""
    searcher = HiAnimeSearcher()
    
    print("""
        ####################################
        ##   HiAnime Search Tool          ##
        ##   (Educational Purposes Only)  ##
        ####################################
        """)
    
    while True:
        print("\nWhat would you like to do?")
        print("1. Search for anime")
        print("2. Exit")
        
        try:
            choice = input("\nEnter your choice (1-2): ")
            
            if choice == '1':
                query = input("\nEnter anime title to search: ")
                if not query.strip():
                    print("Please enter a valid search term.")
                    continue
                
                results = searcher.search_anime(query)
                searcher.display_results(results)
                
                if results:
                    anime_choice = input("\nEnter the number of the anime to view details (or 0 to return): ")
                    if anime_choice.isdigit() and 1 <= int(anime_choice) <= len(results):
                        selected_anime = results[int(anime_choice) - 1]
                        anime_details = searcher.get_anime_details(selected_anime['url'])
                        
                        if anime_details:
                            # Display anime details with poster
                            searcher.display_anime_details(anime_details)
                            
                            print(f"\nFetching episodes for {selected_anime['title']}...")
                            episodes = searcher.get_episodes(anime_details)
                            
                            if episodes:
                                # Display episodes with thumbnails and streaming options
                                searcher.display_episodes(episodes)
                                
                                # Allow viewing streaming links for a specific episode
                                ep_choice = input("\nEnter episode number to view streaming links (or 0 to return): ")
                                if ep_choice.isdigit() and 1 <= int(ep_choice) <= min(20, len(episodes)):
                                    selected_episode = episodes[int(ep_choice) - 1]
                                    
                                    if 'streaming_links' in selected_episode and selected_episode['streaming_links']:
                                        print(f"\n{'=' * 50}")
                                        print(f"Streaming links for {selected_episode['title']}:")
                                        print(f"{'=' * 50}")
                                        
                                        for i, stream in enumerate(selected_episode['streaming_links'], 1):
                                            print(f"{i}. {stream['name']} ({stream['type'].upper()})")
                                            
                                            # Get the actual source URL
                                            source_url = searcher.get_source_url(stream['id'], anime_details['url'])
                                            if source_url:
                                                print(f"   URL: {source_url}")
                                        
                                        print(f"{'=' * 50}")
                                    else:
                                        print("No streaming links available for this episode.")
                            else:
                                print("No episodes found for this anime.")
                        else:
                            print("Failed to get anime details.")
                
            elif choice == '2':
                print("\nThank you for using HiAnime Search Tool. Goodbye!")
                sys.exit(0)
                
            else:
                print("Invalid choice. Please enter 1 or 2.")
                
        except KeyboardInterrupt:
            print("\n\nExiting program. Goodbye!")
            sys.exit(0)
            
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    main_menu()
