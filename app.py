import streamlit as st
from kg_connector import KGConnector
from semantic_retriever import SemanticRetriever
from reranker import Reranker
from llm_callers import call_gemini_api # Giả sử đây là hàm gọi API của bạn
import json
import re

def clean_query(query: str) -> str:
    """
    Hàm làm sạch câu hỏi của người dùng trước khi xử lý.
    - Chuyển về chữ thường
    - Loại bỏ các ký tự đặc biệt, dấu câu thừa
    - Loại bỏ các từ kích hoạt phổ biến (trigger words)
    """
    if not isinstance(query, str):
        return ""
    
    # Chuyển về chữ thường
    cleaned = query.lower()
    
    # Loại bỏ các từ kích hoạt phổ biến và dấu câu đi kèm
    trigger_words = [
        "ok google", "hey siri", "alexa", 
        "cho tôi hỏi", "cho mình hỏi", "giúp tôi với", 
        "giải thích", "định nghĩa", "là gì",
        "[help]"
    ]
    for word in trigger_words:
        cleaned = cleaned.replace(word, "")
    
    # Loại bỏ các ký tự đặc biệt, chỉ giữ lại chữ, số, và khoảng trắng (tiếng Việt)
    # Regex này giữ lại tất cả các ký tự chữ trong bảng chữ cái tiếng Việt
    cleaned = re.sub(r'[^a-zA-Z0-9àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ\s]', '', cleaned)
    
    # Loại bỏ khoảng trắng thừa
    cleaned = " ".join(cleaned.split())
    
    return cleaned.strip()


# --- KHỞI TẠO CÁC THÀNH PHẦN CỐT LÕI (Sử dụng cache của Streamlit) ---
@st.cache_resource
def initialize_components():
    """
    Khởi tạo và cache lại các đối tượng KGConnector, SemanticRetriever và Reranker.
    Chạy duy nhất một lần khi ứng dụng khởi động.
    """
    print("--- Đang khởi tạo các thành phần cốt lõi (chỉ chạy một lần) ---")
    try:
        kg = KGConnector()
        retriever = SemanticRetriever()
        reranker = Reranker()
        print("--- Khởi tạo hoàn tất ---")
        return kg, retriever, reranker
    except Exception as e:
        # Nếu bất kỳ thành phần nào lỗi, ném ngoại lệ để dừng ứng dụng
        raise RuntimeError(f"Lỗi khởi tạo thành phần cốt lõi: {e}")

# Tải các component và xử lý lỗi ngay từ đầu
try:
    kg_connector, semantic_retriever, reranker = initialize_components()
except RuntimeError as e:
    st.error(f"Không thể khởi động ứng dụng. {e}")
    st.stop()


# --- XÂY DỰNG PIPELINE TRUY XUẤT (RETRIEVAL) ---
def retrieval_pipeline(query: str, initial_k: int = 20, final_k: int = 5):
    """
    Thực hiện pipeline truy xuất hoàn chỉnh: Search -> Rerank.
    Đây là logic cốt lõi sẽ được tái sử dụng.
    """
    print(f"\n[PIPELINE] Bắt đầu truy xuất cho câu hỏi: '{query}'")
    
    # --- Giai đoạn 1: Tìm kiếm ứng viên (Candidate Retrieval) ---
    print(f"[PIPELINE] Bước 1: Tìm kiếm ngữ nghĩa để lấy top {initial_k} ứng viên...")
    candidate_results = semantic_retriever.search(query, top_k=initial_k)
    
    if not candidate_results:
        print("[PIPELINE] Không tìm thấy ứng viên nào từ Semantic Search.")
        return []
        
    print(f"[PIPELINE] -> Tìm thấy {len(candidate_results)} ứng viên.")

    # Lấy nội dung chi tiết của các ứng viên từ KG
    candidate_docs = []
    for law_id, semantic_score in candidate_results:
        node_properties = kg_connector.get_node_by_id(law_id)
        if node_properties:
            # Tạo "siêu văn bản" để rerank
            super_content = f"Tên điều luật: {node_properties.get('name', '')}. Nội dung: {node_properties.get('noi_dung', '')}"
            candidate_docs.append({
                'id': law_id,
                'name': node_properties.get('name', ''),
                'phien_ban': node_properties.get('phien_ban', ''),
                'ma_dieu': node_properties.get('ma_dieu', ''),
                'content': super_content,
                'raw_content': node_properties.get('noi_dung', ''), # Giữ lại nội dung gốc
                'semantic_score': semantic_score
            })

    # --- Giai đoạn 2: Sắp xếp lại (Reranking) ---
    print(f"[PIPELINE] Bước 2: Sắp xếp lại {len(candidate_docs)} ứng viên bằng Cross-Encoder...")
    reranked_docs = reranker.rerank(query, candidate_docs)

    # Lấy top-k kết quả cuối cùng
    final_results = reranked_docs[:final_k]
    
    print("[PIPELINE] -> Hoàn thành truy xuất và reranking.")
    return final_results


