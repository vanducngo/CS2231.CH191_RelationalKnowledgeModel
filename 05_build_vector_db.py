import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import os
from kg_connector import KGConnector # Import lớp kết nối của bạn

# --- Cấu hình ---
MODEL_NAME = 'all-MiniLM-L6-v2' 
FAISS_INDEX_PATH = "faiss_index.bin"
LAW_IDS_PATH = "law_ids.json"

def build_vector_database_from_kg():
    """
    Kết nối đến Neo4j qua KGConnector, lấy dữ liệu các điều luật,
    tạo vector embedding, xây dựng index FAISS và lưu kết quả.
    """
    
    # --- Bước 1: Kết nối và lấy dữ liệu từ Knowledge Graph ---
    print("Đang khởi tạo kết nối đến Knowledge Graph...")
    kg = None
    try:
        kg = KGConnector()
        # Gọi hàm đã được xác thực là hoạt động đúng
        all_laws = kg.get_all_laws_for_vectordb() 
    except Exception as e:
        print(f"Lỗi khi kết nối hoặc lấy dữ liệu từ Neo4j: {e}")
        if kg: kg.close()
        return
    finally:
        if kg: kg.close()

    if not all_laws:
        print("Không có dữ liệu luật nào được trả về từ KG. Dừng quá trình.")
        return

    print(f"Đã lấy thành công {len(all_laws)} điều luật từ KG.")

    # Tách riêng ID và nội dung
    law_ids = [law['id'] for law in all_laws]
    contents = [law.get('content', '') for law in all_laws] # Dùng .get() để an toàn hơn

    # --- Bước 2: Tải mô hình và tạo Embeddings ---
    print(f"Đang tải mô hình embedding: '{MODEL_NAME}'...")
    model = SentenceTransformer(MODEL_NAME)

    print("Bắt đầu tạo vector embeddings...")
    embeddings = model.encode(contents, show_progress_bar=True, convert_to_numpy=True)
    print(f"Đã tạo thành công {len(embeddings)} vector với chiều là {embeddings.shape[1]}.")

    # --- Bước 3 & 4: Xây dựng và Lưu Index FAISS và IDs ---
    print("Đang xây dựng và lưu FAISS index...")
    d = embeddings.shape[1] 
    index = faiss.IndexFlatL2(d)
    index.add(embeddings.astype('float32'))
    
    faiss.write_index(index, FAISS_INDEX_PATH)
    print(f"Đã lưu FAISS index vào file: '{FAISS_INDEX_PATH}'")

    with open(LAW_IDS_PATH, 'w', encoding='utf-8') as f:
        json.dump(law_ids, f)
    print(f"Đã lưu danh sách ID điều luật vào file: '{LAW_IDS_PATH}'")
    
    print("\n--- Hoàn thành xây dựng Vector Database! ---")

if __name__ == "__main__":
    build_vector_database_from_kg()