import re
import requests
from typing import List, Optional, Callable, Dict, Any
from urllib.parse import urljoin

class Track:
    def __init__(self, url: str, label: str):
        self.url = url
        self.label = label

class Video:
    def __init__(self, 
                 url: str, 
                 name: str, 
                 quality: str,
                 headers: dict = None,
                 subtitles: List[Track] = None,
                 audio_tracks: List[Track] = None):
        self.url = url
        self.name = name
        self.quality = quality
        self.headers = headers or {}
        self.subtitles = subtitles or []
        self.audio_tracks = audio_tracks or []

class PlaylistUtils:
    PLAYLIST_SEPARATOR = "#EXT-X-STREAM-INF:"
    SUBTITLE_REGEX = re.compile(r'#EXT-X-MEDIA:TYPE=SUBTITLES.*?NAME="(.*?)".*?URI="(.*?)"')
    AUDIO_REGEX = re.compile(r'#EXT-X-MEDIA:TYPE=AUDIO.*?NAME="(.*?)".*?URI="(.*?)"')

    def __init__(self, session: requests.Session = None):
        self.session = session or requests.Session()

    def extract_from_hls(self, 
                        playlist_url: str,
                        referer: str = "",
                        video_name_gen: Callable[[str], str] = lambda q: q,
                        subtitle_list: List[Track] = None,
                        audio_list: List[Track] = None) -> List[Video]:
        """
        Extract videos from HLS playlist.
        Returns list of Video objects with quality, URLs and tracks.
        """
        try:
            headers = {
                'Accept': '*/*',
                'Referer': referer,
                'User-Agent': self.session.headers.get('User-Agent', '')
            }
            
            response = self.session.get(playlist_url, headers=headers)
            response.raise_for_status()
            playlist = response.text

            # Single stream case
            if self.PLAYLIST_SEPARATOR not in playlist:
                return [Video(
                    playlist_url,
                    video_name_gen("Auto"),
                    "Auto",
                    headers=headers,
                    subtitles=subtitle_list,
                    audio_tracks=audio_list
                )]

            # Parse master playlist
            base_url = self._get_base_url(playlist_url)
            subtitles = (subtitle_list or []) + self._parse_tracks(playlist, base_url, self.SUBTITLE_REGEX)
            audio_tracks = (audio_list or []) + self._parse_tracks(playlist, base_url, self.AUDIO_REGEX)

            videos = []
            for segment in playlist.split(self.PLAYLIST_SEPARATOR)[1:]:
                lines = segment.split('\n')
                if len(lines) < 2:
                    continue

                # Extract quality/resolution
                resolution = self._parse_resolution(lines[0])
                stream_url = lines[1].strip()
                
                if not stream_url:
                    continue

                # Make absolute URL if relative
                if not stream_url.startswith(('http', '//')):
                    stream_url = urljoin(base_url, stream_url)

                videos.append(Video(
                    stream_url,
                    video_name_gen(resolution),
                    resolution,
                    headers=headers,
                    subtitles=subtitles,
                    audio_tracks=audio_tracks
                ))

            return videos

        except Exception as e:
            print(f"Error parsing HLS playlist: {e}")
            return []

    def _parse_resolution(self, line: str) -> str:
        """Extract resolution from HLS segment line"""
        match = re.search(r'RESOLUTION=(\d+)x(\d+)', line)
        if match:
            return f"{match.group(2)}p"
        return "Auto"

    def _parse_tracks(self, playlist: str, base_url: str, regex: re.Pattern) -> List[Track]:
        """Parse subtitles or audio tracks from playlist"""
        tracks = []
        for match in regex.finditer(playlist):
            label = match.group(1)
            url = match.group(2)
            if not url.startswith(('http', '//')):
                url = urljoin(base_url, url)
            tracks.append(Track(url, label))
        return tracks

    def _get_base_url(self, url: str) -> str:
        """Get base URL for relative path resolution"""
        parts = url.split('/')
        return '/'.join(parts[:-1]) + '/'

    def extract_from_dash(self, mpd_url: str, **kwargs) -> List[Video]:
        """Placeholder for DASH extraction"""
        # Similar implementation would go here
        return []