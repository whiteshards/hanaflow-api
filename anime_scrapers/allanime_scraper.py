from click import pass_obj
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
        self.json = json

    def bytes_into_human_readable(self, bytes_val: int) -> str:
        """Convert bytes to human readable format like Kotlin implementation"""
        kilobyte = 1000
        megabyte = kilobyte * 1000
        gigabyte = megabyte * 1000
        terabyte = gigabyte * 1000
        
        if 0 <= bytes_val < kilobyte:
            return f"{bytes_val} b/s"
        elif kilobyte <= bytes_val < megabyte:
            return f"{bytes_val // kilobyte} kb/s"
        elif megabyte <= bytes_val < gigabyte:
            return f"{bytes_val // megabyte} mb/s"
        elif gigabyte <= bytes_val < terabyte:
            return f"{bytes_val // gigabyte} gb/s"
        elif bytes_val >= terabyte:
            return f"{bytes_val // terabyte} tb/s"
        else:
            return f"{bytes_val} bits/s"

    def videoFromUrl(self, url: str, name: str) -> List[Dict[str, Any]]:
        """Implementation based on AllAnimeExtractor.kt"""
        print(f"📌 AllAnimeExtractor.videoFromUrl: {url}, Name: {name}")
        video_list = []
        
        try:
            # Get the endpoint from getVersion
            endpoint_response = self.session.get(f"{self.site_url}/getVersion")
            if endpoint_response.status_code != 200:
                print(f"❌ Failed to get version endpoint: {endpoint_response.status_code}")
                with open("error.txt", "a") as f:
                    f.write(f"\nFailed to get version endpoint: {endpoint_response.status_code}")
                    f.write(f"\nResponse: {endpoint_response.text}")
                return []
                
            endpoint_data = endpoint_response.json()
            episode_iframe_head = endpoint_data.get('episodeIframeHead')
            
            if not episode_iframe_head:
                print("❌ No episodeIframeHead found in version response")
                with open("error.txt", "a") as f:
                    f.write("\nNo episodeIframeHead found in version response")
                    f.write(f"\nResponse: {endpoint_response.text}")
                return []
            
            # Replace /clock? with /clock.json? as in Kotlin code
            modified_url = url.replace("/clock?", "/clock.json?")
            
            # Get video link data
            resp = self.session.get(f"{episode_iframe_head}{modified_url}")
            if resp.status_code != 200:
                print(f"❌ Failed to get video data: {resp.status_code}")
                with open("error.txt", "a") as f:
                    f.write(f"\nFailed to get video data: {resp.status_code}")
                    f.write(f"\nURL: {episode_iframe_head}{modified_url}")
                    f.write(f"\nResponse: {resp.text}")
                return []
            
            # Parse the video link JSON
            try:
                link_json = resp.json()
                links = link_json.get('links', [])
            except json.JSONDecodeError:
                print("❌ Invalid JSON response for video links")
                with open("error.txt", "a") as f:
                    f.write("\nInvalid JSON response for video links")
                    f.write(f"\nResponse: {resp.text}")
                return []
            
            # Process each link as in the Kotlin implementation
            for link in links:
                subtitles = []
                # Process subtitles
                if link.get('subtitles'):
                    for sub in link['subtitles']:
                        label = f" - {sub.get('label')}" if sub.get('label') else ""
                        lang = sub.get('lang', 'unknown')
                        subtitles.append({
                            'url': sub.get('src', ''),
                            'language': f"{lang}{label}"
                        })
                
                # MP4 links
                if link.get('mp4') is True:
                    video_list.append({
                        'url': link.get('link', ''),
                        'quality': f"Original ({name} - {link.get('resolutionStr', '')})",
                        'headers': dict(self.headers),
                        'subtitles': subtitles
                    })
                
                # HLS links
                elif link.get('hls') is True:
                    try:
                        # Create headers for master playlist request
                        master_headers = dict(self.headers)
                        master_headers['Accept'] = '*/*'
                        master_headers['Host'] = urllib.parse.urlparse(link.get('link', '')).netloc
                        master_headers['Origin'] = episode_iframe_head
                        master_headers['Referer'] = f"{episode_iframe_head}/"
                        
                        hls_response = self.session.get(link.get('link', ''), headers=master_headers)
                        
                        if hls_response.status_code == 200:
                            master_playlist = hls_response.text
                            
                            # Process audio tracks
                            audio_list = []
                            if "#EXT-X-MEDIA:TYPE=AUDIO" in master_playlist:
                                audio_info = master_playlist.split("#EXT-X-MEDIA:TYPE=AUDIO", 1)[1].split("\n", 1)[0]
                                language = audio_info.split('NAME="', 1)[1].split('"', 1)[0] if 'NAME="' in audio_info else "Unknown"
                                url = audio_info.split('URI="', 1)[1].split('"', 1)[0] if 'URI="' in audio_info else ""
                                if url:
                                    audio_list.append({
                                        'url': url,
                                        'language': language
                                    })
                            
                            # If no streams defined, just use the main link
                            if "#EXT-X-STREAM-INF:" not in master_playlist:
                                video_list.append({
                                    'url': link.get('link', ''),
                                    'quality': f"{name} - {link.get('resolutionStr', '')}",
                                    'headers': master_headers,
                                    'subtitles': subtitles,
                                    'audio_tracks': audio_list
                                })
                                continue
                            
                            # Process streams
                            stream_sections = master_playlist.split("#EXT-X-STREAM-INF:")[1:]
                            for section in stream_sections:
                                bandwidth = ""
                                if "AVERAGE-BANDWIDTH=" in section:
                                    bandwidth_val = int(section.split("AVERAGE-BANDWIDTH=")[1].split(",")[0])
                                    bandwidth = f" {self.bytes_into_human_readable(bandwidth_val)}"
                                
                                resolution = "Unknown"
                                if "RESOLUTION=" in section:
                                    resolution = section.split("RESOLUTION=")[1].split("x")[1].split(",")[0] + "p"
                                
                                quality = f"{resolution}{bandwidth} ({name} - {link.get('resolutionStr', '')})"
                                video_url = section.split("\n")[1].split("\n")[0]
                                
                                # Fix relative URLs
                                if not video_url.startswith("http"):
                                    base_url = "/".join(hls_response.url.split("/")[:-1])
                                    video_url = f"{base_url}/{video_url}"
                                
                                # Create playlist headers
                                pl_headers = dict(self.headers)
                                pl_headers['Accept'] = '*/*'
                                pl_headers['Host'] = urllib.parse.urlparse(video_url).netloc
                                pl_headers['Origin'] = episode_iframe_head
                                pl_headers['Referer'] = f"{episode_iframe_head}/"
                                
                                video_list.append({
                                    'url': video_url,
                                    'quality': quality,
                                    'headers': pl_headers,
                                    'subtitles': subtitles,
                                    'audio_tracks': audio_list
                                })
                    except Exception as e:
                        print(f"❌ Error processing HLS stream: {e}")
                        with open("error.txt", "a") as f:
                            f.write(f"\nError processing HLS stream: {e}")
                
                # Crunchyroll iframe
                elif link.get('crIframe') is True and link.get('portData') and link['portData'].get('streams'):
                    for stream in link['portData']['streams']:
                        if stream.get('format') == 'adaptive_dash':
                            hardsub_info = f" - Hardsub: {stream.get('hardsub_lang')}" if stream.get('hardsub_lang') else ""
                            video_list.append({
                                'url': stream.get('url', ''),
                                'quality': f"Original (AC - Dash{hardsub_info})",
                                'headers': dict(self.headers),
                                'subtitles': subtitles
                            })
                        elif stream.get('format') == 'adaptive_hls':
                            try:
                                hls_response = self.session.get(
                                    stream.get('url', ''), 
                                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:101.0) Gecko/20100101 Firefox/101.0'}
                                )
                                
                                if hls_response.status_code == 200:
                                    master_playlist = hls_response.text
                                    if "#EXT-X-STREAM-INF:" in master_playlist:
                                        stream_sections = master_playlist.split("#EXT-X-STREAM-INF:")[1:]
                                        for section in stream_sections:
                                            resolution = "Unknown"
                                            if "RESOLUTION=" in section:
                                                resolution = section.split("RESOLUTION=")[1].split("x")[1].split(",")[0] + "p"
                                            
                                            hardsub_info = f" - Hardsub: {stream.get('hardsub_lang')}" if stream.get('hardsub_lang') else ""
                                            quality = f"{resolution} (AC - HLS{hardsub_info})"
                                            video_url = section.split("\n")[1].split("\n")[0]
                                            
                                            video_list.append({
                                                'url': video_url,
                                                'quality': quality,
                                                'headers': dict(self.headers),
                                                'subtitles': subtitles
                                            })
                            except Exception as e:
                                print(f"❌ Error processing CR HLS stream: {e}")
                                with open("error.txt", "a") as f:
                                    f.write(f"\nError processing CR HLS stream: {e}")
                
                # DASH links
                elif link.get('dash') is True and link.get('rawUrls'):
                    audio_tracks = []
                    if link['rawUrls'].get('audios'):
                        for audio in link['rawUrls']['audios']:
                            audio_tracks.append({
                                'url': audio.get('url', ''),
                                'language': self.bytes_into_human_readable(audio.get('bandwidth', 0))
                            })
                    
                    if link['rawUrls'].get('vids'):
                        for vid in link['rawUrls']['vids']:
                            video_list.append({
                                'url': vid.get('url', ''),
                                'quality': f"{name} - {vid.get('height', 'Unknown')} {self.bytes_into_human_readable(vid.get('bandwidth', 0))}",
                                'headers': dict(self.headers),
                                'subtitles': subtitles,
                                'audio_tracks': audio_tracks
                            })
            
            return video_list
        except Exception as e:
            import traceback
            print(f"❌ AllAnimeExtractor error: {e}")
            with open("error.txt", "a") as f:
                f.write(f"\nAllAnimeExtractor error: {e}")
                f.write(f"\n{traceback.format_exc()}")
            return []

