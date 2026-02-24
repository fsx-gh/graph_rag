from flask import Blueprint, request, jsonify
import os
import json
from datetime import datetime, timedelta

from neo4j_ops import (
    neo4j_add_person, neo4j_update_person, neo4j_delete_person,
    neo4j_add_relationship, neo4j_delete_relationship, neo4j_get_graph, neo4j_init_data
)

from data_loader import EXPORT_DIR
from graph_proc import GraphProcessor

bp = Blueprint('basic', __name__)


@bp.route('/api/persons', methods=['POST'])
def add_person():
    data = request.json
    if not data.get('name'):
        return jsonify({'error': '姓名不能为空'}), 400
    person, error = neo4j_add_person(data)
    if error:
        return jsonify({'error': error}), 400
    return jsonify(person), 201


@bp.route('/api/persons/<person_id>', methods=['PUT'])
def update_person(person_id):
    data = request.json
    person, error = neo4j_update_person(person_id, data)
    if error:
        return jsonify({'error': error}), 400
    return jsonify(person)


@bp.route('/api/persons/<person_id>', methods=['DELETE'])
def delete_person(person_id):
    if neo4j_delete_person(person_id):
        return jsonify({'message': '删除成功'}), 200
    return jsonify({'error': '删除失败'}), 500


@bp.route('/api/relationships', methods=['POST'])
def add_relationship():
    data = request.json
    if not all(k in data for k in ['source', 'target', 'type']):
        return jsonify({'error': '缺少必要参数'}), 400
    relationship, error = neo4j_add_relationship(data)
    if error:
        return jsonify({'error': error}), 400
    return jsonify(relationship), 201


@bp.route('/api/relationships/<rel_id>', methods=['DELETE'])
def delete_relationship(rel_id):
    if neo4j_delete_relationship(rel_id):
        return jsonify({'message': '删除成功'}), 200
    return jsonify({'error': '删除失败'}), 500


@bp.route('/api/nodes', methods=['GET'])
def get_all_nodes():
    with __import__('neo4j_ops').neo4j_driver.session() as session:
        try:
            result = session.run(
                """
                MATCH (p:Person)
                RETURN elementId(p) as id, p.name as name, p.description as description
                ORDER BY p.name
                """
            )
            nodes = [dict(record) for record in result]
            return jsonify(nodes), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500


@bp.route('/api/nodes', methods=['POST'])
def create_node():
    data = request.json
    try:
        with __import__('neo4j_ops').neo4j_driver.session() as session:
            result = session.run(
                """
                CREATE (n:Person {
                    id: $id,
                    name: $name,
                    description: $description,
                    category: $category
                })
                RETURN elementId(n) as id, n.name as name, n.description as description, n.category as category
                """,
                {
                    'id': data.get('id', ''),
                    'name': data.get('name', ''),
                    'description': data.get('description', ''),
                    'category': data.get('category', '')
                }
            )
            record = result.single()
            return jsonify(dict(record)), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@bp.route('/api/relationships', methods=['GET'])
def get_all_relationships():
    with __import__('neo4j_ops').neo4j_driver.session() as session:
        try:
            result = session.run(
                """
                MATCH (source:Person)-[r:RELATES]->(target:Person)
                RETURN elementId(r) as id, elementId(source) as source_id, source.name as source, elementId(target) as target_id, target.name as target, r.type as type
                ORDER BY source.name, target.name
                """
            )
            relationships = [dict(record) for record in result]
            return jsonify(relationships), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500


@bp.route('/api/graph', methods=['GET'])
def get_graph():
    return jsonify(neo4j_get_graph())


