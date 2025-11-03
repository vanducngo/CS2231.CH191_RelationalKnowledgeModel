import streamlit as st
from kg_connector import KGConnector, normalize_string_id
from retriever import SemanticRetriever
from llm_callers import call_gemini_api
import json

# --- KHỞI TẠO CÁC THÀNH PHẦN CỐT LÕI ---
# Sử dụng cache của Streamlit để không phải load lại các model/kết nối nặng mỗi lần tương tác
@st.cache_resource
def initialize_components():
    """
    Khởi tạo và cache lại các đối tượng KGConnector và SemanticRetriever.
    """
    print("--- Đang khởi tạo các thành phần cốt lõi (chỉ chạy một lần) ---")
    kg = KGConnector()
    retriever = SemanticRetriever()
    print("--- Khởi tạo hoàn tất ---")
    return kg, retriever

# Tải các component
try:
    kg_connector, retriever = initialize_components()
    # Kiểm tra xem retriever có được tải thành công không
    if not retriever.index:
        st.error("Không thể khởi tạo Semantic Retriever. Vui lòng kiểm tra lại file index và ID.")
        st.stop()
except Exception as e:
    st.error(f"Đã xảy ra lỗi nghiêm trọng khi khởi tạo: {e}")
    st.stop()


# --- THIẾT KẾ GIAO DIỆN NGƯỜI DÙNG ---
st.set_page_config(layout="wide", page_title="Trợ lý Pháp lý Đất đai")

st.title("🏛️ Trợ lý Pháp lý Thông minh về Luật Đất đai")
st.write("Đặt câu hỏi hoặc yêu cầu so sánh về Luật Đất đai 2013 và 2024.")

# Tạo 2 tab cho 2 chức năng chính
tab1, tab2 = st.tabs(["❓ Hỏi-Đáp Tình huống", "⚖️ So sánh Luật"])


# --- XỬ LÝ TAB 1: HỎI-ĐÁP TÌNH HUỐNG ---
with tab1:
    st.header("Đặt câu hỏi tình huống")
    user_query = st.text_input("Nhập câu hỏi của bạn vào đây:", key="qa_input", placeholder="Ví dụ: Hạn mức nhận chuyển nhượng đất nông nghiệp là bao nhiêu?")

    if user_query:
        with st.spinner("🧠 Đang phân tích và tìm kiếm câu trả lời..."):
            
            # 1. TRUY XUẤT (RETRIEVE) - Tăng top_k để có ngữ cảnh rộng hơn
            semantic_ids = retriever.search(user_query, top_k=10)
            keyword_results = kg_connector.keyword_search(user_query, limit=10)
            keyword_ids = [res['id'] for res in keyword_results]
            retrieved_ids = list(set(semantic_ids + keyword_ids))
            
            # 2. XÂY DỰNG NGỮ CẢNH (CONTEXT)
            context = ""
            retrieved_docs = []
            if not retrieved_ids:
                 st.warning("Không tìm thấy điều luật nào có liên quan về mặt ngữ nghĩa.")
            else:
                for law_id in retrieved_ids:
                    # Sử dụng hàm get_node_properties_by_id đã được sửa lỗi
                    details = kg_connector.get_node_properties_by_id(law_id)
                    if details:
                        content = details.get('noi_dung', details.get('name', 'Không có nội dung chi tiết.'))
                        # Suy ra thông tin từ ID nếu thuộc tính không có
                        ma_dieu = details.get('ma_dieu', law_id.split('_')[1] if 'dieu' in law_id else 'N/A')
                        phien_ban = details.get('phien_ban', law_id.split('_')[-1] if 'dieu' in law_id else 'N/A')
                        
                        doc_info = f"Trích dẫn từ Điều {ma_dieu} Luật Đất đai {phien_ban}"
                        context += f"--- {doc_info} ---\n{content}\n\n"
                        retrieved_docs.append({"source": doc_info, "content": content})

            # 3. SINH CÂU TRẢ LỜI (GENERATE)
            if context:
                final_prompt = f"""
                    Bạn là một trợ lý pháp lý cực kỳ cẩn thận. Chỉ được phép sử dụng thông tin từ phần "NGỮ CẢNH LUẬT" được cung cấp dưới đây.
                    Hãy trả lời câu hỏi của người dùng.
                    1. Phân tích câu hỏi.
                    2. Tìm câu trả lời CHÍNH XÁC trong ngữ cảnh.
                    3. Với mỗi luận điểm, trích dẫn trực tiếp bằng cách copy-paste một đoạn ngắn từ ngữ cảnh và đặt nó trong ngoặc kép, sau đó ghi căn cứ '[Căn cứ: Điều X Luật Y]'.
                    4. Nếu không có bất kỳ thông tin nào trong ngữ cảnh có thể trả lời câu hỏi, hãy trả lời DUY NHẤT câu: "Tôi không tìm thấy thông tin để trả lời câu hỏi này trong các điều luật được cung cấp."

                    --- NGỮ CẢNH LUẬT ---
                    {context}
                    --- CÂU HỎI ---
                    {user_query}

                    --- CÂU TRẢ LỜI ---
                """
                
                try:
                    final_answer = call_gemini_api(final_prompt)
                    st.markdown("### 📝 Câu trả lời:")
                    st.markdown(final_answer)

                    with st.expander("🔍 Xem các trích dẫn luật đã được sử dụng làm ngữ cảnh"):
                        for doc in retrieved_docs:
                            st.markdown(f"**{doc['source']}**")
                            st.text(doc['content'])
                except Exception as e:
                    st.error(f"Đã có lỗi xảy ra khi gọi đến mô hình ngôn ngữ: {e}")
            else:
                st.error("Không thể xây dựng ngữ cảnh từ các điều luật truy xuất được.")


