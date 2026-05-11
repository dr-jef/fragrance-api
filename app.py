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

    if not target_url.startswith('http'):
        target_url = 'https://' + target_url

    try:
        # استخدام AllOrigins بنمط RAW لجلب الصفحة بسرعة وكأنها طلب مباشر
        proxy_url = f"https://api.allorigins.win/raw?url={requests.utils.quote(target_url)}"
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(proxy_url, headers=headers, timeout=25)
        
        if response.status_code != 200:
            return jsonify({"error": f"Bridge error: {response.status_code}"}), 502
            
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')

        # استخراج الوصف
        desc = "لا يوجد وصف متاح لهذا العطر حالياً."
        desc_div = soup.find('div', id='perfume-description-content')
        if desc_div:
            p_tag = desc_div.find('p')
            if p_tag:
                desc = p_tag.get_text(strip=True)

        # استخراج النوتات
        def extract_notes(html_content, label):
            notes = []
            if label in html_content:
                parts = html_content.split(label)
                # نأخذ الجزء بعد كلمة العنوان (Top, Middle, Base)
                sub_html = parts[1].split('</div>')[0] 
                pattern = r'src="([^"]+)".*?pyramid-note-label[^>]*>\s*([^<]+)\s*</span>'
                matches = re.findall(pattern, sub_html, re.DOTALL)
                for img, name in matches:
                    notes.append({'name': name.strip(), 'image': img.strip()})
            return notes

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
