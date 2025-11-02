import json
import pandas as pd
from glob import glob

def main():
    all_entities = {}
    all_relationships = []
    
    # 1. Đọc JSON từ trích xuất nội tại
    json_files = glob('output_json_2013/*.json') + glob('output_json_2024/*.json')
    print(f"Đang xử lý {len(json_files)} file trích xuất nội tại...")
    
    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for entity in data.get('entities', []):
                # Dùng ID làm key để loại bỏ trùng lặp
                all_entities[entity['id']] = {
                    'label': entity['label'],
                    'properties': json.dumps(entity.get('properties', {}), ensure_ascii=False)
                }

            all_relationships.extend(data.get('relationships', []))
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Bỏ qua file lỗi: {file_path} - Lỗi: {e}")

    # 2. Đọc JSON từ trích xuất so sánh
    comparison_files = glob('comparisons_json/*.json')
    print(f"Đang xử lý {len(comparison_files)} file so sánh...")
    
    for file_path in comparison_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if data.get('target_id_2013'):
                # Tạo quan hệ THAY_THE_CHO
                relationship = {
                    'source_id': data['source_id_2024'],
                    'target_id': data['target_id_2013'],
                    'relationship_type': 'THAY_THE_CHO',
                    'properties': json.dumps({
                        'type': data.get('change_type', ''),
                        'summary': data.get('change_summary', '')
                    }, ensure_ascii=False)
                }
                all_relationships.append(relationship)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Bỏ qua file so sánh lỗi: {file_path} - Lỗi: {e}")

    # 3. Chuyển đổi và lưu file CSV
    # Nodes CSV
    nodes_list = [{'node_id': k, 'label': v['label'], 'properties': v['properties']} for k, v in all_entities.items()]
    nodes_df = pd.DataFrame(nodes_list)
    nodes_df.to_csv('final_csv/nodes.csv', index=False, encoding='utf-8-sig')
    
    # Relationships CSV
    # Cần thêm cột properties cho các quan hệ thông thường
    for rel in all_relationships:
        if 'properties' not in rel:
            rel['properties'] = json.dumps({})
            
    rels_df = pd.DataFrame(all_relationships)
    # Đổi tên cột cho phù hợp với Neo4j
    rels_df.rename(columns={
        'source_id': ':START_ID',
        'target_id': ':END_ID',
        'relationship_type': ':TYPE',
        'properties': 'properties'
    }, inplace=True)
    rels_df.to_csv('final_csv/relationships.csv', index=False, encoding='utf-8-sig')
    
    print("\n--- Hoàn thành! ---")
    print(f"Đã tạo {len(nodes_df)} nút trong final_csv/nodes.csv")
    print(f"Đã tạo {len(rels_df)} quan hệ trong final_csv/relationships.csv")

if __name__ == "__main__":
    main()