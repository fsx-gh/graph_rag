from neo4j import GraphDatabase
import os
import json
import re
from datetime import datetime, timedelta

import sys
import os

# 兼容作为包或脚本运行时导入 data_loader
try:
    from backend.data_loader import load_sample_data
except Exception:
    try:
        from data_loader import load_sample_data
    except Exception:
        # 尝试把项目根加入 sys.path 后重试
        _this_dir = os.path.dirname(__file__)
        _project_root = os.path.dirname(_this_dir)
        if _project_root not in sys.path:
            sys.path.insert(0, _project_root)
        try:
            from data_loader import load_sample_data
        except Exception:
            load_sample_data = None

# Neo4j 配置（从环境变量读取）
NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', '88888888')

try:
    neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    neo4j_driver.verify_connectivity()
except Exception as e:
    print(f"✗ Neo4j 连接失败: {e}")
    print("请确保 Neo4j 数据库正在运行（模块将继续加载，但后续 Neo4j 调用会失败）")
    neo4j_driver = None


# 可选的中文分词：优先使用 jieba，否则回退到简单正则
try:
    import jieba
    _jieba_available = True
except Exception:
    _jieba_available = False


def tokenize(text):
    """将文本拆分为词项列表。优先用 jieba；不可用时使用正则回退。

    返回的词项对 ASCII 单词会做小写归一化，以保持原实现行为。
    """
    if text is None:
        return []
    s = str(text)
    if _jieba_available:
        toks = [t.strip() for t in jieba.lcut(s) if t.strip()]
        norm = []
        for t in toks:
            if re.search(r'[A-Za-z0-9]', t):
                norm.append(t.lower())
            else:
                norm.append(t)
        return [t for t in norm if re.search(r'\w', t)]
    else:
        return re.findall(r"\w+", s.lower())


def neo4j_add_person(data):
    with neo4j_driver.session() as session:
        try:
            result = session.run(
                """
                MERGE (p:Person {name: $name})
                ON CREATE SET p.age = $age, p.occupation = $occupation, p.description = $description
                RETURN elementId(p) as id, p.name as name, p.age as age, p.occupation as occupation, p.description as description
                """,
                name=data['name'],
                age=data.get('age'),
                occupation=data.get('occupation'),
                description=data.get('description', '')
            )
            record = result.single()
            if record:
                return dict(record), None
        except Exception as e:
            return None, str(e)


def neo4j_update_person(person_id, data):
    with neo4j_driver.session() as session:
        try:
            result = session.run(
                """
                MATCH (p:Person) WHERE elementId(p) = $id
                SET p.name = COALESCE($name, p.name),
                    p.age = COALESCE($age, p.age),
                    p.occupation = COALESCE($occupation, p.occupation),
                    p.description = COALESCE($description, p.description)
                RETURN elementId(p) as id, p.name as name, p.age as age, p.occupation as occupation, p.description as description
                """,
                id=person_id,
                name=data.get('name'),
                age=data.get('age'),
                occupation=data.get('occupation'),
                description=data.get('description')
            )
            record = result.single()
            if record:
                return dict(record), None
            return None, '人物不存在'
        except Exception as e:
            return None, str(e)


def neo4j_delete_person(person_id):
    with neo4j_driver.session() as session:
        try:
            session.run(
                "MATCH (p:Person) WHERE elementId(p) = $id DETACH DELETE p",
                id=person_id
            )
            return True
        except Exception as e:
            print(f"删除失败: {e}")
            return False


def neo4j_add_relationship(data):
    with neo4j_driver.session() as session:
        try:
            result = session.run(
                """
                MATCH (a:Person), (b:Person)
                WHERE elementId(a) = $source AND elementId(b) = $target
                MERGE (a)-[r:RELATES {type: $type}]->(b)
                RETURN elementId(r) as id, elementId(a) as source, elementId(b) as target, r.type as type
                """,
                source=data['source'],
                target=data['target'],
                type=data['type']
            )
            record = result.single()
            if record:
                return dict(record), None
            return None, '人物不存在'
        except Exception as e:
            return None, str(e)


def neo4j_delete_relationship(rel_id):
    with neo4j_driver.session() as session:
        try:
            session.run(
                "MATCH ()-[r:RELATES]->() WHERE elementId(r) = $id DELETE r",
                id=rel_id
            )
            return True
        except Exception as e:
            print(f"删除失败: {e}")
            return False