# --- XỬ LÝ TAB 2: SO SÁNH LUẬT ---
with tab2:
    st.header("So sánh sự khác biệt giữa Luật 2013 và 2024")
    comparison_query = st.text_input("Nhập chủ đề bạn muốn so sánh (ví dụ: 'hộ gia đình', 'bảng giá đất'):", key="compare_input")

    if comparison_query:
        with st.spinner("⚖️ Đang đối chiếu các phiên bản luật..."):
            # Tìm các điều luật 2024 liên quan đến chủ đề
            related_law_ids = retriever.search(comparison_query, top_k=10)
            
            comparison_results = []
            processed_ids = set() 

            for law_id in related_law_ids:
                # Chỉ xử lý các điều luật của 2024
                if '_2024' in law_id and law_id not in processed_ids:
                    # Sử dụng hàm find_comparison_by_id
                    comp = kg_connector.find_comparison_by_id(law_id)
                    if comp:
                        comparison_results.append(comp)
                    processed_ids.add(law_id)
            
            if not comparison_results:
                st.warning("Không tìm thấy sự thay đổi trực tiếp nào liên quan đến chủ đề này trong cơ sở tri thức.")
            else:
                st.markdown("### 📊 Kết quả so sánh:")
                for res in comparison_results:
                    new_law = res.get('new_law_details', {})
                    old_law = res.get('old_law_details', {})
                    details = res.get('comparison_details', {})

                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader(f"Luật Đất đai 2013 (Điều {old_law.get('ma_dieu', 'N/A')})")
                        st.text(old_law.get('noi_dung', 'Không có nội dung chi tiết.'))
                    with col2:
                        st.subheader(f"Luật Đất đai 2024 (Điều {new_law.get('ma_dieu', 'N/A')})")
                        st.text(new_law.get('noi_dung', 'Không có nội dung chi tiết.'))
                    
                    st.info(f"**Phân tích thay đổi ({details.get('change_type', 'N/A')}):** {details.get('summary', 'Không có tóm tắt.')}")
                    st.divider()