# **Trợ lý Pháp lý Thông minh về Luật Đất đai (2013 & 2024)**

Dự án này là một hệ thống Hỏi-Đáp và So sánh thông minh, được xây dựng nhằm cung cấp các câu trả lời chính xác và có căn cứ về hai phiên bản Luật Đất đai 2013 và 2024 của Việt Nam.

Hệ thống sử dụng kiến trúc RAG (Retrieval-Augmented Generation) nâng cao, kết hợp sức mạnh của Đồ thị Tri thức (Knowledge Graph - Neo4j), Tìm kiếm Ngữ nghĩa (Semantic Search - FAISS), và các Mô hình Ngôn ngữ Lớn (Large Language Models - LLMs).

## **Tính năng chính**

*   **Hỏi-Đáp Tình huống:** Trả lời các câu hỏi phức tạp về quyền và nghĩa vụ sử dụng đất, thủ tục hành chính, chế tài...
*   **So sánh Luật:** Tự động đối chiếu và chỉ ra sự khác biệt về một chủ đề cụ thể giữa hai phiên bản luật 2013 và 2024.
*   **Trích dẫn Đáng tin cậy:** Mọi câu trả lời đều đi kèm với trích dẫn Điều/Khoản luật cụ thể làm căn cứ.
*   **Tìm kiếm Thông minh:** Sử dụng kết hợp tìm kiếm ngữ nghĩa và tìm kiếm từ khóa để đảm bảo truy xuất được những thông tin liên quan nhất.

## **Kiến trúc Hệ thống**
1.  **Giao diện người dùng (Streamlit):** Nhận câu hỏi từ người dùng.
2.  **Bộ điều phối (Orchestrator):**
    *   **Phân loại Truy vấn:** Dùng LLM để xác định ý định của người dùng (Hỏi-đáp hay So sánh).
    *   **Truy xuất Kết hợp (Hybrid Retrieval):**
        *   **Semantic Search (FAISS):** Tìm các điều luật liên quan về mặt ngữ nghĩa.
        *   **Keyword Search (Neo4j):** Tìm các điều luật chứa từ khóa chính xác.
        *   **Graph Traversal (Neo4j):** Tìm các cặp so sánh luật (cũ-mới) cho chức năng so sánh.
3.  **Xây dựng Ngữ cảnh (Context Building):** Tập hợp nội dung các điều luật đã truy xuất.
4.  **Bộ sinh Câu trả lời (Generator - LLM):** Dùng LLM (ví dụ: Gemini) để đọc ngữ cảnh và tạo ra câu trả lời cuối cùng kèm trích dẫn.

---

## **Hướng dẫn Cài đặt và Chạy**

Dự án này được khuyến khích cài đặt và chạy trong môi trường **Conda** để đảm bảo tính tương thích của các thư viện khoa học dữ liệu.

### **1. Yêu cầu Cần có**

*   **Conda:** Đã cài đặt [Anaconda](https://www.anaconda.com/download) hoặc [Miniconda](https://docs.conda.io/en/latest/miniconda.html).
*   **Java:** Đã cài đặt [JDK 17](https://adoptium.net/temurin/releases/) để chạy Neo4j.
*   **Neo4j Desktop:** Đã cài đặt và tạo một cơ sở dữ liệu.
*   **API Keys:**
    *   Tạo một file `.env` trong thư mục gốc của project.
    *   Điền các thông tin sau vào file `.env`:
        ```env
        # Google Gemini API Key
        GOOGLE_API_KEY="AIzaSy..."

        # Neo4j Credentials
        NEO4J_URI="bolt://localhost:7687"
        NEO4J_USER="neo4j"
        NEO4J_PASSWORD="your_neo4j_password"
        ```

### **2. Cài đặt Môi trường (Conda)**

Mở Terminal (hoặc Anaconda Prompt trên Windows) và thực hiện các lệnh sau:

**a. Tạo môi trường Conda mới:**
```bash
conda create -n luatdatdai_env python=3.10
conda activate luatdatdai_env
```

**b. Cài đặt các gói chính từ `conda-forge` và `pytorch`:**
Kênh `conda-forge` và `pytorch` cung cấp các phiên bản đã được biên dịch sẵn, ổn định cho các thư viện phức tạp.
```bash
conda install -c pytorch faiss-cpu
conda install -c conda-forge pytorch torchvision torchaudio sentence-transformers numpy pandas
```

**c. Cài đặt các gói còn lại bằng `pip`:**
```bash
pip install python-dotenv PyPDF2 neo4j unidecode streamlit tqdm google-generativeai openai
```

### **3. Chạy Pipeline Xử lý Dữ liệu**

Bạn cần chạy các script sau theo đúng thứ tự để xây dựng cơ sở tri thức. **Các bước này chỉ cần thực hiện một lần.**

**a. Tiền xử lý PDF:**
```bash
python 01_preprocess_pdfs.py
```

**b. Trích xuất thông tin bằng LLM:**
```bash
python 02_extract_entities.py
python 03_extract_comparisons.py
```

**d. Chuyển đổi sang CSV:**
```bash
python 04_2_process_and_transform_to_csv.py
```

**e. Import vào Neo4j:**
1.  Dừng cơ sở dữ liệu trong Neo4j Desktop.
2.  Mở Terminal tại thư mục `bin` của CSDL.
3.  Xóa dữ liệu cũ: `rm -rf ../data/databases/neo4j`
4.  Chạy lệnh import:
    ```bash
    ./neo4j-admin database import full --nodes=../import/nodes_final.csv --relationships=../import/relationships_final.csv --overwrite-destination=true --multiline-fields=true
    ```
5.  Khởi động lại CSDL.

**f. Xây dựng Vector Database:**
```bash
python 05_build_vector_db.py
```

### **4. Chạy Ứng dụng**

Sau khi đã hoàn thành tất cả các bước xử lý dữ liệu ở trên, bạn có thể khởi động ứng dụng Trợ lý Pháp lý.

**a. Chạy ứng dụng Streamlit:**
```bash
streamlit run app.py
```

**b. Mở trình duyệt:** Một tab mới sẽ tự động mở trong trình duyệt của bạn tại địa chỉ `http://localhost:8501`. Bây giờ bạn có thể bắt đầu đặt câu hỏi