import os
import json
import re
import time
from tqdm import tqdm
# Lựa chọn LLM bạn muốn dùng (bỏ comment dòng tương ứng)
# from llm_callers import call_openai_api as call_llm 
from llm_callers import call_gemini_api as call_llm

def get_extraction_prompt(law_year, article_code, article_content):
    # Prompt 1 chi tiết
    return f"""
Bạn là một trợ lý pháp lý chuyên nghiệp với nhiệm vụ xây dựng một Đồ thị Tri thức (Knowledge Graph) từ văn bản luật. Với nội dung của Điều luật được cung cấp dưới đây, hãy trích xuất tất cả các thực thể và mối quan hệ giữa chúng theo một cấu trúc JSON định sẵn.

**QUY TẮC TRÍCH XUẤT:**

1.  **Định danh (ID):** Tạo một ID duy nhất cho mỗi thực thể, theo quy tắc: `[loại]_[tên_không_dấu]`. Ví dụ: `chuthe_canhan`, `hanhvi_chuyennhuong`. Với ĐiềuLuật, ID là `dieu_{article_code}`.
2.  **Phân loại Thực thể:** Chỉ sử dụng các loại (labels) sau: `ĐiềuLuật`, `KháiNiệm`, `ChủThể`, `HànhViPhápLý`, `ChếTài`, `ĐiềuKiện`.
3.  **Quan hệ:** Mô tả các mối quan hệ tìm thấy dưới dạng một mảng các object. Mỗi object gồm `source_id`, `relationship_type`, và `target_id`.
4.  **Các loại quan hệ được phép:** Chỉ sử dụng các loại sau: `ĐỊNH_NGHĨA`, `QUY_ĐỊNH_VỀ`, `ÁP_DỤNG_CHO`, `DẪN_ĐẾN`, `YÊU_CẦU`.

---

**VĂN BẢN NGUỒN:**

*   **Tên Luật:** Luật Đất đai {law_year}
*   **Mã Điều:** {article_code}
*   **Nội dung:**
    {article_content}

---

**OUTPUT DƯỚI DẠNG JSON (Không thêm bất kỳ giải thích nào khác):**
"""

def process_law_year(year, input_dir, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    file_list = [f for f in os.listdir(input_dir) if f.endswith('.txt')]
    
    print(f"\n--- Bắt đầu trích xuất cho Luật {year} ({len(file_list)} điều) ---")
    
    for filename in tqdm(file_list, desc=f"Luật {year}"):
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename.replace('.txt', '.json'))
        
        # Bỏ qua nếu đã xử lý
        if os.path.exists(output_path):
            continue
            
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        article_code_match = re.search(r'dieu_(\d+)_', filename)
        if not article_code_match:
            continue
        article_code = article_code_match.group(1)

        prompt = get_extraction_prompt(year, article_code, content)
        
        try:
            # Gọi API và xử lý kết quả
            response_text = call_llm(prompt)
            # Tách phần JSON ra khỏi markdown code block nếu có
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response_text

            # Lưu file json
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(json.loads(json_str), f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"Lỗi khi xử lý file {filename}: {e}")
        
        # Tạm dừng để tránh rate limit của API
        time.sleep(1) 

def main():
    process_law_year(2024, 'chunks_2024', 'output_json_2024')
    process_law_year(2013, 'chunks_2013', 'output_json_2013')
    print("\n--- Hoàn thành trích xuất thực thể! ---")

if __name__ == "__main__":
    main()

# ----- File helper: llm_callers.py -----
# (Bạn cần tạo file này để chứa các hàm gọi API)
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

def call_gemini_api(prompt):
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content(prompt)
    return response.text

# Bạn cũng có thể thêm hàm call_openai_api tương tự nếu muốn
# import openai
# def call_openai_api(prompt):
#     openai.api_key = os.getenv("OPENAI_API_KEY")
#     response = openai.Completion.create(engine="text-davinci-003", prompt=prompt, max_tokens=1500)
#     return response.choices[0].text.strip()