@bp.route('/api/graph/import', methods=['POST'])
def import_graph():
    data = request.json
    if not data or 'nodes' not in data or 'relationships' not in data:
        return jsonify({'error': '无效的 JSON 格式'}), 400

    with __import__('neo4j_ops').neo4j_driver.session() as session:
        try:
            session.run("MATCH (n) DETACH DELETE n")
            for node in data['nodes']:
                session.run(
                    """
                    MERGE (p:Person {name: $name})
                    ON CREATE SET p.age = $age, p.occupation = $occupation, p.description = $description
                    """,
                    name=node['name'],
                    age=node.get('age'),
                    occupation=node.get('occupation'),
                    description=node.get('description', '')
                )
            for rel in data['relationships']:
                source_idx = int(rel['source']) - 1 if isinstance(rel['source'], str) else rel['source'] - 1
                target_idx = int(rel['target']) - 1 if isinstance(rel['target'], str) else rel['target'] - 1
                if 0 <= source_idx < len(data['nodes']) and 0 <= target_idx < len(data['nodes']):
                    session.run(
                        """
                        MATCH (a:Person {name: $source_name}), (b:Person {name: $target_name})
                        MERGE (a)-[r:RELATES {type: $type}]->(b)
                        """,
                        source_name=data['nodes'][source_idx]['name'],
                        target_name=data['nodes'][target_idx]['name'],
                        type=rel.get('type', '关系')
                    )
            # 成功导入数据后，重建 RAG（生成节点 embeddings，写回 Neo4j 并导出到文件）
            try:
                gp = GraphProcessor()
                data_after = gp.fetch_nodes_and_rels()
                emb_map = gp.node_embeddings(data_after['nodes'])
                try:
                    gp.persist_embeddings_to_neo4j(emb_map)
                except Exception:
                    pass
                try:
                    emb_path = os.path.join(EXPORT_DIR, 'embeddings.json')
                    gp.save_embeddings_to_file(emb_map, emb_path)
                except Exception:
                    pass
            except Exception:
                # 重建失败不影响导入结果，但记录/忽略错误
                pass

            return jsonify({'message': '导入成功'}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 400


@bp.route('/api/graph/export', methods=['POST'])
def export_graph():
    try:
        export_data = request.get_json() if request.is_json else neo4j_get_graph()
        os.makedirs(EXPORT_DIR, exist_ok=True)
        import time
        timestamp = int(time.time() * 1000)
        filename = f'graph_{timestamp}.json'
        filepath = os.path.join(EXPORT_DIR, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        return jsonify({'message': '导出成功', 'filename': filename, 'path': filepath})
    except Exception as e:
        return jsonify({'error': f'导出失败: {str(e)}'}), 500


@bp.route('/api/init', methods=['POST'])
def init_data():
    dataset = request.args.get('dataset', 'qing-dynasty')
    neo4j_init_data(dataset)
    # 初始化完成后重建 RAG
    try:
        gp = GraphProcessor()
        data_after = gp.fetch_nodes_and_rels()
        emb_map = gp.node_embeddings(data_after['nodes'])
        try:
            gp.persist_embeddings_to_neo4j(emb_map)
        except Exception:
            pass
        try:
            emb_path = os.path.join(EXPORT_DIR, 'embeddings.json')
            gp.save_embeddings_to_file(emb_map, emb_path)
        except Exception:
            pass
    except Exception:
        pass

    return jsonify({'message': '数据初始化成功'}), 200


@bp.route('/api/query', methods=['GET'])
def query_person():
    name = request.args.get('name')
    if not name:
        return jsonify({'error': '请提供姓名'}), 400
    with __import__('neo4j_ops').neo4j_driver.session() as session:
        result = session.run(
            """
            MATCH (p:Person {name: $name})
            OPTIONAL MATCH (p)-[r:RELATES]-(other)
            RETURN elementId(p) as id, p.name as name, p.age as age, p.occupation as occupation, p.description as description,
                   collect(DISTINCT {id: elementId(r), source: elementId(startNode(r)), target: elementId(endNode(r)), type: r.type}) as relationships
            """,
            name=name
        )
        record = result.single()
        if not record:
            return jsonify({'error': '人物未找到'}), 404
        return jsonify({
            'person': {
                'id': record['id'],
                'name': record['name'],
                'age': record['age'],
                'occupation': record['occupation'],
                'description': record['description']
            },
            'relationships': [r for r in record['relationships'] if r['id'] is not None]
        })


@bp.route('/api/search', methods=['GET'])
def search_advanced():
    keyword = request.args.get('keyword', '').lower()
    field = request.args.get('field', 'name')
    if not keyword:
        return jsonify({'error': '搜索关键词不能为空'}), 400
    with __import__('neo4j_ops').neo4j_driver.session() as session:
        query = f"""
        MATCH (p:Person)
        WHERE toLower(p.{field}) CONTAINS $keyword
        RETURN elementId(p) as id, p.name as name, p.age as age, 
               p.occupation as occupation, p.description as description
        LIMIT 20
        """
        results = session.run(query, keyword=keyword)
        persons = [dict(record) for record in results]
        return jsonify(persons)


@bp.route('/api/relationships/type/<rel_type>', methods=['GET'])
def get_relationships_by_type(rel_type):
    with __import__('neo4j_ops').neo4j_driver.session() as session:
        result = session.run(
            """
            MATCH (a:Person)-[r:RELATES {type: $type}]->(b:Person)
            RETURN elementId(a) as source_id, a.name as source_name,
                   elementId(b) as target_id, b.name as target_name,
                   elementId(r) as rel_id, r.type as type
            """,
            type=rel_type
        )
        rels = [dict(record) for record in result]
        return jsonify(rels)


@bp.route('/api/network/path', methods=['GET'])
def find_path():
    start_name = request.args.get('start')
    end_name = request.args.get('end')
    if not start_name or not end_name:
        return jsonify({'error': '起点和终点名称不能为空'}), 400
    with __import__('neo4j_ops').neo4j_driver.session() as session:
        try:
            result = session.run(
                """
                MATCH path = shortestPath((a:Person {name: $start_name})-[*]-(b:Person {name: $end_name}))
                WITH path, length(path) as pathLength
                UNWIND nodes(path) as node
                RETURN node.name as name, pathLength
                """,
                start_name=start_name,
                end_name=end_name
            )
            records = list(result)
            if records:
                path_length = records[0]['pathLength']
                nodes_in_path = [{'name': r['name']} for r in records]
                return jsonify({'pathLength': path_length, 'nodes': nodes_in_path})
            return jsonify({'error': '未找到路径'}), 404
        except Exception as e:
            return jsonify({'error': f'查询失败: {str(e)}'}), 500

bp = Blueprint('basic', __name__)

@bp.route('/api/persons', methods=['POST'])
def add_person():
    data = request.json
    if not data.get('name'):
        return jsonify({'error': '姓名不能为空'}), 400
    person, error = neo4j_add_person(data)
    if error:
        return jsonify({'error': error}), 400
    
    return jsonify(person), 201


@bp.route('/api/persons/<person_id>', methods=['PUT'])
def update_person(person_id):
    data = request.json
    person, error = neo4j_update_person(person_id, data)
    if error:
        return jsonify({'error': error}), 400
    return jsonify(person)


@bp.route('/api/persons/<person_id>', methods=['DELETE'])
def delete_person(person_id):
    if neo4j_delete_person(person_id):
        return jsonify({'message': '删除成功'}), 200
    return jsonify({'error': '删除失败'}), 500


@bp.route('/api/relationships', methods=['POST'])
def add_relationship():
    data = request.json
    if not all(k in data for k in ['source', 'target', 'type']):
        return jsonify({'error': '缺少必要参数'}), 400
    relationship, error = neo4j_add_relationship(data)
    if error:
        return jsonify({'error': error}), 400
    
    return jsonify(relationship), 201


@bp.route('/api/relationships/<rel_id>', methods=['DELETE'])
def delete_relationship(rel_id):
    if neo4j_delete_relationship(rel_id):
        
        return jsonify({'message': '删除成功'}), 200
    return jsonify({'error': '删除失败'}), 500


@bp.route('/api/nodes', methods=['GET'])
def get_all_nodes():
    from neo4j_ops import neo4j_driver
    with neo4j_driver.session() as session:
        try:
            result = session.run(
                """
                MATCH (p:Person)
                RETURN p.id as id, p.name as name, p.description as description
                ORDER BY p.name
                """
            )
            nodes = [dict(record) for record in result]
            return jsonify(nodes), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500


@bp.route('/api/nodes', methods=['POST'])
def create_node():
    data = request.json
    from neo4j_ops import neo4j_driver
    try:
        with neo4j_driver.session() as session:
            result = session.run(
                """
                CREATE (n:Person {
                    id: $id,
                    name: $name,
                    description: $description,
                    category: $category
                })
                RETURN n.id as id, n.name as name, n.description as description, n.category as category
                """,
                {
                    'id': data.get('id', ''),
                    'name': data.get('name', ''),
                    'description': data.get('description', ''),
                    'category': data.get('category', '')
                }
            )
            record = result.single()
            return jsonify(dict(record)), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@bp.route('/api/relationships', methods=['GET'])
def get_all_relationships():
    from neo4j_ops import neo4j_driver
    with neo4j_driver.session() as session:
        try:
            result = session.run(
                """
                MATCH (source:Person)-[r:RELATES]->(target:Person)
                RETURN r.id as id, source.id as source_id, source.name as source, target.id as target_id, target.name as target, r.type as type
                ORDER BY source.name, target.name
                """
            )
            relationships = [dict(record) for record in result]
            return jsonify(relationships), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500


@bp.route('/api/graph', methods=['GET'])
def get_graph():
    return jsonify(neo4j_get_graph())


@bp.route('/api/graph/import', methods=['POST'])
def import_graph():
    data = request.json
    if not data or 'nodes' not in data or 'relationships' not in data:
        return jsonify({'error': '无效的 JSON 格式'}), 400

    from neo4j_ops import neo4j_driver
    with neo4j_driver.session() as session:
        try:
            session.run("MATCH (n) DETACH DELETE n")
            for node in data['nodes']:
                session.run(
                    """
                    MERGE (p:Person {name: $name})
                    ON CREATE SET p.age = $age, p.occupation = $occupation, p.description = $description
                    """,
                    name=node['name'],
                    age=node.get('age'),
                    occupation=node.get('occupation'),
                    description=node.get('description', '')
                )

            for rel in data['relationships']:
                source_idx = int(rel['source']) - 1 if isinstance(rel['source'], str) else rel['source'] - 1
                target_idx = int(rel['target']) - 1 if isinstance(rel['target'], str) else rel['target'] - 1
                if 0 <= source_idx < len(data['nodes']) and 0 <= target_idx < len(data['nodes']):
                    session.run(
                        """
                        MATCH (a:Person {name: $source_name}), (b:Person {name: $target_name})
                        MERGE (a)-[r:RELATES {type: $type}]->(b)
                        """,
                        source_name=data['nodes'][source_idx]['name'],
                        target_name=data['nodes'][target_idx]['name'],
                        type=rel.get('type', '关系')
                    )

            return jsonify({'message': '导入成功'}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 400


@bp.route('/api/graph/export', methods=['POST'])
def export_graph():
    try:
        export_data = request.get_json() if request.is_json else neo4j_get_graph()
        os.makedirs(EXPORT_DIR, exist_ok=True)
        import time
        timestamp = int(time.time() * 1000)
        filename = f'graph_{timestamp}.json'
        filepath = os.path.join(EXPORT_DIR, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        return jsonify({'message': '导出成功', 'filename': filename, 'path': filepath})
    except Exception as e:
        return jsonify({'error': f'导出失败: {str(e)}'}), 500


@bp.route('/api/init', methods=['POST'])
def init_data():
    dataset = request.args.get('dataset', 'qing-dynasty')
    neo4j_init_data(dataset)
    return jsonify({'message': '数据初始化成功'}), 200


@bp.route('/api/query', methods=['GET'])
def query_person():
    name = request.args.get('name')
    if not name:
        return jsonify({'error': '请提供姓名'}), 400
    from neo4j_ops import neo4j_driver
    with neo4j_driver.session() as session:
        result = session.run(
            """
            MATCH (p:Person {name: $name})
            OPTIONAL MATCH (p)-[r:RELATES]-(other)
            RETURN elementId(p) as id, p.name as name, p.age as age, p.occupation as occupation, p.description as description,
                   collect(DISTINCT {id: elementId(r), source: elementId(startNode(r)), target: elementId(endNode(r)), type: r.type}) as relationships
            """,
            name=name
        )
        record = result.single()
        if not record:
            return jsonify({'error': '人物未找到'}), 404
        return jsonify({
            'person': {
                'id': record['id'],
                'name': record['name'],
                'age': record['age'],
                'occupation': record['occupation'],
                'description': record['description']
            },
            'relationships': [r for r in record['relationships'] if r['id'] is not None]
        })


@bp.route('/api/search', methods=['GET'])
def search_advanced():
    keyword = request.args.get('keyword', '').lower()
    field = request.args.get('field', 'name')
    if not keyword:
        return jsonify({'error': '搜索关键词不能为空'}), 400
    from neo4j_ops import neo4j_driver
    with neo4j_driver.session() as session:
        query = f"""
        MATCH (p:Person)
        WHERE toLower(p.{field}) CONTAINS $keyword
        RETURN elementId(p) as id, p.name as name, p.age as age, 
               p.occupation as occupation, p.description as description
        LIMIT 20
        """
        results = session.run(query, keyword=keyword)
        persons = [dict(record) for record in results]
        return jsonify(persons)


@bp.route('/api/relationships/type/<rel_type>', methods=['GET'])
def get_relationships_by_type(rel_type):
    from neo4j_ops import neo4j_driver
    with neo4j_driver.session() as session:
        result = session.run(
            """
            MATCH (a:Person)-[r:RELATES {type: $type}]->(b:Person)
            RETURN elementId(a) as source_id, a.name as source_name,
                   elementId(b) as target_id, b.name as target_name,
                   elementId(r) as rel_id, r.type as type
            """,
            type=rel_type
        )
        rels = [dict(record) for record in result]
        return jsonify(rels)


@bp.route('/api/network/path', methods=['GET'])
def find_path():
    start_name = request.args.get('start')
    end_name = request.args.get('end')
    if not start_name or not end_name:
        return jsonify({'error': '起点和终点名称不能为空'}), 400
    from neo4j_ops import neo4j_driver
    with neo4j_driver.session() as session:
        try:
            result = session.run(
                """
                MATCH path = shortestPath((a:Person {name: $start_name})-[*]-(b:Person {name: $end_name}))
                WITH path, length(path) as pathLength
                UNWIND nodes(path) as node
                RETURN node.name as name, pathLength
                """,
                start_name=start_name,
                end_name=end_name
            )
            records = list(result)
            if records:
                path_length = records[0]['pathLength']
                nodes_in_path = [{'name': r['name']} for r in records]
                return jsonify({'pathLength': path_length, 'nodes': nodes_in_path})
            return jsonify({'error': '未找到路径'}), 404
        except Exception as e:
            return jsonify({'error': f'查询失败: {str(e)}'}), 500
