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

    try:
        # استخدام جسر AllOrigins الخام لتجاوز الحظر
        proxy_url = f"https://api.allorigins.win/raw?url={requests.utils.quote(target_url)}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(proxy_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            return jsonify({"error": "Bridge error"}), 502
            
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')

        # استخراج الوصف
        desc = "الوصف غير متوفر حالياً."
        desc_div = soup.find('div', id='perfume-description-content')
        if desc_div and desc_div.find('p'):
            desc = desc_div.find('p').get_text(strip=True)

        # دالة محسنة جداً لاستخراج النوتات
        def extract_notes(html_content, label):
            found_notes = []
            if label in html_content:
                try:
                    segment = html_content.split(label)[1].split('</div>')[0]
                    # البحث عن الصور والأسماء داخل هذا القسم
                    pattern = r'src="([^"]+)".*?>\s*([^<]+)\s*</span>'
                    matches = re.findall(pattern, segment, re.DOTALL)
                    for img, name in matches:
                        if "nnotes" in img: # التأكد أنها صورة نوتة
                            found_notes.append({'name': name.strip(), 'image': img.strip()})
                except: pass
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