# --- CÁC HÀM TẠO PROMPT ---
def build_qa_prompt(query, context):
    """Xây dựng prompt cho chức năng Hỏi-Đáp với hướng dẫn suy luận chi tiết."""
    return f"""
        Bạn là một trợ lý pháp lý chuyên nghiệp, cẩn thận và thông minh. Nhiệm vụ của bạn là trả lời câu hỏi của người dùng một cách chi tiết và chính xác nhất có thể, chỉ dựa trên NGỮ CẢNH LUẬT được cung cấp.

        **QUY TRÌNH SUY LUẬN BẮT BUỘC (Hãy tư duy từng bước):**

        1.  **Phân tích câu hỏi:** Đọc kỹ câu hỏi để hiểu rõ người dùng đang hỏi về vấn đề gì, chủ thể nào và điều kiện nào.
        2.  **Rà soát ngữ cảnh:** Tìm kiếm tất cả các thông tin, con số, điều kiện liên quan đến câu hỏi trong toàn bộ "NGỮ CẢNH LUẬT".
        3.  **Tổng hợp câu trả lời:** Dựa trên những thông tin tìm được, hãy xây dựng một câu trả lời hoàn chỉnh.
            *   **Nếu ngữ cảnh cung cấp câu trả lời trực tiếp và đầy đủ:** Hãy trả lời thẳng vào vấn đề.
            *   **Nếu ngữ cảnh cung cấp câu trả lời nhưng còn phụ thuộc vào các điều luật khác (thông tin gián tiếp):** Hãy trả lời những gì bạn biết và chỉ rõ thông tin đó phụ thuộc vào điều gì. Ví dụ: "Hạn mức là X lần hạn mức giao đất, theo quy định tại Điều Y...".
            *   **Luôn trích dẫn nguồn:** Với mỗi luận điểm, hãy trích dẫn trực tiếp một đoạn ngắn từ văn bản luật để làm bằng chứng và ghi rõ căn cứ. Ví dụ: "...theo quy định: \"[trích dẫn trực tiếp]\" [Căn cứ: Điều X Luật Y]".
        4.  **Trường hợp cuối cùng:** Nếu sau khi đã phân tích kỹ lưỡng mà không có bất kỳ thông tin nào trong ngữ cảnh có thể trả lời câu hỏi, chỉ được phép trả lời DUY NHẤT câu: "Dựa trên các điều luật được cung cấp, tôi không tìm thấy thông tin chính xác để trả lời cho câu hỏi này."

        --- NGỮ CẢNH LUẬT ---
        {context}
        --- CÂU HỎI ---
        {query}

        --- CÂU TRẢ LỜI CHI TIẾT VÀ CÓ TRÍCH DẪN (Theo đúng quy trình suy luận trên) ---
    """

