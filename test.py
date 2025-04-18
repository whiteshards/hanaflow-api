from flask import Flask, request, render_template_string
import requests
import json
import re
from Crypto.Cipher import AES
import base64
import binascii

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>MegaCloud Decryption Test</title>
    <style>
        .container { max-width: 800px; margin: 0 auto; padding: 20px; }
        .debug { margin-top: 20px; background: #f5f5f5; padding: 10px; }
        pre { white-space: pre-wrap; }
        .success { color: green; }
        .error { color: red; }
    </style>
</head>
<body>
    <div class="container">
        <h1>MegaCloud Decryption Test</h1>
        <form method="post">
            <input type="text" name="embed_url" placeholder="Enter MegaCloud embed URL" size="50" 
                   value="{{ embed_url or '' }}">
            <button type="submit">Decrypt</button>
        </form>

        {% if result %}
        <div class="debug">
            <h3>Results:</h3>
            {% if result.error %}
                <p class="error">Error: {{ result.error }}</p>
            {% else %}
                <p class="success">Decryption successful!</p>
                <h4>Video Sources:</h4>
                <ul>
                {% for source in result.sources %}
                    <li>{{ source }}</li>
                {% endfor %}
                </ul>
            {% endif %}
            
            <h4>Debug Info:</h4>
            <pre>{{ result.debug }}</pre>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

def decrypt_megacloud(ciphertext, key):
    """Decrypt MegaCloud encrypted sources using AES"""
    try:
        cipher = AES.new(key.encode(), AES.MODE_CBC, iv=bytes(16))
        decrypted = cipher.decrypt(base64.b64decode(ciphertext))
        return decrypted.decode('utf-8').strip()
    except Exception as e:
        return None, f"Decryption failed: {str(e)}"

def extract_megacloud_sources(embed_url):
    """Extract and decrypt MegaCloud sources"""
    result = {
        'sources': [],
        'error': None,
        'debug': {}
    }
    
    try:
        # Extract video ID
        video_id = embed_url.split('/e-1/')[-1].split('?')[0]
        if not video_id:
            result['error'] = "Could not extract video ID"
            return result

        # Get sources from API
        api_url = f"https://megacloud.tv/embed-2/ajax/e-1/getSources?id={video_id}"
        headers = {
            'Referer': 'https://hianimez.to/',
            'X-Requested-With': 'XMLHttpRequest'
        }
        response = requests.get(api_url, headers=headers)
        data = response.json()
        result['debug']['api_response'] = data

        if not data.get('encrypted', True):
            # Not encrypted, return sources directly
            result['sources'] = [s['file'] for s in data.get('sources', [])]
            return result

        # Get player script to extract decryption keys
        script_url = "https://megacloud.tv/js/player/a/prod/e1-player.min.js"
        script = requests.get(script_url).text
        result['debug']['script_url'] = script_url

        # Find key parts in script (following reference implementation)
        key_pairs = re.findall(r'case\s*0x[0-9a-f]+:(?![^;]*=partKey)\s*\w+\s*=\s*(\w+)\s*,\s*\w+\s*=\s*(\w+);', script)
        if not key_pairs:
            result['error'] = "Could not find decryption keys in player script"
            return result

        # Find hex values for each key part
        key_segments = []
        for var1, var2 in key_pairs[:4]:  # Use first 4 pairs as in reference
            # Find hex values for each variable
            hex1 = re.search(f',{var1}=((?:0x)?([0-9a-fA-F]+))', script)
            hex2 = re.search(f',{var2}=((?:0x)?([0-9a-fA-F]+))', script)
            
            if hex1 and hex2:
                val1 = hex1.group(1).replace('0x', '')
                val2 = hex2.group(1).replace('0x', '')
                try:
                    # Convert hex to decimal as in reference
                    key_segments.extend([int(val1, 16), int(val2, 16)])
                except:
                    continue

        if not key_segments:
            result['error'] = "Could not extract hex values for decryption keys"
            return result

        # Build decryption key from segments
        key = ''.join([str(k) for k in key_segments])[:32]  # Truncate to 32 chars
        result['debug']['key_segments'] = key_segments
        result['debug']['key'] = key

        # Decrypt sources
        ciphertext = data['sources']
        decrypted = decrypt_megacloud(ciphertext, key)
        if not decrypted:
            result['error'] = "Decryption failed"
            return result

        result['sources'] = json.loads(decrypted)
        return result

    except Exception as e:
        result['error'] = f"Error: {str(e)}"
        return result

@app.route('/', methods=['GET', 'POST'])
def index():
    embed_url = result = None
    
    if request.method == 'POST':
        embed_url = request.form.get('embed_url', '').strip()
        if embed_url and 'megacloud' in embed_url:
            result = extract_megacloud_sources(embed_url)
            result['debug'] = json.dumps(result['debug'], indent=2)
        else:
            result = {'error': 'Please enter a valid MegaCloud embed URL'}

    return render_template_string(HTML_TEMPLATE, 
                               embed_url=embed_url,
                               result=result)

if __name__ == '__main__':
    app.run(port=5001, debug=True)
