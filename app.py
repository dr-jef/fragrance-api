from flask import Flask, request, jsonify
from flask_cors import CORS
from bs4 import BeautifulSoup
import requests
import re
import os

app = Flask(__name__)
CORS(app)

@app.route('/scrape', methods=['GET'])
def scrape_fragrantica():
    target_url = request.args.get('url')
    
    # 1. التحقق من وجود الرابط وصحته
    if not target_url:
        return jsonify({"error": "Missing URL parameter"}), 400
    
    if 'fragrantica.com' not in target_url:
        return jsonify({"error": "Only Fragrantica URLs are allowed"}), 400

    # التأكد من وجود البروتوكول
    if not target_url.startswith('http'):
        target_url = 'https://' + target_url

    try:
        # 2. استخدام جسر AllOrigins لجلب البيانات
        proxy_url = f"https://api.allorigins.win/get?url={requests.utils.quote(target_url)}"
        
        response = requests.get(proxy_url, timeout=30)
        response.raise_for_status() # سيثير خطأ إذا كان الرد 404 أو 500
        
        data = response.json()
        html = data.get('contents', '')

        if not html or 'Checking your browser' in html:
            return jsonify({"error": "Cloudflare bypass failed on bridge"}), 502
            
        soup = BeautifulSoup(html, 'html.parser')

        # 3. استخراج الوصف
        desc = "No description available"
        desc_div = soup.find('div', id='perfume-description-content')
        if desc_div and desc_div.find('p'):
            desc = desc_div.find('p').get_text(strip=True)

        # 4. دالة استخراج النوتات
        def get_notes(html_text, level_name):
            notes = []
            parts = html_text.split(level_name)
            if len(parts) > 1:
                block = parts[1][:4000] 
                pattern = r'pyramid-note-link.*?src="([^"]+)".*?pyramid-note-label[^>]*>\s*([^<]+)\s*</span>'
                matches = re.findall(pattern, block, re.IGNORECASE | re.DOTALL)
                for img, name in matches:
                    notes.append({'name': name.strip(), 'image': img.strip()})
            return notes

        return jsonify({
            "status": "success",
            "description": desc,
            "notes": {
                "top": get_notes(html, 'Top Notes'),
                "middle": get_notes(html, 'Middle Notes'),
                "base": get_notes(html, 'Base Notes')
            }
        }), 200

    except Exception as e:
        # إرجاع تفاصيل الخطأ بدقة
        return jsonify({
            "status": "error",
            "message": str(e),
            "suggestion": "Try refreshing the page in a few seconds."
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