def build_comparison_prompt(query, context):
    """
    Xây dựng prompt cho chức năng So Sánh, nhấn mạnh vào việc đối chiếu trực tiếp.
    """
    return f"""
        Bạn là một chuyên gia pháp lý đối chiếu văn bản. Nhiệm vụ của bạn là so sánh Luật Đất đai 2013 và 2024 về một chủ đề cụ thể, chỉ dựa trên NGỮ CẢNH LUẬT được cung cấp.

        **QUY TRÌNH ĐỐI CHIẾU NGHIÊM NGẶT:**

        1.  **Xác định cặp Điều luật cốt lõi:** Đọc "YÊU CẦU SO SÁNH" và tìm trong "NGỮ CẢNH LUẬT" **chính xác 2 điều luật** (một của 2013, một của 2024) có tiêu đề hoặc nội dung trực tiếp nhất về chủ đề được hỏi. Ví dụ, nếu hỏi về "người sử dụng đất", hãy tìm Điều luật có tên "Người sử dụng đất".
        2.  **Bắt buộc thừa nhận:** Mở đầu câu trả lời bằng cách xác nhận đã tìm thấy cả hai điều luật. Ví dụ: "Để so sánh về [chủ đề], chúng ta sẽ đối chiếu trực tiếp giữa Điều X Luật 2013 và Điều Y Luật 2024."
        3.  **Đối chiếu song song:**
            *   Trình bày nội dung cốt lõi của điều luật cũ trước. **Phải trích dẫn trực tiếp** và ghi rõ căn cứ.
            *   Trình bày nội dung cốt lõi của điều luật mới sau. **Phải trích dẫn trực tiếp** và ghi rõ căn cứ.
        4.  **Phân tích điểm khác biệt:** Sau khi đã trình bày song song, hãy viết một đoạn "Phân tích các điểm thay đổi chính", liệt kê các khác biệt một cách rõ ràng (ví dụ: loại bỏ đối tượng A, bổ sung đối tượng B, thay đổi thuật ngữ C...).
        5.  **TUYỆT ĐỐI KHÔNG ĐƯỢC** kết luận rằng một bộ luật "không có quy định" nếu trong ngữ cảnh đã cung cấp điều luật tương ứng. Nếu thực sự không tìm thấy điều luật tương ứng trong ngữ cảnh, hãy nêu rõ: "Trong ngữ cảnh được cung cấp, chỉ tìm thấy quy định tại [Điều X Luật Y] về chủ đề này."

        --- NGỮ CẢNH LUẬT ---
        {context}
        --- YÊU CẦU SO SÁNH ---
        {query}

        --- BÀI PHÂN TÍCH SO SÁNH (Theo đúng quy trình đối chiếu trên) ---
    """

# --- THIẾT KẾ GIAO DIỆN NGƯỜI DÙNG ---
st.set_page_config(layout="wide", page_title="Trợ lý Pháp lý Đất đai")

st.title("🏛️ Trợ lý Pháp lý Thông minh về Luật Đất đai")
st.write("Hỏi đáp, tra cứu và so sánh về Luật Đất đai 2013 và 2024.")

# Tạo 2 tab cho 2 chức năng chính
tab1, tab2 = st.tabs(["❓ Hỏi-Đáp & Tra cứu", "⚖️ So sánh Luật"])

