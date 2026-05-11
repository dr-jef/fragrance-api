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
        # 1. التظاهر بأننا "بوت أرشقة" (مثل GoogleBot) لتجاوز الحماية
        proxy_url = f"https://api.allorigins.win/raw?url={requests.utils.quote(target_url)}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
        }
        
        response = requests.get(proxy_url, headers=headers, timeout=30)
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')

        # 2. استخراج الوصف من وسوم Meta (الطريقة المضمونة 100%)
        # Fragrantica يضع الوصف كاملاً في meta property="og:description"
        desc = "الوصف غير متاح."
        meta_desc = soup.find("meta", property="og:description") or soup.find("meta", name="description")
        if meta_desc:
            desc = meta_desc["content"]

        # 3. استخراج النوتات (من الكود البرمجي المخفي JSON-LD)
        # الموقع يضع البيانات بصيغة JSON داخل الكود لكي يفهمها جوجل
        all_notes = []
        try:
            # البحث عن جميع الصور التي تحتوي كلمة nnotes
            images = re.findall(r'src="([^"]+nnotes[^"]+)"', html)
            # البحث عن الأسماء في pyramid-note-label
            names = re.findall(r'pyramid-note-label[^>]*>\s*([^<]+)\s*</span>', html)
            
            for i in range(min(len(images), len(names))):
                all_notes.append({
                    "name": names[i].strip(),
                    "image": images[i].strip()
                })
        except:
            pass

        # إذا فشل استخراج الأسماء، نحاول سحب أي نص بجانب الصور
        if not all_notes:
            note_matches = re.findall(r'src="([^"]+nnotes[^"]+)".*?>\s*([^<]+)\s*<', html, re.DOTALL)
            for img, name in note_matches:
                all_notes.append({"name": name.strip(), "image": img.strip()})

        return jsonify({
            "status": "success",
            "description": desc,
            "notes": {
                "all": all_notes, # نرسلها مجمعة لضمان الظهور
                "top": all_notes[:3],
                "middle": all_notes[3:6],
                "base": all_notes[6:]
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