def neo4j_get_graph():
    with neo4j_driver.session() as session:
        nodes_result = session.run(
            "MATCH (p:Person) RETURN elementId(p) as id, p.name as name, p.age as age, p.occupation as occupation, p.description as description"
        )
        nodes = [dict(record) for record in nodes_result]

        id_mapping = {}
        nodes_result = session.run(
            "MATCH (p:Person) RETURN elementId(p) as eid, p.name as name"
        )
        for record in nodes_result:
            id_mapping[record['eid']] = record['name']

        rels_result = session.run(
            "MATCH (a:Person)-[r:RELATES]->(b:Person) RETURN elementId(r) as id, elementId(a) as source, elementId(b) as target, r.type as type"
        )
        relationships = []
        for record in rels_result:
            relationships.append({
                'id': record['id'],
                'source': record['source'],
                'target': record['target'],
                'type': record['type']
            })

        return {'nodes': nodes, 'relationships': relationships}

def neo4j_get_graph_specific(query: str = None, k: int = 6):
    # 为 AI 输出只提供自然语言语料（人物描述汇总）及人物间的关系描述（不包含任何 elementId/编号）
    # 如果提供 query，则执行一个简单的 RAG 检索（基于关键词重叠），返回检索到的证据
    with neo4j_driver.session() as session:
        # 查询所有人物节点并构建自然语言语料（去掉 elementId）
        persons_result = session.run(
            "MATCH (p:Person) RETURN elementId(p) as id, p.name as name, properties(p) as props"
        )
        corpus = []
        persons = {}
        for record in persons_result:
            pid = record['id']
            name = record.get('name') or (record['props'].get('name') if record.get('props') else None)
            props = record.get('props') or {}
            persons[pid] = name

            parts = []
            if name:
                parts.append(f"姓名：{name}")
            if 'occupation' in props and props.get('occupation'):
                parts.append(f"职业：{props.get('occupation')}")
            if 'age' in props and props.get('age'):
                parts.append(f"年龄：{props.get('age')}")
            # 优先使用 description、bio 或 summary 等字段作为自然语言描述
            desc = props.get('description') or props.get('bio') or props.get('summary') or ''
            if desc:
                parts.append(f"描述：{desc}")

            # 构造一句话语料（不包含 elementId）
            if parts:
                text = '；'.join(parts)
            else:
                text = name or ''
            corpus.append(text)

        # 获取人物之间的关系并构建自然语言描述（使用姓名，不暴露编号）
        rels_result = session.run(
            "MATCH (a:Person)-[r]->(b:Person) RETURN elementId(r) as id, elementId(a) as source, elementId(b) as target, type(r) as rel_label, properties(r) as props"
        )
        relationships = []
        for record in rels_result:
            sid = record['source']
            tid = record['target']
            sname = persons.get(sid) or '未知人物'
            tname = persons.get(tid) or '未知人物'
            props = record.get('props') or {}
            # 优先使用关系属性中的 type 字段（如有），否则使用关系的标签名（rel_label）
            rtype = props.get('type') or record.get('rel_label') or ''
            rel_text = f"{sname} 与 {tname} 的关系：{rtype}"
            note = props.get('note') or props.get('description') or props.get('summary')
            if note:
                rel_text += f"；说明：{note}"
            relationships.append(rel_text)

        result = {'corpus': corpus, 'relationships': relationships}

        if query:
            # 简单检索：关键词重叠计数（在已清洗的自然语言语料上进行）
            q_tokens = set(tokenize(query))
            scores = []
            for idx, text in enumerate(corpus):
                t_tokens = set(tokenize(text))
                score = len(q_tokens & t_tokens)
                scores.append((score, idx, text))
            scores.sort(key=lambda x: x[0], reverse=True)
            retrieved = [t for s, i, t in scores if s > 0][:k]
            if not retrieved:
                retrieved = corpus[:k]
            result['retrieved'] = retrieved

        return result

def neo4j_init_data(dataset="qing_history"):
    sample_data = load_sample_data(dataset)

    with neo4j_driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")

        id_to_name = {}
        for node in sample_data['nodes']:
            node_id = int(node['id']) if isinstance(node['id'], str) else node['id']
            id_to_name[node_id] = node['name']
            session.run(
                """
                CREATE (p:Person {name: $name, age: $age, occupation: $occupation, description: $description})
                """,
                name=node['name'],
                age=node.get('age'),
                occupation=node.get('occupation'),
                description=node.get('description', '')
            )

        for rel in sample_data['relationships']:
            source_id = int(rel['source']) if isinstance(rel['source'], str) else rel['source']
            target_id = int(rel['target']) if isinstance(rel['target'], str) else rel['target']

            source_name = id_to_name.get(source_id)
            target_name = id_to_name.get(target_id)

            if source_name and target_name:
                session.run(
                    """
                    MATCH (a:Person {name: $source_name}), (b:Person {name: $target_name})
                    CREATE (a)-[r:RELATES {type: $type}]->(b)
                    """,
                    source_name=source_name,
                    target_name=target_name,
                    type=rel.get('type', '关系')
                )
