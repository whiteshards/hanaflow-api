from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import logging
import json
import time
from typing import Optional, List, Dict

class WebViewResolver:
    TIMEOUT_SEC = 30  # Match Android timeout
    
    def __init__(self, headers: dict):
        self.headers = headers
        self.driver = None
        self.log = logging.getLogger(__name__)
        self.result = None
        
    def _init_driver(self):
        """Initialize headless Chrome with proper settings"""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument(f"user-agent={self.headers.get('User-Agent', '')}")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        self.driver = webdriver.Chrome(options=options)
        
    def _inject_scripts(self):
        """Inject required JavaScript files"""
        scripts = [
            # These would be the equivalent of the Android assets
            # In a real implementation, you'd need these JS files locally
            "https://cdnjs.cloudflare.com/ajax/libs/crypto-js/4.1.1/crypto-js.min.js",
            # Add megacloud.decodedpng.js and megacloud.getsrcs.js contents here
            # or load from local files
        ]
        
        for script in scripts:
            self.driver.execute_script(f"""
                var s = document.createElement('script');
                s.src = '{script}';
                document.head.appendChild(s);
            """)
            time.sleep(1)  # Allow script to load

    def get_sources(self, video_id: str) -> Optional[List[Dict]]:
        """Get sources using headless browser with proper timeout"""
        try:
            self._init_driver()
            
            # First load about page to set cookies
            self.driver.get("https://megacloud.tv/about")
            time.sleep(2)
            
            # Now load the embed page
            embed_url = f"https://megacloud.tv/embed-2/e-1/{video_id}"
            self.driver.get(embed_url)
            
            # Inject required scripts
            self._inject_scripts()
            
            # Execute the decryption script with timeout
            script = """
            return new Promise((resolve, reject) => {
                const timeout = setTimeout(() => {
                    reject(new Error('Timeout getting sources'));
                }, 25000);
                
                getSources(arguments[0])
                    .then(sources => {
                        clearTimeout(timeout);
                        resolve(JSON.stringify(sources));
                    })
                    .catch(err => {
                        clearTimeout(timeout);
                        reject(err);
                    });
            });
            """
            
            start_time = time.time()
            while time.time() - start_time < self.TIMEOUT_SEC:
                try:
                    result = self.driver.execute_async_script(script, video_id)
                    if result:
                        return json.loads(result)
                except Exception as e:
                    if "timeout" not in str(e).lower():
                        self.log.error(f"Script error: {e}")
                    time.sleep(1)
                    
            self.log.error("Timed out waiting for sources")
            return None
            
        except Exception as e:
            self.log.error(f"WebViewResolver failed: {e}")
            return None
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None