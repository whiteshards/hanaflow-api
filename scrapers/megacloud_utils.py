import json
import requests
import base64
import logging
from typing import Optional, List, Dict, Any
from .webview_resolver import WebViewResolver
from .playlist_utils import PlaylistUtils, Video

# [Previous crypto implementation remains...]

class MegaCloudExtractor:
    def __init__(self, session=None):
        self.session = session or requests.Session()
        self.webview = WebViewResolver(dict(self.session.headers))
        self.playlist_utils = PlaylistUtils(self.session)
        self.log = logging.getLogger(__name__)

    def get_videos_from_url(self, url: str) -> List[Video]:
        """Main entry point - gets videos from MegaCloud URL"""
        try:
            # First try direct decryption
            sources = self._get_sources_direct(url)
            
            # Fall back to WebView if needed
            if not sources and ('megacloud.tv' in url or 'megacloud.blog' in url):
                sources = self._get_sources_webview(url)
                
            if not sources:
                return []
                
            # Process sources through playlist utils
            master_url = sources[0].get('file')
            if not master_url:
                return []
                
            return self.playlist_utils.extract_from_hls(
                master_url,
                referer=url,
                video_name_gen=lambda q: f"MegaCloud - {q}"
            )
            
        except Exception as e:
            self.log.error(f"Failed to get videos: {e}", exc_info=True)
            return []

    def _get_sources_direct(self, url: str) -> Optional[List[Dict]]:
        """Try direct decryption approach"""
        try:
            video_id = self._extract_video_id(url)
            if not video_id:
                return None
                
            api_url = f"https://megacloud.tv/embed-2/ajax/e-1/getSources?id={video_id}"
            response = self.session.get(api_url, headers={
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': url
            })
            response.raise_for_status()
            
            data = response.json()
            if not data.get('encrypted'):
                return data.get('sources', [])
                
            ciphertext = data.get('sources')
            if not ciphertext:
                return None
                
            decrypted = decrypt_source_url(ciphertext)
            return decrypted
            
        except Exception as e:
            self.log.warning(f"Direct decryption failed: {e}")
            return None

    def _get_sources_webview(self, url: str) -> Optional[List[Dict]]:
        """Fallback to WebView approach"""
        try:
            video_id = self._extract_video_id(url)
            if not video_id:
                return None
            return self.webview.get_sources(video_id)
        except Exception as e:
            self.log.warning(f"WebView resolver failed: {e}")
            return None

    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from URL"""
        parts = url.split('/e-1/')
        if len(parts) < 2:
            return None
        return parts[-1].split('?')[0]