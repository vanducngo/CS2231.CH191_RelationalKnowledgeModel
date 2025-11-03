import os
import json
from neo4j import GraphDatabase
from dotenv import load_dotenv
import re
from unidecode import unidecode

def normalize_string_id(s: str) -> str:
    if not isinstance(s, str): return ""
    s = unidecode(s.strip())
    s = re.sub(r'[^a-zA-Z0-9]+', '_', s)
    return s.lower().strip('_')

class KGConnector:
    def __init__(self):
        load_dotenv()
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD")
        
        if not all([uri, user, password]):
            raise ValueError("Vui lòng thiết lập NEO4J_URI, NEO4J_USER, và NEO4J_PASSWORD trong file .env")
            
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.driver.verify_connectivity()
            print("Kết nối đến Neo4j thành công!")
        except Exception as e:
            print(f"Lỗi kết nối đến Neo4j: {e}")
            self.driver = None

    def close(self):
        if self.driver is not None:
            self.driver.close()
            print("Đã đóng kết nối Neo4j.")

    def _run_query(self, query, parameters=None):
        if self.driver is None: return []
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters)
                return [record.data() for record in result]
        except Exception as e:
            print(f"Lỗi thực thi truy vấn: {query} | Lỗi: {e}")
            return []

    def get_all_laws_for_vectordb(self):
        print("Đang lấy dữ liệu (ID và nội dung) của tất cả các Điều Luật từ KG...")
        query = """
        MATCH (n:Dieuluat)
        WHERE n.noi_dung IS NOT NULL AND n.noi_dung <> ''
        RETURN n.id AS id, n.noi_dung AS content
        """
        return self._run_query(query)

    def get_node_properties_by_id(self, node_id: str):
        if not node_id: return None
        
        normalized_id = normalize_string_id(node_id)
        query = "MATCH (n {id: $node_id}) RETURN n"
        parameters = {"node_id": normalized_id}
        result = self._run_query(query, parameters)
        
        if result:
            node = result[0].get('n')
            return dict(node) if node else None
        return None
        
    def find_comparison_by_id(self, law_id_2024: str):
        normalized_id = normalize_string_id(law_id_2024)
        query = """
        MATCH (new_law:Dieuluat {id: $law_id_2024})-[r:THAY_THE_CHO]->(old_law:Dieuluat)
        RETURN new_law, old_law, properties(r) AS comparison_properties
        """
        parameters = {"law_id_2024": normalized_id}
        result = self._run_query(query, parameters)
        
        if result:
            record = result[0]
            return {
                "new_law_details": dict(record.get('new_law', {})),
                "old_law_details": dict(record.get('old_law', {})),
                "comparison_details": record.get('comparison_properties', {})
            }
        return None

    def find_laws_by_concept_name(self, concept_name: str, limit: int = 5):
        print(f"Đang tìm kiếm các luật liên quan đến '{concept_name}'...")
        query = """
        MATCH (c)
        WHERE (c:Khainiem OR c:Chuthe) AND toLower(c.name) CONTAINS toLower($concept_name)
        MATCH (c)<-[r]-(d:Dieuluat)
        RETURN DISTINCT d.id AS id, d.name AS ten_dieu
        LIMIT $limit
        """
        parameters = {"concept_name": concept_name, "limit": limit}
        return self._run_query(query, parameters)

    def keyword_search(self, keyword: str, limit: int = 5):
        query = """
        MATCH (n:Dieuluat)
        WHERE toLower(n.name) CONTAINS toLower($keyword) OR toLower(n.noi_dung) CONTAINS toLower($keyword)
        RETURN n.id as id
        LIMIT $limit
        """
        return self._run_query(query, {"keyword": keyword, "limit": limit})

# --- Ví dụ sử dụng và kiểm tra ---
if __name__ == '__main__':
    kg = KGConnector()
    if kg.driver:
        # 1. Test lấy dữ liệu cho VectorDB
        all_laws = kg.get_all_laws_for_vectordb()
        print(f"\nTìm thấy {len(all_laws)} điều luật có nội dung để tạo VectorDB.")
        if all_laws:
            print("Ví dụ điều luật đầu tiên:", all_laws[0])
        else:
            print("Không tìm thấy điều luật nào có nội dung.")

        # 2. Test lấy chi tiết một nút
        print("\n--- Test: Lấy chi tiết Điều 27 (2024) ---")
        details_27 = kg.get_node_properties_by_id('dieu_27_2024')
        if details_27:
            print(json.dumps(details_27, indent=2, ensure_ascii=False))
        else:
            print("Không tìm thấy thông tin cho 'dieu_27_2024'.")
            
        # 3. Test tìm kiếm so sánh
        print("\n--- Test: Tìm so sánh cho Điều 4 (2024) - Về Chủ thể ---")
        comparison_4 = kg.find_comparison_by_id('dieu_4_2024')
        if comparison_4:
            print(json.dumps(comparison_4, indent=2, ensure_ascii=False))
        else:
            print("Không tìm thấy thông tin so sánh cho 'dieu_4_2024'.")
            
        # 4. Test tìm luật theo khái niệm
        print("\n--- Test: Tìm luật liên quan đến khái niệm 'Hộ gia đình' ---")
        related_laws = kg.find_laws_by_concept_name('Hộ gia đình') 
        print(f"Các luật liên quan đến 'Hộ gia đình': {related_laws}")
        
        kg.close()