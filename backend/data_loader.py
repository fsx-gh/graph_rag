import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
EXPORT_DIR = os.path.join(os.path.dirname(BASE_DIR), 'export')
SAMPLE_DATA_PATH = os.path.join(DATA_DIR, 'qing_history.json')


def load_sample_data(dataset):
    dataset_files = {
        'qing-dynasty': os.path.join(DATA_DIR, 'qing_history.json'),
        'journey-to-west': os.path.join(DATA_DIR, 'journey_to_west.json'),
        'dream-of-red-mansion': os.path.join(DATA_DIR, 'dream_of_red_mansion.json'),
        'four-gen-family': os.path.join(DATA_DIR, 'four_gen_family.json'),
        'advanced-analysis': os.path.join(DATA_DIR, 'advanced_analysis.json'),
        'water-margin': os.path.join(DATA_DIR, 'water_margin.json')
    }
    file_path = dataset_files.get(dataset, SAMPLE_DATA_PATH)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"警告: {file_path} 未找到，使用内置默认数据")
        return {
            'nodes': [
                {'id': 1, 'name': '张三', 'age': 45, 'occupation': '企业家', 'description': '科技公司CEO'},
                {'id': 2, 'name': '李四', 'age': 42, 'occupation': '医生', 'description': '主任医师'},
                {'id': 3, 'name': '王五', 'age': 20, 'occupation': '学生', 'description': '大学生'},
                {'id': 4, 'name': '赵六', 'age': 40, 'occupation': '教师', 'description': '大学教授'},
            ],
            'relationships': [
                {'id': 1, 'source': 1, 'target': 2, 'type': '朋友'},
                {'id': 2, 'source': 1, 'target': 3, 'type': '父子'},
                {'id': 3, 'source': 2, 'target': 4, 'type': '同事'},
                {'id': 4, 'source': 3, 'target': 4, 'type': '师生'},
            ]
        }
    except json.JSONDecodeError as e:
        print(f"错误: {SAMPLE_DATA_PATH} JSON 格式不正确: {e}")
        return {'nodes': [], 'relationships': []}
