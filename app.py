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
        return jsonify({"error": "Missing URL"}), 400

    # تصحيح الرابط إذا كان ينقصه البروتوكول
    if not target_url.startswith('http'):
        target_url = 'https://' + target_url

    try:
        # استخدام AllOrigins بنمط RAW لجلب محتوى الصفحة بالكامل
        proxy_url = f"https://api.allorigins.win/raw?url={requests.utils.quote(target_url)}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        response = requests.get(proxy_url, headers=headers, timeout=30)
        if response.status_code != 200:
            return jsonify({"error": "لا يمكن الوصول للموقع حالياً"}), 502
            
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')

        # 1. استخراج الوصف
        desc = "الوصف غير متوفر حالياً."
        desc_div = soup.find('div', id='perfume-description-content')
        if desc_div and desc_div.find('p'):
            desc = desc_div.find('p').get_text(strip=True)

        # 2. استخراج النوتات (طريقة محسنة جداً)
        def extract_notes(html_content, label):
            found_notes = []
            if label in html_content:
                # نأخذ المقطع الذي يلي العنوان (Top, Middle, Base)
                segment = html_content.split(label)[1][:6000] 
                # البحث عن أي نمط يحتوي على صورة واسم نوتة
                pattern = r'src="([^"]+)".*?pyramid-note-label[^>]*>\s*([^<]+)\s*</span>'
                matches = re.findall(pattern, segment, re.DOTALL | re.IGNORECASE)
                for img, name in matches:
                    found_notes.append({
                        'name': name.strip(),
                        'image': img.strip()
                    })
            return found_notes

        return jsonify({
            "status": "success",
            "description": desc,
            "notes": {
                "top": extract_notes(html, 'Top Notes'),
                "middle": extract_notes(html, 'Middle Notes'),
                "base": extract_notes(html, 'Base Notes')
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
