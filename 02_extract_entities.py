import os
import re
import json
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from llm_callers import call_gemini_api as call_llm

def get_extraction_prompt(law_year, article_code, article_content):
    # Prompt 1 chi tiết
    return f"""
    Bạn là một trợ lý pháp lý chuyên nghiệp, thực hiện nhiệm vụ trích xuất thông tin có cấu trúc để xây dựng Đồ thị Tri thức. Với nội dung của Điều luật dưới đây, hãy trích xuất các thực thể và mối quan hệ theo cấu trúc JSON định sẵn.

    **QUY TẮC BẮT BUỘC:**

    1.  **ĐỊNH DANH (ID):**
        *   Sử dụng định dạng `[loại]_[tên_không_dấu_viết_liền]`.
        *   Ví dụ cho Khái niệm "Người sử dụng đất" -> ID là `khainiem_nguoisudungdat`.
        *   Ví dụ cho Chủ thể "Hộ gia đình" -> ID là `chuthe_hogiadinh`.
        *   **Với Điều Luật, ID phải là `dieu_[số hiệu]_[năm luật]`. Ví dụ: `dieu_4_2024`.**

    2.  **PHÂN LOẠI THỰC THỂ (LABEL):**
        *   Chỉ được phép sử dụng các label sau: `DieuLuat`, `KhaiNiem`, `ChuThe`, `HanhViPhapLy`, `CheTai`, `DieuKien`.
        *   Phân loại một cách chính xác nhất có thể.

    3.  **THUỘC TÍNH (PROPERTIES):**
        *   Tất cả các thuộc tính phải nằm trong một object JSON con có tên là "properties".
        *   Mỗi thực thể phải có thuộc tính `name` chứa tên đầy đủ, có dấu.
        *   **CHỈ nút có label `DieuLuat` mới được có thuộc tính `noi_dung` chứa toàn bộ văn bản của điều luật.** Các loại nút khác TUYỆT ĐỐI KHÔNG được có thuộc tính này.
        *   Nút có label `DieuLuat` cũng phải có thuộc tính `ma_dieu` và `phien_ban`.

    4.  **QUAN HỆ (RELATIONSHIPS):**
        *   Mỗi quan hệ phải có `source_id` và `target_id` tương ứng với các ID đã được định nghĩa trong phần `entities`.
        *   Chỉ được phép sử dụng các loại quan hệ sau: `QUY_DINH_VE`, `AP_DUNG_CHO`, `DAN_DEN`, `YEU_CAU`, `DINH_NGHIA`.

    ---
    **VÍ DỤ MẪU:**
    Nếu Điều luật là "Điều 5. Người sử dụng đất gồm hộ gia đình...", output phải tương tự:
    ```json
    {{
    "entities": [
        {{ "id": "dieu_5_2013", "label": "DieuLuat", "properties": {{ "name": "Người sử dụng đất", "ma_dieu": "5", "phien_ban": 2013, "noi_dung": "Người sử dụng đất được giao đất, cho thuê đất..." }} }},
        {{ "id": "chuthe_hogiadinh", "label": "ChuThe", "properties": {{ "name": "Hộ gia đình" }} }}
    ],
    "relationships": [
        {{ "source_id": "dieu_5_2013", "target_id": "chuthe_hogiadinh", "relationship_type": "QUY_DINH_VE" }}
    ]
    }}

    VĂN BẢN NGUỒN CẦN XỬ LÝ:
    Tên Luật: Luật Đất đai {law_year}
    Mã Điều: {article_code}
    Nội dung:
    {article_content}
    JSON OUTPUT (Tuân thủ nghiêm ngặt các quy tắc trên):
    """

def process_single_file(filename, year, input_dir, output_dir):
    """Hàm này xử lý một file duy nhất, được gọi bởi các luồng."""
    output_path = os.path.join(output_dir, filename.replace('.txt', '.json'))
    
    if os.path.exists(output_path):
        return f"Đã xử lý: Bỏ qua: {filename}"
        
    input_path = os.path.join(input_dir, filename)
    
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    article_code_match = re.search(r'dieu_(\d+)_', filename)
    if not article_code_match:
        return f"Lỗi tên file: {filename}"
    article_code = article_code_match.group(1)

    prompt = get_extraction_prompt(year, article_code, content)
    
    try:
        response_text = call_llm(prompt)
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
        json_str = json_match.group(1) if json_match else response_text

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json.loads(json_str), f, ensure_ascii=False, indent=2)
        return f"Thành công: {filename}"
            
    except Exception as e:
        return f"Lỗi: {filename} - {e}"

def process_law_year_parallel(year, input_dir, output_dir, max_workers=5):
    """Hàm xử lý song song."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    file_list = [f for f in os.listdir(input_dir) if f.endswith('.txt')]
    print(f"\n--- Bắt đầu trích xuất song song cho Luật {year} ({len(file_list)} điều) ---")

    # Sử dụng ThreadPoolExecutor để xử lý song song
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Tạo các task
        futures = {executor.submit(process_single_file, filename, year, input_dir, output_dir): filename for filename in file_list}
        
        # Dùng tqdm để theo dõi tiến trình
        for future in tqdm(as_completed(futures), total=len(file_list), desc=f"Luật {year}"):
            result = future.result()
            # Bạn có thể in kết quả nếu muốn, nhưng nó sẽ làm chậm thanh tiến trình
            print(result)
            pass

def main():
    # max_workers là số lượng yêu cầu bạn muốn gửi đi cùng lúc.
    # Con số này phụ thuộc vào giới hạn RPM của bạn. Nếu RPM=60, bạn có thể đặt max_workers=10 hoặc 20.
    # Bắt đầu với một con số nhỏ như 5 để an toàn.
    process_law_year_parallel(2024, 'chunks_2024', 'output_json_2024', max_workers=5)
    process_law_year_parallel(2013, 'chunks_2013', 'output_json_2013', max_workers=5)
    print("\n--- Hoàn thành trích xuất thực thể! ---")

if __name__ == "__main__":
    main()