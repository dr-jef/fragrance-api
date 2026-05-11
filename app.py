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
        # استخدام البروكسي بنمط RAW لجلب محتوى الصفحة الحقيقي
        proxy_url = f"https://api.allorigins.win/raw?url={requests.utils.quote(target_url)}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(proxy_url, headers=headers, timeout=30)
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')

        # --- 1. البحث عن الوصف (طريقة الرادار) ---
        # سنبحث عن أي فقرة تحتوي على كلمات "عطرية" شهيرة
        desc = "الوصف غير متوفر حالياً."
        keywords = ["launched in", "was launched", "top note", "fragrance for"]
        for p in soup.find_all('p'):
            p_text = p.get_text().lower()
            if any(key in p_text for key in keywords):
                desc = p.get_text(strip=True)
                break

        # --- 2. البحث عن النوتات (طريقة المسح الشامل) ---
        # سنقوم بسحب كل الصور التي تتبع نمط نوتات Fragrantica (تسمى nnotes)
        all_notes = []
        # هذا الـ Regex يبحث عن الصور التي تحتوي مسار نوتات ويستخرج النص الذي يليها مباشرة
        note_matches = re.findall(r'src="([^"]+nnotes[^"]+)".*?pyramid-note-label[^>]*>\s*([^<]+)\s*</span>', html, re.I | re.S)
        
        for img, name in note_matches:
            all_notes.append({"name": name.strip(), "image": img.strip()})

        # توزيع النوتات يدوياً (أول 3 إفتتاحية، ثم 3 قلب، ثم الباقي قاعدة) لضمان العرض
        # لأن الموقع يغير تقسيم الأقسام (Top, Middle, Base) في الكود
        notes_data = {
            "top": all_notes[:3] if len(all_notes) > 0 else [],
            "middle": all_notes[3:6] if len(all_notes) > 3 else [],
            "base": all_notes[6:] if len(all_notes) > 6 else []
        }

        return jsonify({
            "status": "success",
            "description": desc,
            "notes": notes_data,
            "raw_count": len(all_notes) # للتأكد من عدد النوتات المكتشفة
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
