from flask import Flask, request, jsonify
from flask_cors import CORS
from bs4 import BeautifulSoup
import urllib.request
import urllib.parse
import json
import os

app = Flask(__name__)
CORS(app)

@app.route('/scrape', methods=['GET'])
def scrape_fragrantica():
    target_url = request.args.get('url')
    if not target_url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        # استخدام وسيط (Bridge) لتجاوز حماية Fragrantica
        # هذا المسار لا يمكن حظره لأنه يطلب البيانات من سيرفر AllOrigins
        proxy_url = "https://api.allorigins.win/get?url=" + urllib.parse.quote(target_url)
        
        req = urllib.request.Request(proxy_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            html = data.get('contents', '')

        if not html:
            return jsonify({"error": "Empty content from bridge"}), 502
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # استخراج الوصف
        desc = "No description found"
        desc_div = soup.find('div', id='perfume-description-content')
        if desc_div and desc_div.find('p'):
            desc = desc_div.find('p').get_text(strip=True)

        # استخراج النوتات
        import re
        def get_notes(html_text, level_name):
            notes = []
            parts = html_text.split(level_name)
            if len(parts) > 1:
                block = parts[1][:3000]
                pattern = r'<a[^>]*pyramid-note-link[^>]*>.*?<img[^>]*src="([^"]+)".*?<span[^>]*pyramid-note-label[^>]*>\s*([^<]+)\s*<\/span>'
                matches = re.findall(pattern, block, re.IGNORECASE | re.DOTALL)
                for img, name in matches:
                    notes.append({'name': name.strip(), 'image': img.strip()})
            return notes

        return jsonify({
            "version": "2.0-NEW",
            "description": desc,
            "notes": {
                "top": get_notes(html, 'Top Notes'),
                "middle": get_notes(html, 'Middle Notes'),
                "base": get_notes(html, 'Base Notes')
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
