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
        # استخدام AllOrigins بنمط RAW لجلب محتوى الصفحة كما هو
        proxy_url = f"https://api.allorigins.win/raw?url={requests.utils.quote(target_url)}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        response = requests.get(proxy_url, headers=headers, timeout=30)
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')

        # 1. استخراج الوصف (نفس منطق Colab)
        desc = ""
        desc_div = soup.find('div', id='perfume-description-content')
        if desc_div:
            paragraphs = desc_div.find_all('p')
            desc = " ".join([p.get_text() for p in paragraphs])
        
        if not desc:
            desc = "الوصف غير متوفر لهذا العطر."

        # 2. استخراج النوتات (المنطق الذي نجح في Colab)
        def get_notes_by_section(label_text):
            found_notes = []
            # البحث عن النص (Top Notes, Middle Notes, Base Notes)
            target = soup.find(string=re.compile(label_text, re.I))
            if target:
                # نتحرك للعثور على أقرب حاوية تحتوي على النوتات
                parent = target.find_parent(['div', 'b'])
                if parent:
                    # البحث عن كل النوتات التي تلي هذا العنوان حتى نصل للعنوان التالي
                    next_elements = parent.find_next_siblings()
                    for element in next_elements:
                        # إذا وصلنا لعنوان قسم جديد، نتوقف
                        if element.name in ['b', 'h3', 'h4'] or (element.get_text() and "Notes" in element.get_text() and element.get_text() != label_text):
                            break
                        
                        # استخراج الصور والأسماء داخل هذا القسم
                        note_links = element.find_all('div', style=re.compile("display: flex|grid")) # مرونة في البحث
                        # طريقة بديلة: البحث عن الصور التي تحتوي على nnotes
                        imgs = element.find_all('img', src=re.compile("nnotes"))
                        for img in imgs:
                            name_span = img.find_next('span', class_=re.compile("pyramid-note-label"))
                            if name_span:
                                found_notes.append({
                                    "name": name_span.get_text(strip=True),
                                    "image": img.get('src')
                                })
            return found_notes

        # محاولة أخيرة إذا فشلت الطريقة الأولى (المنطق البديل)
        top = get_notes_by_section("Top Notes")
        middle = get_notes_by_section("Middle Notes")
        base = get_notes_by_section("Base Notes")

        # إذا كانت النوتات لا تزال فارغة، نستخدم Regex المباشر على الـ HTML الخام
        if not top and not middle and not base:
            # هذا الجزء هو الأقوى في استخراج البيانات إذا فشل الـ Soup
            all_matches = re.findall(r'src="([^"]+nnotes[^"]+)".*?pyramid-note-label[^>]*>\s*([^<]+)\s*</span>', html, re.DOTALL)
            # تقسيمها يدوياً (أول 1-3 نوتات افتتاحية، إلخ) أو وضعها في قائمة واحدة
            if all_matches:
                top = [{"name": m[1].strip(), "image": m[0]} for m in all_matches[:3]]
                middle = [{"name": m[1].strip(), "image": m[0]} for m in all_matches[3:6]]
                base = [{"name": m[1].strip(), "image": m[0]} for m in all_matches[6:]]

        return jsonify({
            "status": "success",
            "description": desc,
            "notes": {
                "top": top,
                "middle": middle,
                "base": base
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
