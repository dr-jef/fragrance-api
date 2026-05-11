from flask import Flask, request, jsonify
from flask_cors import CORS
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
        # استخدام AllOrigins بنمط RAW
        proxy_url = f"https://api.allorigins.win/raw?url={requests.utils.quote(target_url)}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        # محاولة جلب البيانات بمهلة زمنية محددة
        response = requests.get(proxy_url, headers=headers, timeout=25)
        html = response.text

        # 1. استخراج الوصف عبر Regex (أسرع من BS4)
        desc = "الوصف غير متوفر."
        desc_match = re.search(r'property="og:description" content="([^"]+)"', html)
        if desc_match:
            desc = desc_match.group(1)

        # 2. استخراج النوتات (المسح الشامل للصور والأسماء)
        # هذا النمط يبحث عن صور النوتات والاسم الذي يليها مباشرة في الكود
        note_pattern = r'src="([^"]+nnotes[^"]+)".*?pyramid-note-label[^>]*>\s*([^<]+)\s*</span>'
        all_notes = []
        matches = re.findall(note_pattern, html, re.DOTALL | re.IGNORECASE)
        
        for img, name in matches:
            all_notes.append({"name": name.strip(), "image": img.strip()})

        # توزيع النوتات لضمان العرض في الواجهة
        return jsonify({
            "status": "success",
            "description": desc,
            "notes": {
                "top": all_notes[:4],
                "middle": all_notes[4:8],
                "base": all_notes[8:]
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
