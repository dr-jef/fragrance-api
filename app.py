from flask import Flask, request, jsonify
from flask_cors import CORS
import cloudscraper
from bs4 import BeautifulSoup
import re
import os

app = Flask(__name__)
CORS(app) # للسماح بالاتصال من واجهة موقعك الأمامية

@app.route('/scrape', methods=['GET'])
def scrape_fragrantica():
    url = request.args.get('url')
    
    if not url or 'fragrantica.com/perfume/' not in url:
        return jsonify({"error": "رابط غير صالح"}), 400

    try:
        print(f"جاري جلب البيانات من: {url}")
        
        # إنشاء المتصفح الوهمي لتجاوز Cloudflare
        scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
        )
        
        response = scraper.get(url, timeout=20)
        
        if response.status_code != 200 or 'Checking your browser' in response.text:
            return jsonify({"error": f"فشل تجاوز الحماية. كود الخطأ: {response.status_code}"}), 403
            
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')

        # --- 1. استخراج الوصف ---
        desc = "لا يوجد وصف متاح"
        desc_div = soup.find('div', id='perfume-description-content')
        if desc_div:
            p_tag = desc_div.find('p')
            if p_tag:
                desc = p_tag.get_text(strip=True)

        # --- 2. دالة استخراج النوتات ---
        def get_notes(html_text, level_name):
            notes = []
            parts = html_text.split(level_name)
            if len(parts) > 1:
                block = parts[1][:3000]
                pattern = r'<a[^>]*pyramid-note-link[^>]*>.*?<img[^>]*src="([^"]+)".*?<span[^>]*pyramid-note-label[^>]*>\s*([^<]+)\s*<\/span>'
                matches = re.findall(pattern, block, re.IGNORECASE | re.DOTALL)
                
                for img, name in matches:
                    notes.append({'name': name.strip(), 'image': img.strip()})
            return notes

        result = {
            "description": desc,
            "notes": {
                "top": get_notes(html, 'Top Notes'),
                "middle": get_notes(html, 'Middle Notes'),
                "base": get_notes(html, 'Base Notes')
            }
        }
        
        print("تم استخراج البيانات بنجاح!")
        return jsonify(result), 200

    except Exception as e:
        print(f"حدث خطأ: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # تهيئة السيرفر ليعمل على المنصات السحابية (Render)
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)