class GogoStreamExtractor(BaseExtractor):
    def videosFromUrl(self, serverUrl: str) -> List[Dict[str, Any]]:
        print(f"🔍 GogoStreamExtractor.videosFromUrl: {serverUrl}")
        try:
            # Basic implementation based on the Kotlin code
            with open('error.txt', 'a', encoding='utf-8') as f:
                f.write(f"\nAttempting GogoStreamExtractor: {serverUrl}\n")
            
            response = self.session.get(serverUrl)
            response.raise_for_status()
            
            # Log details about what we're processing
            with open('error.txt', 'a', encoding='utf-8') as f:
                f.write(f"Got response {response.status_code}\n")
                
            # For now, return a basic video entry - would need crypto functions for complete implementation
            return [{
                'url': serverUrl,
                'quality': 'Vidstreaming (Direct)',
                'headers': dict(self.headers)
            }]
            
        except Exception as e:
            import traceback
            print(f"❌ Error in GogoStreamExtractor: {e}")
            with open('error.txt', 'a', encoding='utf-8') as f:
                f.write(f"Error in GogoStreamExtractor: {e}\n")
                f.write(traceback.format_exc())
            return []

class DoodExtractor(BaseExtractor):
    def videosFromUrl(self, url: str, quality: str = None, redirect: bool = True) -> List[Dict[str, Any]]:
        print(f"🔍 DoodExtractor.videosFromUrl: {url}")
        try:
            with open('error.txt', 'a', encoding='utf-8') as f:
                f.write(f"\nAttempting DoodExtractor: {url}\n")
                
            response = self.session.get(url)
            response.raise_for_status()
            
            # Basic implementation to get visible URL
            video_url = None
            if '/pass_md5/' in response.text:
                with open('error.txt', 'a', encoding='utf-8') as f:
                    f.write(f"Found /pass_md5/ in response\n")
                # For now return a placeholder - would need to implement token generation
                return [{
                    'url': url,
                    'quality': 'Doodstream',
                    'headers': dict(self.headers)
                }]
            else:
                with open('error.txt', 'a', encoding='utf-8') as f:
                    f.write(f"No /pass_md5/ found in response\n")
            
            return []
            
        except Exception as e:
            import traceback
            print(f"❌ Error in DoodExtractor: {e}")
            with open('error.txt', 'a', encoding='utf-8') as f:
                f.write(f"Error in DoodExtractor: {e}\n")
                f.write(traceback.format_exc())
            return []

