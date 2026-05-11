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
    if not target_url:
        return jsonify({"error": "رابط مفقود"}), 400

    try:
        # استخدام الرابط المباشر عبر AllOrigins الخام
        proxy_url = f"https://api.allorigins.win/raw?url={requests.utils.quote(target_url)}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        response = requests.get(proxy_url, headers=headers, timeout=30)
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')

        # 1. استخراج الوصف (نص صافي 100%)
        desc_text = "الوصف غير متوفر لهذا العطر."
        desc_div = soup.find('div', id='perfume-description-content')
        if desc_div:
            # مسح أي وسوم داخلية والحصول على النص فقط
            desc_text = desc_div.get_text(" ", strip=True)
            # تنظيف النص من أي علامات غريبة
            desc_text = re.sub(r'\s+', ' ', desc_text)[:500] + "..."

        # 2. استخراج النوتات (منطق مرن جداً)
        def get_notes_list(label):
            notes = []
            if label in html:
                segment = html.split(label)[1].split('</div>')[0]
                # البحث عن أي نمط يحتوي على رابط صورة واسم
                matches = re.findall(r'src="([^"]+nnotes[^"]+)".*?>\s*([^<]+)\s*</span>', segment, re.I)
                for img, name in matches:
                    notes.append({"name": name.strip(), "image": img.strip()})
            return notes

        return jsonify({
            "status": "success",
            "description": str(desc_text),
            "notes": {
                "top": get_notes_list('Top Notes'),
                "middle": get_notes_list('Middle Notes'),
                "base": get_notes_list('Base Notes')
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
