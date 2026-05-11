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
        return jsonify({"error": "URL missing"}), 400

    try:
        # استخدام AllOrigins بنمط RAW لسرعة الاستجابة
        proxy_url = f"https://api.allorigins.win/raw?url={requests.utils.quote(target_url)}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        response = requests.get(proxy_url, headers=headers, timeout=30)
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')

        # 1. استخراج الوصف بشكل نصي صافي (لحل مشكلة object Object)
        desc_text = "الوصف غير متوفر حالياً."
        desc_div = soup.find('div', id='perfume-description-content')
        if desc_div:
            # نأخذ أول فقرتين فقط لضمان النظافة
            p_tags = desc_div.find_all('p')
            if p_tags:
                desc_text = " ".join([p.get_text(strip=True) for p in p_tags[:2]])

        # 2. دالة استخراج النوتات (منطق Colab المطور)
        def get_notes(html_str, section_name):
            notes_list = []
            if section_name in html_str:
                # نأخذ المقطع الذي يلي العنوان
                parts = html_str.split(section_name)
                segment = parts[1][:5000] # نطاق بحث واسع
                # البحث عن رابط الصورة والاسم المصاحب له
                matches = re.findall(r'src="([^"]+nnotes[^"]+)".*?pyramid-note-label[^>]*>\s*([^<]+)\s*</span>', segment, re.DOTALL | re.IGNORECASE)
                for img, name in matches:
                    notes_list.append({
                        "name": name.strip(),
                        "image": img.strip()
                    })
            return notes_list

        return jsonify({
            "status": "success",
            "description": str(desc_text), # نضمن أنه String
            "notes": {
                "top": get_notes(html, 'Top Notes'),
                "middle": get_notes(html, 'Middle Notes'),
                "base": get_notes(html, 'Base Notes')
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
