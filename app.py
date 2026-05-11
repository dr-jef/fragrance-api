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
        # استخدام AllOrigins بنمط RAW لسرعة الاستجابة
        proxy_url = f"https://api.allorigins.win/raw?url={requests.utils.quote(target_url)}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        response = requests.get(proxy_url, headers=headers, timeout=30)
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')

        # --- 1. استخراج الوصف (طريقة هجينة) ---
        desc_text = ""
        # محاولة أ: البحث عن طريق الـ ID الشهير
        desc_div = soup.find('div', id='perfume-description-content')
        if desc_div:
            desc_text = desc_div.get_text(" ", strip=True)
        
        # محاولة ب: إذا فشلت أ، نبحث عن الفقرة التي تحتوي على كلمة "launched" أو اسم البراند
        if not desc_text:
            all_p = soup.find_all('p')
            for p in all_p:
                txt = p.get_text()
                if "launched in" in txt or "was launched" in txt:
                    desc_text = txt.strip()
                    break

        # تنظيف النص النهائي
        desc_final = re.sub(r'\s+', ' ', desc_text).strip() if desc_text else "تعذر استخراج الوصف، جرب رابطاً آخر."

        # --- 2. استخراج النوتات (منطق Colab المطور) ---
        def extract_notes_by_type(section_label):
            found = []
            # البحث عن العنوان (Top Notes, etc)
            label_node = soup.find(string=re.compile(section_label, re.I))
            if label_node:
                # التحرك للأمام في الكود للعثور على الصور
                current = label_node.parent
                for _ in range(5): # البحث في الـ 5 عناصر التالية
                    if current:
                        imgs = current.find_all('img', src=re.compile(r'nnotes|ingredients'))
                        for img in imgs:
                            # البحث عن اسم النوتة الذي يكون عادة في span بجانب الصورة
                            parent_div = img.find_parent('div')
                            name = ""
                            if parent_div:
                                name_node = parent_div.find('span') or parent_div.find('b')
                                name = name_node.get_text(strip=True) if name_node else "N/A"
                            
                            if name and name != "N/A":
                                found.append({"name": name, "image": img.get('src')})
                        current = current.next_sibling
            return found

        # محاولة استخراج النوتات
        notes_data = {
            "top": extract_notes_by_type("Top Notes"),
            "middle": extract_notes_by_type("Middle Notes"),
            "base": extract_notes_by_type("Base Notes")
        }

        # إذا كانت النوتات لا تزال فارغة، نستخدم Regex القوي كحل أخير
        if not any(notes_data.values()):
            regex_matches = re.findall(r'src="([^"]+nnotes[^"]+)".*?>\s*([^<]+)\s*</span>', html, re.I)
            if regex_matches:
                notes_data["top"] = [{"name": m[1].strip(), "image": m[0]} for m in regex_matches]

        return jsonify({
            "status": "success",
            "description": desc_final,
            "notes": notes_data
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