class OkruExtractor(BaseExtractor):
    def videosFromUrl(self, url: str, prefix: str = "", fixQualities: bool = True) -> List[Dict[str, Any]]:
        print(f"🔍 OkruExtractor.videosFromUrl: {url}")
        try:
            with open('error.txt', 'a', encoding='utf-8') as f:
                f.write(f"\nAttempting OkruExtractor: {url}\n")
                
            response = self.session.get(url)
            response.raise_for_status()
            
            # Find the data-options attribute in div element
            import re
            data_options_match = re.search(r'data-options="([^"]+)"', response.text)
            
            if data_options_match:
                data_options = data_options_match.group(1)
                with open('error.txt', 'a', encoding='utf-8') as f:
                    f.write(f"Found data-options: {data_options[:100]}...\n")
                
                # Basic implementation - would need to properly extract video URLs
                return [{
                    'url': url, 
                    'quality': f'Okru - Original',
                    'headers': dict(self.headers)
                }]
            else:
                with open('error.txt', 'a', encoding='utf-8') as f:
                    f.write(f"No data-options found\n")
            
            return []
            
        except Exception as e:
            import traceback
            print(f"❌ Error in OkruExtractor: {e}")
            with open('error.txt', 'a', encoding='utf-8') as f:
                f.write(f"Error in OkruExtractor: {e}\n")
                f.write(traceback.format_exc())
            return []

class Mp4uploadExtractor(BaseExtractor):
     def videosFromUrl(self, url: str, headers: Dict[str, str]) -> List[Dict[str, Any]]:
         print(f"🔍 Mp4uploadExtractor.videosFromUrl: {url}")
         try:
             with open('error.txt', 'a', encoding='utf-8') as f:
                 f.write(f"\nAttempting Mp4uploadExtractor: {url}\n")
                 
             # For now just return a placeholder
             return [{
                 'url': url,
                 'quality': 'Mp4upload',
                 'headers': headers
             }]
             
         except Exception as e:
             import traceback
             print(f"❌ Error in Mp4uploadExtractor: {e}")
             with open('error.txt', 'a', encoding='utf-8') as f:
                 f.write(f"Error in Mp4uploadExtractor: {e}\n")
                 f.write(traceback.format_exc())
             return []

class StreamlareExtractor(BaseExtractor):
    def videosFromUrl(self, url: str, prefix: str = "", suffix: str = "") -> List[Dict[str, Any]]:
        print(f"🔍 StreamlareExtractor.videosFromUrl: {url}")
        try:
            with open('error.txt', 'a', encoding='utf-8') as f:
                f.write(f"\nAttempting StreamlareExtractor: {url}\n")
            
            # Extract ID from URL
            video_id = url.split('/')[-1]
            
            # POST request to API
            api_url = "https://slwatch.co/api/video/stream/get"
            data = {"id": video_id}
            
            with open('error.txt', 'a', encoding='utf-8') as f:
                f.write(f"Sending POST to {api_url} with data: {data}\n")
                
            response = self.session.post(api_url, json=data)
            response.raise_for_status()
            
            # Basic implementation
            return [{
                'url': url,
                'quality': f'Streamlare{": " + prefix if prefix else ""}',
                'headers': dict(self.headers)
            }]
            
        except Exception as e:
            import traceback
            print(f"❌ Error in StreamlareExtractor: {e}")
            with open('error.txt', 'a', encoding='utf-8') as f:
                f.write(f"Error in StreamlareExtractor: {e}\n")
                f.write(traceback.format_exc())
            return []

class FilemoonExtractor(BaseExtractor):
    def videosFromUrl(self, url: str, prefix: str = "") -> List[Dict[str, Any]]:
        print(f"🔍 FilemoonExtractor.videosFromUrl: {url}")
        try:
            with open('error.txt', 'a', encoding='utf-8') as f:
                f.write(f"\nAttempting FilemoonExtractor: {url}\n")
                
            response = self.session.get(url, headers=self.headers)
            response.raise_for_status()
            
            # Basic implementation
            return [{
                'url': url,
                'quality': f'{prefix}Filemoon' if prefix else 'Filemoon',
                'headers': dict(self.headers)
            }]
            
        except Exception as e:
            import traceback
            print(f"❌ Error in FilemoonExtractor: {e}")
            with open('error.txt', 'a', encoding='utf-8') as f:
                f.write(f"Error in FilemoonExtractor: {e}\n")
                f.write(traceback.format_exc())
            return []

class StreamWishExtractor(BaseExtractor):
    def videosFromUrl(self, url: str, videoNameGen=None) -> List[Dict[str, Any]]:
        print(f"🔍 StreamWishExtractor.videosFromUrl: {url}")
        try:
            with open('error.txt', 'a', encoding='utf-8') as f:
                f.write(f"\nAttempting StreamWishExtractor: {url}\n")
            
            # Get embed URL
            if "/f/" in url:
                video_id = url.split("/f/")[1]
                embed_url = f"https://streamwish.com/{video_id}"
            else:
                embed_url = url
            
            with open('error.txt', 'a', encoding='utf-8') as f:
                f.write(f"Fetching embed URL: {embed_url}\n")
                
            response = self.session.get(embed_url, headers=self.headers)
            response.raise_for_status()
            
            # Basic implementation - would need JS unpacking logic for complete implementation
            quality = "720p"  # Default quality
            name = videoNameGen(quality) if videoNameGen else f"StreamWish:{quality}"
            
            return [{
                'url': url,
                'quality': name,
                'headers': dict(self.headers)
            }]
            
        except Exception as e:
            import traceback
            print(f"❌ Error in StreamWishExtractor: {e}")
            with open('error.txt', 'a', encoding='utf-8') as f:
                f.write(f"Error in StreamWishExtractor: {e}\n")
                f.write(traceback.format_exc())
            return []

