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
        return jsonify({"error": "No URL"}), 400

    try:
        # استخدام AllOrigins بنمط RAW لجلب الصفحة
        proxy_url = f"https://api.allorigins.win/raw?url={requests.utils.quote(target_url)}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(proxy_url, headers=headers, timeout=30)
        
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')

        # 1. استخراج الوصف
        desc = "الوصف غير متوفر."
        desc_div = soup.find('div', id='perfume-description-content')
        if desc_div and desc_div.find('p'):
            desc = desc_div.find('p').get_text(strip=True)

        # 2. استخراج النوتات بذكاء
        def get_notes_by_label(html_text, label):
            found = []
            if label in html_text:
                try:
                    # نأخذ المقطع الذي يلي العنوان مباشرة
                    segment = html_text.split(label)[1].split('</div>')[0]
                    # نمط البحث عن رابط الصورة واسم النوتة
                    pattern = r'src="([^"]+)".*?pyramid-note-label[^>]*>\s*([^<]+)\s*</span>'
                    matches = re.findall(pattern, segment, re.DOTALL | re.IGNORECASE)
                    for img, name in matches:
                        found.append({'name': name.strip(), 'image': img.strip()})
                except: pass
            return found

        return jsonify({
            "status": "success",
            "description": desc,
            "notes": {
                "top": get_notes_by_label(html, 'Top Notes'),
                "middle": get_notes_by_label(html, 'Middle Notes'),
                "base": get_notes_by_label(html, 'Base Notes')
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
