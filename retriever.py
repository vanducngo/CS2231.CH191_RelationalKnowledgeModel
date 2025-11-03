import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# --- Cấu hình (phải khớp với file build_vector_db.py) ---
MODEL_NAME = 'all-MiniLM-L6-v2'
FAISS_INDEX_PATH = "faiss_index.bin"
LAW_IDS_PATH = "law_ids.json"

class SemanticRetriever:
    """
    Lớp để tải index và thực hiện tìm kiếm ngữ nghĩa.
    """
    def __init__(self):
        print("Đang tải Semantic Retriever...")
        try:
            # Tải mô hình embedding
            self.model = SentenceTransformer(MODEL_NAME)
            print(" - Tải mô hình thành công.")

            # Tải FAISS index
            self.index = faiss.read_index(FAISS_INDEX_PATH)
            print(f" - Tải FAISS index thành công. Chứa {self.index.ntotal} vector.")

            # Tải danh sách ID
            with open(LAW_IDS_PATH, 'r', encoding='utf-8') as f:
                self.law_ids = json.load(f)
            print(f" - Tải danh sách ID thành công. Chứa {len(self.law_ids)} ID.")

            if self.index.ntotal != len(self.law_ids):
                print("CẢNH BÁO: Số lượng vector trong index và số lượng ID không khớp!")

            print("Semantic Retriever đã sẵn sàng.")
        except Exception as e:
            print(f"Lỗi khi khởi tạo SemanticRetriever: {e}")
            self.model = None
            self.index = None
            self.law_ids = None

    def search(self, query: str, top_k: int = 5):
        """
        Thực hiện tìm kiếm ngữ nghĩa.
        Input: câu hỏi của người dùng.
        Output: danh sách các ID điều luật liên quan nhất.
        """
        if not self.model or not self.index or not self.law_ids:
            print("Retriever chưa được khởi tạo đúng cách.")
            return []

        # Chuyển câu hỏi thành vector
        query_vector = self.model.encode([query])
        
        # Tìm kiếm trong index
        # faiss trả về (distances, indices)
        distances, indices = self.index.search(query_vector.astype('float32'), top_k)
        
        # Lấy ra các ID tương ứng từ danh sách
        results = [self.law_ids[i] for i in indices[0]]
        
        return results

# --- Ví dụ sử dụng và kiểm tra ---
if __name__ == '__main__':
    # Khởi tạo retriever (chỉ cần làm một lần khi ứng dụng khởi động)
    retriever = SemanticRetriever()
    
    if retriever.index:
        print("\n--- Bắt đầu kiểm tra tìm kiếm ---")
        
        test_query_1 = "hạn mức nhận chuyển nhượng đất nông nghiệp của hộ gia đình là bao nhiêu?"
        print(f"\nCâu hỏi test 1: '{test_query_1}'")
        results_1 = retriever.search(test_query_1, top_k=3)
        print("Kết quả (IDs):", results_1)

        test_query_2 = "khi nào thì nhà nước thu hồi đất do vi phạm pháp luật?"
        print(f"\nCâu hỏi test 2: '{test_query_2}'")
        results_2 = retriever.search(test_query_2, top_k=3)
        print("Kết quả (IDs):", results_2)