# --- Playlist Utils Implementation ---
class PlaylistUtils:
    def __init__(self, session: requests.Session, headers: Dict[str, str] = None):
        self.session = session
        self.headers = headers if headers is not None else {}

    def extractFromHls(self, playlistUrl: str, referer: str = "", videoNameGen=None, subtitleList: List[Track] = None, audioList: List[Track] = None) -> List[Dict[str, Any]]:
        print(f"🔍 PlaylistUtils.extractFromHls: {playlistUrl}")
        videos = []
        
        try:
            with open('error.txt', 'a', encoding='utf-8') as f:
                f.write(f"\nExtracting from HLS: {playlistUrl}\n")
                f.write(f"Referer: {referer}\n")
            
            # Setup headers for HLS request
            request_headers = dict(self.headers)
            if referer:
                request_headers['Referer'] = referer
            
            # Fetch the HLS playlist
            response = self.session.get(playlistUrl, headers=request_headers)
            if response.status_code != 200:
                with open('error.txt', 'a', encoding='utf-8') as f:
                    f.write(f"Failed to fetch HLS playlist: {response.status_code}\n")
                # Return basic fallback
                quality = "720p" if "720" in playlistUrl else "1080p" if "1080" in playlistUrl else "Unknown"
                name = videoNameGen(quality) if videoNameGen else quality
                return [{'url': playlistUrl, 'quality': name, 'headers': request_headers}]
            
            master_playlist = response.text
            
            # If no stream information, just return the main URL
            if "#EXT-X-STREAM-INF:" not in master_playlist:
                with open('error.txt', 'a', encoding='utf-8') as f:
                    f.write(f"No stream information in playlist, returning main URL\n")
                quality = "original"
                name = videoNameGen(quality) if videoNameGen else quality
                return [{
                    'url': playlistUrl, 
                    'quality': name, 
                    'headers': request_headers,
                    'subtitles': subtitleList or [],
                    'audio_tracks': audioList or []
                }]
            
            # Extract streams
            stream_sections = master_playlist.split("#EXT-X-STREAM-INF:")[1:]
            
            base_url = "/".join(playlistUrl.split("/")[:-1]) + "/"
            
            for section in stream_sections:
                resolution = "Unknown"
                bandwidth = ""
                
                # Extract resolution
                if "RESOLUTION=" in section:
                    resolution_part = section.split("RESOLUTION=")[1].split(",")[0]
                    resolution = resolution_part.split("x")[1] + "p" if "x" in resolution_part else resolution_part
                
                # Extract bandwidth for quality description
                if "BANDWIDTH=" in section:
                    bandwidth_val = int(section.split("BANDWIDTH=")[1].split(",")[0])
                    bandwidth = f" ({self._bytesIntoHumanReadable(bandwidth_val)})"
                
                # Get stream URL
                stream_url = section.split("\n", 1)[1].split("\n")[0]
                
                # Handle relative URLs
                if not stream_url.startswith("http"):
                    stream_url = base_url + stream_url
                
                quality = f"{resolution}{bandwidth}"
                name = videoNameGen(quality) if videoNameGen else quality
                
                videos.append({
                    'url': stream_url,
                    'quality': name,
                    'headers': request_headers,
                    'subtitles': subtitleList or [],
                    'audio_tracks': audioList or []
                })
            
            with open('error.txt', 'a', encoding='utf-8') as f:
                f.write(f"Extracted {len(videos)} HLS streams\n")
            
            return videos
            
        except Exception as e:
            import traceback
            print(f"❌ Error extracting from HLS: {e}")
            with open('error.txt', 'a', encoding='utf-8') as f:
                f.write(f"Error extracting from HLS: {e}\n")
                f.write(traceback.format_exc())
            
            # Return basic fallback
            quality = "720p" if "720" in playlistUrl else "1080p" if "1080" in playlistUrl else "Unknown"
            name = videoNameGen(quality) if videoNameGen else quality
            return [{'url': playlistUrl, 'quality': name, 'headers': self.headers}]

    def extractFromDash(self, mpdUrl: str, videoNameGen=None, referer: str = "", subtitleList: List[Track] = None, audioList: List[Track] = None) -> List[Dict[str, Any]]:
        print(f"🔍 PlaylistUtils.extractFromDash: {mpdUrl}")
        try:
            with open('error.txt', 'a', encoding='utf-8') as f:
                f.write(f"\nExtracting from DASH: {mpdUrl}\n")
            
            # Basic implementation - a full implementation would parse the MPD XML
            quality = "adaptive"
            name = videoNameGen(quality) if videoNameGen else f"DASH:{quality}"
            
            return [{
                'url': mpdUrl,
                'quality': name,
                'headers': self.headers,
                'subtitles': subtitleList or [],
                'audio_tracks': audioList or []
            }]
            
        except Exception as e:
            import traceback
            print(f"❌ Error extracting from DASH: {e}")
            with open('error.txt', 'a', encoding='utf-8') as f:
                f.write(f"Error extracting from DASH: {e}\n")
                f.write(traceback.format_exc())
            return []
    
    def _bytesIntoHumanReadable(self, bytes_val: int) -> str:
        """Convert bytes to human readable format"""
        kilobyte = 1000
        megabyte = kilobyte * 1000
        gigabyte = megabyte * 1000
        terabyte = gigabyte * 1000
        
        if 0 <= bytes_val < kilobyte:
            return f"{bytes_val} b/s"
        elif kilobyte <= bytes_val < megabyte:
            return f"{bytes_val // kilobyte} kb/s"
        elif megabyte <= bytes_val < gigabyte:
            return f"{bytes_val // megabyte} mb/s"
        elif gigabyte <= bytes_val < terabyte:
            return f"{bytes_val // gigabyte} gb/s"
        elif bytes_val >= terabyte:
            return f"{bytes_val // terabyte} tb/s"
        else:
            return f"{bytes_val} bits/s"

# --- Main Scraper Class ---
class AllAnimeScraper:
    # --- Constants ---
    PAGE_SIZE = 26

    # GraphQL Query Constants (Copied carefully, ensure formatting is exact)
    SEARCH_QUERY = "query ($search: SearchInput, $limit: Int, $page: Int, $translationType: VaildTranslationTypeEnumType, $countryOrigin: VaildCountryOriginEnumType) { shows(search: $search, limit: $limit, page: $page, translationType: $translationType, countryOrigin: $countryOrigin) { edges { _id name englishName nativeName thumbnail slugTime type season score availableEpisodesDetail } } }"
# Note: Added more fields to SEARCH_QUERY based on parseAnime usage

    DETAILS_QUERY = """query ($_id: String!) { show(_id: $_id) { _id name englishName nativeName thumbnail description genres studios season status score type availableEpisodesDetail } }"""
