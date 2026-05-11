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
        # 1. التظاهر بهوية متصفح حقيقي + Googlebot لتجاوز الحماية
        proxy_url = f"https://api.allorigins.win/raw?url={requests.utils.quote(target_url)}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        
        response = requests.get(proxy_url, headers=headers, timeout=30)
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')

        # 2. استخراج الوصف من Meta Tags (الذي نجحنا فيه)
        desc = "الوصف غير متاح."
        meta_desc = soup.find("meta", property="og:description") or soup.find("meta", name="description")
        if meta_desc:
            desc = meta_desc["content"]

        # 3. دالة استخراج النوتات (المسح الذكي)
        def get_notes_from_pyramid(section_name):
            notes_list = []
            # البحث عن العنوان النصي في الصفحة
            label = soup.find(string=re.compile(section_name, re.I))
            if label:
                # العثور على الحاوية الأقرب التي تضم الصور والأسماء
                parent_container = label.find_parent(['div', 'b']).find_next_sibling()
                if parent_container:
                    # استخراج كل النوتات داخل هذا القسم
                    items = parent_container.find_all('div', recursive=True)
                    for item in items:
                        img_tag = item.find('img')
                        label_tag = item.find(class_=re.compile("pyramid-note-label|note-label", re.I))
                        
                        if img_tag and label_tag:
                            img_url = img_tag.get('src')
                            if "nnotes" in img_url or "ingredients" in img_url:
                                notes_list.append({
                                    "name": label_tag.get_text(strip=True),
                                    "image": img_url
                                })
            return notes_list

        # تنفيذ المسح للأقسام الثلاثة
        final_notes = {
            "top": get_notes_from_pyramid("Top Notes"),
            "middle": get_notes_from_pyramid("Middle Notes"),
            "base": get_notes_from_pyramid("Base Notes")
        }

        # حل احتياطي (Backup Plan): إذا كانت الأقسام فارغة، نسحب كل الصور التي تتبع نمط النوتات
        if not any(final_notes.values()):
            backup_matches = re.findall(r'src="([^"]+nnotes[^"]+)".*?>\s*([^<]+)\s*</span>', html, re.DOTALL | re.I)
            if backup_matches:
                # نضعها كلها في قسم الـ Top كبداية لكي تظهر للمستخدم
                final_notes["top"] = [{"name": m[1].strip(), "image": m[0]} for m in backup_matches]

        return jsonify({
            "status": "success",
            "description": str(desc),
            "notes": final_notes
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