# --- XỬ LÝ TAB 1: HỎI-ĐÁP TÌNH HUỐNG ---
with tab1:
    st.header("Đặt câu hỏi hoặc tra cứu theo từ khóa")
    user_query = st.text_input("Nhập câu hỏi của bạn vào đây:", key="qa_input", placeholder="Ví dụ: Hạn mức nhận chuyển nhượng đất nông nghiệp là bao nhiêu?")

    if user_query:
        with st.spinner("🧠 Đang phân tích và tìm kiếm trong cơ sở tri thức..."):
            cleaned_query = clean_query(user_query)
            st.info(f"Đang tìm kiếm cho câu hỏi đã được chuẩn hóa: '{cleaned_query}'") # Hiển thị để debug

            # 1. TRUY XUẤT (RETRIEVE) - SỬ DỤNG PIPELINE HOÀN CHỈNH
            retrieved_docs = retrieval_pipeline(cleaned_query, initial_k=20, final_k=5)
            
            # 2. XÂY DỰNG NGỮ CẢNH (CONTEXT)
            context = ""
            if not retrieved_docs:
                 st.warning("Không tìm thấy điều luật nào có liên quan.")
            else:
                for doc in retrieved_docs:
                    doc_info = f"Trích dẫn từ Điều {doc['ma_dieu']} Luật Đất đai {int(float(doc['phien_ban']))}"
                    context += f"--- {doc_info} ---\n{doc['raw_content']}\n\n"

            # 3. SINH CÂU TRẢ LỜI (GENERATE)
            if context:
                final_prompt = build_qa_prompt(user_query, context)
                try:
                    final_answer = call_gemini_api(final_prompt)
                    st.markdown("### 📝 Câu trả lời:")
                    st.markdown(final_answer)

                    with st.expander("🔍 Xem các điều luật liên quan nhất đã được sử dụng"):
                        for doc in retrieved_docs:
                            st.markdown(f"**Điều {doc['ma_dieu']} Luật Đất đai {int(float(doc['phien_ban']))} (Điểm liên quan: {doc.get('rerank_score'):.4f})**")
                            st.text(doc['raw_content'])
                except Exception as e:
                    st.error(f"Đã có lỗi xảy ra khi gọi đến mô hình ngôn ngữ: {e}")
            else:
                st.error("Không thể xây dựng ngữ cảnh từ các điều luật truy xuất được.")

# --- XỬ LÝ TAB 2: SO SÁNH LUẬT ---
with tab2:
    st.header("So sánh sự khác biệt giữa Luật 2013 và 2024")
    comparison_query = st.text_input("Nhập chủ đề bạn muốn so sánh:", key="compare_input", placeholder="Ví dụ: So sánh quy định về thu hồi đất để phát triển kinh tế - xã hội")

    if comparison_query:
        with st.spinner("⚖️ Đang đối chiếu các phiên bản luật..."):
            
            # 1. TRUY XUẤT (RETRIEVE) - TÁI SỬ DỤNG PIPELINE
            # Lấy một tập các điều luật liên quan từ cả 2 phiên bản
            retrieved_docs = retrieval_pipeline(comparison_query, initial_k=30, final_k=5) # Lấy nhiều hơn để có ngữ cảnh rộng
            
            # 2. XÂY DỰNG NGỮ CẢNH SO SÁNH
            context = ""
            if not retrieved_docs:
                st.warning("Không tìm thấy điều luật nào liên quan đến chủ đề này.")
            else:
                for doc in retrieved_docs:
                    doc_info = f"Trích dẫn từ Điều {doc['ma_dieu']} Luật Đất đai {int(float(doc['phien_ban']))}"
                    context += f"--- {doc_info} ---\n{doc['raw_content']}\n\n"

            # 3. SINH CÂU TRẢ LỜI SO SÁNH (GENERATE)
            if context:
                final_prompt = build_comparison_prompt(comparison_query, context)
                try:
                    final_answer = call_gemini_api(final_prompt)
                    st.markdown("### 📊 Bài phân tích so sánh:")
                    st.markdown(final_answer)

                    with st.expander("🔍 Xem các điều luật liên quan đã được sử dụng để so sánh"):
                        for doc in retrieved_docs:
                            st.markdown(f"**Điều {doc['ma_dieu']} Luật Đất đai {int(float(doc['phien_ban']))} (Điểm liên quan: {doc.get('rerank_score'):.4f})**")
                            st.text(doc['raw_content'])
                except Exception as e:
                    st.error(f"Đã có lỗi xảy ra khi gọi đến mô hình ngôn ngữ: {e}")