# Note: Added more fields to DETAILS_QUERY based on animeDetailsParse usage

    EPISODES_QUERY = "query ($_id: String!) { show(_id: $_id) { _id availableEpisodesDetail } }"

    STREAMS_QUERY = "query ($showId: String!, $translationType: VaildTranslationTypeEnumType!, $episodeString: String!) { episode(showId: $showId, translationType: $translationType, episodeString: $episodeString) { sourceUrls } }"
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
        
        # Define quality options (similar to Hanime)
        self.quality_list = ["1080p", "720p", "480p", "360p", "240p"]

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
            
            # Store the ID in the format that details endpoint expects
            anime_id = url  # This is the ID that will be used by get_anime_details

            anime_list.append({
                'title': f"{title} [AllAnime]",
                'url': url,
                'id': anime_id,  # Add the ID explicitly to ensure it's available for details
                'poster': thumbnail_url,
                'source': 'allanime',
                # Add other potential fields if needed later from 'item'
                'type': item.get('type'),
                #'year': item.get('season', {}).get('year'),
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
        
    def get_filters(self) -> Dict[str, Any]:
        """Get all available filters for AllAnime."""
        print("📋 Getting filters for AllAnime...")
        
        # Based on AllAnimeFilters.kt
        filters = {
            "origin": [
                {"id": "ALL", "name": "All"},
                {"id": "JP", "name": "Japan"},
                {"id": "CN", "name": "China"},
                {"id": "KR", "name": "Korea"}
            ],
            "seasons": [
                {"id": "all", "name": "All"},
                {"id": "Winter", "name": "Winter"},
                {"id": "Spring", "name": "Spring"},
                {"id": "Summer", "name": "Summer"},
                {"id": "Fall", "name": "Fall"}
            ],
            "years": [
                {"id": "all", "name": "All"}
            ] + [{"id": str(year), "name": str(year)} for year in range(2024, 1974, -1)],
            "sortBy": [
                {"id": "update", "name": "Update"},
                {"id": "Name_ASC", "name": "Name Asc"},
                {"id": "Name_DESC", "name": "Name Desc"},
                {"id": "Top", "name": "Ratings"}
            ],
            "types": [
                {"id": "Movie", "name": "Movie"},
                {"id": "ONA", "name": "ONA"},
                {"id": "OVA", "name": "OVA"},
                {"id": "Special", "name": "Special"},
                {"id": "TV", "name": "TV"},
                {"id": "Unknown", "name": "Unknown"}
            ],
            "genres": [
                {"id": "Action", "name": "Action"},
                {"id": "Adventure", "name": "Adventure"},
                {"id": "Cars", "name": "Cars"},
                {"id": "Comedy", "name": "Comedy"},
                {"id": "Dementia", "name": "Dementia"},
                {"id": "Demons", "name": "Demons"},
                {"id": "Drama", "name": "Drama"},
                {"id": "Ecchi", "name": "Ecchi"},
                {"id": "Fantasy", "name": "Fantasy"},
                {"id": "Game", "name": "Game"},
                {"id": "Harem", "name": "Harem"},
                {"id": "Historical", "name": "Historical"},
                {"id": "Horror", "name": "Horror"},
                {"id": "Isekai", "name": "Isekai"},
                {"id": "Josei", "name": "Josei"},
                {"id": "Kids", "name": "Kids"},
                {"id": "Magic", "name": "Magic"},
                {"id": "Martial Arts", "name": "Martial Arts"},
                {"id": "Mecha", "name": "Mecha"},
                {"id": "Military", "name": "Military"},
                {"id": "Music", "name": "Music"},
                {"id": "Mystery", "name": "Mystery"},
                {"id": "Parody", "name": "Parody"},
                {"id": "Police", "name": "Police"},
                {"id": "Psychological", "name": "Psychological"},
                {"id": "Romance", "name": "Romance"},
                {"id": "Samurai", "name": "Samurai"},
                {"id": "School", "name": "School"},
                {"id": "Sci-Fi", "name": "Sci-Fi"},
                {"id": "Seinen", "name": "Seinen"},
                {"id": "Shoujo", "name": "Shoujo"},
                {"id": "Shoujo Ai", "name": "Shoujo Ai"},
                {"id": "Shounen", "name": "Shounen"},
                {"id": "Shounen Ai", "name": "Shounen Ai"},
                {"id": "Slice of Life", "name": "Slice of Life"},
                {"id": "Space", "name": "Space"},
                {"id": "Sports", "name": "Sports"},
                {"id": "Super Power", "name": "Super Power"},
                {"id": "Supernatural", "name": "Supernatural"},
                {"id": "Thriller", "name": "Thriller"},
                {"id": "Unknown", "name": "Unknown"},
                {"id": "Vampire", "name": "Vampire"},
                {"id": "Yaoi", "name": "Yaoi"},
                {"id": "Yuri", "name": "Yuri"}
            ],
            "quality": self.quality_list
        }
        
        return filters
        
    def set_quality(self, quality: str) -> bool:
        """Set preferred video quality."""
        if quality in self.quality_list:
            self.preferences["preferred_quality"] = quality
            print(f"Quality preference set to: {quality}")
            return True
        else:
            print(f"Invalid quality. Available options: {', '.join(self.quality_list)}")
            return False

    # --- Public Scraper Methods ---
    
    def get_popular_anime(self, page=1, max_pages=5) -> List[Dict[str, Any]]:
        """Get popular anime from AllAnime."""
        print(f"💫 Getting popular anime from AllAnime...")
        results = []
        
        try:
            # We'll use the recommendations query which is used for popular anime in the Kotlin implementation
            data = {
                "variables": {
                    "type": "anime",
                    "size": self.PAGE_SIZE,
                    "dateRange": 7,
                    "page": page
                },
                "query": "query ($type: RecommendationQueryType, $size: Int, $dateRange: Int, $page: Int) { queryPopular(type: $type, size: $size, dateRange: $dateRange, page: $page) { recommendations { anyCard { _id name englishName nativeName thumbnail slugTime type } } } }"
            }
            
            request = self._build_post_request(data)
            response = self.session.send(request, timeout=20)
            
            if response.status_code == 400:
                print(f"❌ AllAnime popular anime request failed (400 Bad Request). Payload: {json.dumps(data)}")
                with open("error.txt", "w") as n: n.write("Payload: " + str(data)); n.write("\nResponse Text:" + str(response.text))
                print(f"Response Text: {response.text[:500]}")
                return []
            
            response.raise_for_status()
            
            response_data = response.json()
            
            # Process recommendations format
            recommendations = response_data.get('data', {}).get('queryPopular', {}).get('recommendations', [])
            
            for rec in recommendations:
                card = rec.get('anyCard')
                if not card or '_id' not in card:
                    continue
                    
                title = card.get('name', 'Unknown Title')
                if self._get_preference("preferred_title_style") == "eng":
                    title = card.get('englishName') or title
                elif self._get_preference("preferred_title_style") == "native":
                    title = card.get('nativeName') or title
                    
                thumbnail_url = card.get('thumbnail')
                url = f"{card.get('_id')}<&sep>{card.get('slugTime', '')}<&sep>{self._slugify(card.get('name', ''))}"
                anime_id = url  # This is the ID that will be used by get_anime_details
                
                results.append({
                    'title': f"{title} [AllAnime]",
                    'url': url,
                    'id': anime_id,  # Add the ID explicitly to ensure it's available for details
                    'poster': thumbnail_url,
                    'source': 'allanime',
                    'type': card.get('type')
                })
                
            print(f"✅ Found {len(results)} popular anime from AllAnime")
            return results
            
        except requests.exceptions.Timeout:
            print("❌ AllAnime popular anime request timed out.")
        except requests.exceptions.RequestException as e:
            print(f"❌ AllAnime popular anime request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status: {e.response.status_code}")
                print(f"Response body: {e.response.text[:500]}")
        except json.JSONDecodeError:
            print("❌ Failed to parse JSON response from AllAnime popular anime request.")
        except Exception as e:
            import traceback
            print(f"An unexpected error occurred during AllAnime popular anime request: {e}")
            print(traceback.format_exc())
            
        return results
    
    def get_latest_anime(self, page=1, max_pages=5) -> List[Dict[str, Any]]:
        """Get latest anime from AllAnime."""
        print(f"🆕 Getting latest anime from AllAnime...")
        results = []
        
        try:
            # For latest anime, we'll use the search API with a specific sort 
            data = {
                "variables": {
                    "search": {
                        "allowAdult": False,
                        "allowUnknown": False,
                        "sortBy": "update"  # Sort by latest updates
                    },
                    "limit": self.PAGE_SIZE,
                    "page": page,
                    "translationType": self._get_preference("preferred_sub"),
                    "countryOrigin": "ALL"
                },
                "query": self.SEARCH_QUERY
            }
            
            request = self._build_post_request(data)
            response = self.session.send(request, timeout=20)
            
            if response.status_code == 400:
                print(f"❌ AllAnime latest anime request failed (400 Bad Request). Payload: {json.dumps(data)}")
                with open("error.txt", "w") as n: n.write("Payload: " + str(data)); n.write("\nResponse Text:" + str(response.text))
                print(f"Response Text: {response.text[:500]}")
                return []
                
            response.raise_for_status()
            
            response_data = response.json()
            results = self._parse_anime(response_data)
            
            print(f"✅ Found {len(results)} latest anime from AllAnime")
            return results
            
        except requests.exceptions.Timeout:
            print("❌ AllAnime latest anime request timed out.")
        except requests.exceptions.RequestException as e:
            print(f"❌ AllAnime latest anime request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status: {e.response.status_code}")
                print(f"Response body: {e.response.text[:500]}")
        except json.JSONDecodeError:
            print("❌ Failed to parse JSON response from AllAnime latest anime request.")
        except Exception as e:
            import traceback
            print(f"An unexpected error occurred during AllAnime latest anime request: {e}")
            print(traceback.format_exc())
            
        return results

    def search_anime(self, query: str, filters: Optional[FilterSearchParams] = None, page=1, max_pages=5) -> List[Dict[str, Any]]:
        """Search for anime on AllAnime by title or filters."""
        print(f"🔍 Searching for '{query}' on AllAnime...")
        results = []
        current_page = page
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

            # Fetch multiple pages if requested
            while current_page <= max_pages:
                variables["page"] = current_page
                
                data = {
                    "variables": variables,
                    "query": self.SEARCH_QUERY
                }

                request = self._build_post_request(data)
                response = self.session.send(request, timeout=20) # Add timeout

                if response.status_code == 400:
                     print(f"❌ AllAnime search failed (400 Bad Request). Payload: {json.dumps(data)}")
                     with open("error.txt", "w") as n: n.write("Payload: " + str(data)); n.write("\nRespone Text:" + str(response.text))
                     print(f"Response Text: {response.text[:500]}")
                     break
                
                response.raise_for_status() # Raise an exception for other bad status codes

                response_data = response.json()
                page_results = self._parse_anime(response_data)
                
                if not page_results:
                    # No more results
                    break
                    
                results.extend(page_results)
                print(f"Found {len(page_results)} results on page {current_page}. Total: {len(results)}")
                
                # Check if we can continue for more pages
                if len(page_results) < self.PAGE_SIZE:
                    # Less than a full page, assume no more results
                    break
                    
                current_page += 1

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
            anime_id = url

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
            print(f"❌ Failed to get anime details from AllAnime: {e} payload: {data} response: {response.text}")
            with open("error.txt", "w") as n: n.write("Payload: " + str(data)); n.write("\nRespone Text:" + str(response.text))
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
            
            # Since we now get the whole object, we need to parse it differently
            if isinstance(available_episodes, dict):
                episode_list_raw = available_episodes.get(sub_pref, [])
            else:
                # Try to parse the string if it's not a dict
                try:
                    # It might be a JSON string
                    if isinstance(available_episodes, str):
                        available_episodes = json.loads(available_episodes)
                        episode_list_raw = available_episodes.get(sub_pref, [])
                    else:
                        print(f"❌ Unexpected format for availableEpisodesDetail: {type(available_episodes)}")
                        print(f"Data: {available_episodes}")
                        episode_list_raw = []
                except json.JSONDecodeError:
                    print(f"❌ Could not parse availableEpisodesDetail as JSON: {available_episodes}")
                    episode_list_raw = []

            if not episode_list_raw:
                print(f"❌ No '{sub_pref}' episodes found for this anime.")
                # Optionally, try the other type if one is empty
                other_pref = "dub" if sub_pref == "sub" else "sub"
                
                if isinstance(available_episodes, dict):
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
            print(f"❌ Failed to get episodes from AllAnime: {e} payload: {data} response: {response.text}")
            with open("error.txt", "w") as n: n.write("Payload: " + str(data)); n.write("\nRespone Text:" + str(response.text))
            
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
        import concurrent.futures
        from threading import Lock
        
        print(f"🎥 Extracting video sources from AllAnime episode...")
        video_sources = []
        server_list: List[Tuple[Dict[str, Any], float]] = [] # Store as (server_info, priority)
        extracted_video_list: List[Tuple[Dict[str, Any], float]] = [] # Store as (video_dict, priority)
        extracted_video_list_lock = Lock()  # Lock for thread-safe appending to extracted_video_list

        try:
            # Log start of extraction to error.txt for debugging
            with open('error.txt', 'a', encoding='utf-8') as f:
                f.write(f"\n\n===== STARTING VIDEO SOURCE EXTRACTION =====\n")
                f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Episode payload (truncated): {episode_url_payload[:200]}...\n")
            
            data = json.loads(episode_url_payload) # Parse the payload stored in the URL
            request = self._build_post_request(data)
            response = self.session.send(request, timeout=20)

            # Log API response details
            with open('error.txt', 'a', encoding='utf-8') as f:
                f.write(f"API Response Status: {response.status_code}\n")
                f.write(f"API Request URL: {request.url}\n")
                f.write(f"API Request Headers: {request.headers}\n")
                f.write(f"API Request Body: {request.body.decode('utf-8') if hasattr(request.body, 'decode') else request.body}\n\n")

            if response.status_code == 400:
                 print(f"❌ AllAnime stream fetch failed (400 Bad Request). Payload: {json.dumps(data)}")
                 print(f"Response Text: {response.text[:500]}")
                 with open('error.txt', 'a', encoding='utf-8') as f:
                    f.write(f"Error 400 Bad Request\n")
                    f.write(f"Response Text: {response.text}\n")
                 return []
            response.raise_for_status()

            response_data = response.json()

            # Add detailed debugging
            print(f"DEBUG: Raw response: {json.dumps(response_data)[:300]}...")
            with open('error.txt', 'a', encoding='utf-8') as f:
                f.write(f"Response Data: {json.dumps(response_data, indent=2)}\n\n")

            data_obj = response_data.get('data')
            if not data_obj:
                print("❌ No 'data' field in API response.")
                print(f"Full response: {response_data}")
                with open('error.txt', 'a', encoding='utf-8') as f:
                    f.write(f"Error: No 'data' field in API response\n")
                return []

            episode_data = data_obj.get('episode')
            if not episode_data:
                print("❌ No 'episode' field in data object.")
                print(f"Data object: {data_obj}")
                with open('error.txt', 'a', encoding='utf-8') as f:
                    f.write(f"Error: No 'episode' field in data object\n")
                return []

            if not isinstance(episode_data, dict):
                print(f"❌ 'episode' is not a dictionary. Type: {type(episode_data)}")
                print(f"Episode data: {episode_data}")
                with open('error.txt', 'a', encoding='utf-8') as f:
                    f.write(f"Error: 'episode' is not a dictionary. Type: {type(episode_data)}\n")
                return []

            if 'sourceUrls' not in episode_data:
                print("❌ 'sourceUrls' field not found in episode data.")
                print(f"Episode data keys: {episode_data.keys()}")
                with open('error.txt', 'a', encoding='utf-8') as f:
                    f.write(f"Error: 'sourceUrls' field not found in episode data\n")
                    f.write(f"Episode data keys: {episode_data.keys()}\n")
                return []

            raw_source_urls = episode_data.get('sourceUrls', [])
            if not raw_source_urls:
                print("❌ 'sourceUrls' is empty or null.")
                with open('error.txt', 'a', encoding='utf-8') as f:
                    f.write(f"Error: 'sourceUrls' is empty or null\n")
                return []

            print(f"DEBUG: Found {len(raw_source_urls)} raw sources.")
            with open('error.txt', 'a', encoding='utf-8') as f:
                f.write(f"Found {len(raw_source_urls)} raw sources\n")
                for i, source in enumerate(raw_source_urls):
                    f.write(f"Source {i+1}: {json.dumps(source, indent=2)}\n")

            if not isinstance(raw_source_urls, list):
                 print(f"❌ Unexpected format for sourceUrls: {type(raw_source_urls)}")
                 with open('error.txt', 'a', encoding='utf-8') as f:
                     f.write(f"Error: Unexpected format for sourceUrls: {type(raw_source_urls)}\n")
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
                     with open('error.txt', 'a', encoding='utf-8') as f:
                         f.write(f"Skipping invalid video source item: {video_source}\n")
                     continue

                 source_url_raw = video_source.get('sourceUrl', '')
                 source_url = self._decrypt_source(source_url_raw)
                 source_name_raw = video_source.get('sourceName', '')
                 source_name = source_name_raw.lower()
                 source_type = video_source.get('type', '')
                 priority = float(video_source.get('priority', 0.0)) # Ensure float

                 with open('error.txt', 'a', encoding='utf-8') as f:
                     f.write(f"Processing source: {source_name_raw}\n")
                     f.write(f"  Raw URL: {source_url_raw}\n")
                     f.write(f"  Decrypted URL: {source_url}\n")
                     f.write(f"  Type: {source_type}\n")
                     f.write(f"  Priority: {priority}\n")

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
                                 with open('error.txt', 'a', encoding='utf-8') as f:
                                     f.write(f"  ✅ Added as internal host: {name.lower()}\n")
                                 break
                     if is_internal: continue # Skip other checks if matched internal

                 # Check player type
                 if source_type == "player" and "player" in alt_hoster_selection:
                     server_info['name'] = f"player@{source_name_raw}"
                     temp_server_list.append((server_info, priority))
                     with open('error.txt', 'a', encoding='utf-8') as f:
                         f.write(f"  ✅ Added as player: {source_name_raw}\n")
                     continue # Skip other checks if matched player

                 # Check alternative hosters
                 matched_alt = False
                 for alt_hoster, url_matches in mappings.items():
                     if alt_hoster in alt_hoster_selection and any(match in source_url for match in url_matches):
                         server_info['name'] = alt_hoster
                         temp_server_list.append((server_info, priority))
                         matched_alt = True
                         with open('error.txt', 'a', encoding='utf-8') as f:
                             f.write(f"  ✅ Added as alt hoster: {alt_hoster}\n")
                         break
                 
                 if not matched_alt and not is_internal:
                     with open('error.txt', 'a', encoding='utf-8') as f:
                         f.write(f"  ❌ No matching hoster found, skipped\n")

            with open('error.txt', 'a', encoding='utf-8') as f:
                f.write(f"\nSelected {len(temp_server_list)} servers for processing\n")
                for i, (server, priority) in enumerate(temp_server_list):
                    f.write(f"Server {i+1}: {server['name']} (priority: {priority})\n")

            # --- Extract Videos from Selected Servers using thread pool ---
            def extract_videos_from_server(server_tuple):
                server_info, priority = server_tuple
                s_name = server_info['name']
                s_url = server_info['url']
                s_raw_name = server_info['raw_name']  # Original name for internal extractor
                local_videos = []

                try:
                    with open('error.txt', 'a', encoding='utf-8') as f:
                        f.write(f"\n[Thread] Extracting videos from: {s_name} ({s_url})\n")

                    if s_name.startswith("internal "):
                        pass
                        #local_videos = self.all_anime_extractor.videoFromUrl(s_url, s_raw_name)
                    elif s_name.startswith("player@"):
                        print(f"Player type extraction not implemented for: {s_url}")
                        with open('error.txt', 'a', encoding='utf-8') as f:
                            f.write(f"Player type extraction not implemented\n")
                    elif s_name == "vidstreaming":
                        pass
                        #local_videos = self.gogo_stream_extractor.videosFromUrl(s_url.replace("//", "https://"))
                    elif s_name == "doodstream":
                        pass
                        #local_videos = self.dood_extractor.videosFromUrl(s_url)
                    elif s_name == "okru":
                        local_videos = self.okru_extractor.videosFromUrl(s_url)
                    elif s_name == "mp4upload":
                        local_videos = self.mp4upload_extractor.videosFromUrl(s_url, self.headers)
                    elif s_name == "streamlare":
                        pass
                        #local_videos = self.streamlare_extractor.videosFromUrl(s_url)
                    elif s_name == "filemoon":
                        pass
                        #local_videos = self.filemoon_extractor.videosFromUrl(s_url, prefix="Filemoon:")
                    elif s_name == "streamwish":
                        pass
                        #local_videos = self.streamwish_extractor.videosFromUrl(s_url, videoNameGen=lambda q: f"StreamWish:{q}")

                    with open('error.txt', 'a', encoding='utf-8') as f:
                        f.write(f"[Thread] Extracted {len(local_videos)} videos from {s_name}\n")
                    
                    video_tuples = []
                    # Process videos from this server
                    for video in local_videos:
                        if isinstance(video, dict):
                            video['source'] = 'allanime'  # Add source identifier
                            video_tuples.append((video, priority))
                        elif hasattr(video, 'videoUrl') and hasattr(video, 'videoTitle'):  # Handle Video object from placeholders
                            video_dict = {
                                'url': video.videoUrl,
                                'quality': video.videoTitle,
                                'headers': video.headers,
                                'source': 'allanime',
                                'subtitles': [{'url': sub.url, 'language': sub.lang} for sub in getattr(video, 'subtitleTracks', [])]
                            }
                            video_tuples.append((video_dict, priority))
                    
                    # Add to shared list with lock protection
                    with extracted_video_list_lock:
                        extracted_video_list.extend(video_tuples)
                        
                    return len(video_tuples)
                    
                except Exception as e:
                    print(f"Error extracting videos from server {s_name} ({s_url}): {e}")
                    import traceback
                    trace = traceback.format_exc()
                    print(trace)
                    with open('error.txt', 'a', encoding='utf-8') as f:
                        f.write(f"[Thread] Error extracting videos: {e}\n")
                        f.write(f"{trace}\n")
                    return 0
            
            # Process servers in parallel using ThreadPoolExecutor with max 3 workers
            print(f"⏳ Starting parallel extraction of {len(temp_server_list)} servers with max 3 workers...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                # Submit all tasks
                future_to_server = {executor.submit(extract_videos_from_server, server_tuple): server_tuple for server_tuple in temp_server_list}
                
                # Process results as they complete
                for future in concurrent.futures.as_completed(future_to_server):
                    server_tuple = future_to_server[future]
                    server_name = server_tuple[0]['name']
                    try:
                        count = future.result()
                        print(f"✅ Extracted {count} videos from {server_name}")
                    except Exception as e:
                        print(f"❌ Server {server_name} generated an exception: {e}")

            print(f"🔄 Parallel extraction complete. Processing {len(extracted_video_list)} videos...")
            with open('error.txt', 'a', encoding='utf-8') as f:
                f.write(f"\nExtracted {len(extracted_video_list)} total videos\n")

            # --- Sort Videos (like Kotlin's prioritySort) ---
            pref_server = self._get_preference("preferred_server")
            quality_pref = self._get_preference("preferred_quality")
            sub_pref = self._get_preference("preferred_sub") # sub or dub

            with open('error.txt', 'a', encoding='utf-8') as f:
                f.write(f"\nSorting videos with preferences:\n")
                f.write(f"  Preferred server: {pref_server}\n")
                f.write(f"  Preferred quality: {quality_pref}\n")
                f.write(f"  Preferred sub/dub: {sub_pref}\n")

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
                    
                # Enhanced quality scoring based on resolution
                resolution_score = 0
                # Extract resolution from quality string
                resolution_match = re.search(r'(\d+)p', quality)
                if resolution_match:
                    res_value = int(resolution_match.group(1))
                    # Map common resolutions to scores (higher is better)
                    resolution_map = {
                        2160: 5,  # 4K
                        1440: 4,  # 2K
                        1080: 3,  # 1080p
                        720: 2,   # 720p
                        480: 1,   # 480p
                        360: 0,   # 360p
                        240: -1,  # 240p
                        144: -2   # 144p
                    }
                    resolution_score = resolution_map.get(res_value, 0)

                # Score based on sub/dub preference (simple check in quality name)
                sub_dub_score = 0
                if sub_pref in quality:
                    sub_dub_score = 1

                # Return tuple for sorting (higher scores first)
                return (server_score, quality_score, resolution_score, sub_dub_score)

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
                with open('error.txt', 'a', encoding='utf-8') as f:
                    f.write(f"\n✅ Successfully found {len(video_sources)} video streams\n")
            else:
                print("ℹ️ No video streams found after processing servers.")
                with open('error.txt', 'a', encoding='utf-8') as f:
                    f.write(f"\n❌ No video streams found after processing servers\n")

            return video_sources

        except requests.exceptions.Timeout:
            print("❌ AllAnime stream fetch request timed out.")
            with open('error.txt', 'a', encoding='utf-8') as f:
                f.write(f"\nError: Request timed out\n")
            return []
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to get video sources from AllAnime: {e}")
            with open('error.txt', 'a', encoding='utf-8') as f:
                f.write(f"\nRequest error: {e}\n")
            return []
        except json.JSONDecodeError:
            print("❌ Failed to parse JSON payload/response for AllAnime video sources.")
            with open('error.txt', 'a', encoding='utf-8') as f:
                f.write(f"\nJSON decode error\n")
            return []
        except Exception as e:
            import traceback
            trace = traceback.format_exc()
            print(f"❌ An unexpected error occurred during AllAnime video source fetch: {e}")
            print(trace)
            with open('error.txt', 'a', encoding='utf-8') as f:
                f.write(f"\nUnexpected error: {e}\n")
                f.write(f"{trace}\n")
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