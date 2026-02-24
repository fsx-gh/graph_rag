from flask import Blueprint, request, jsonify
from openai import OpenAI
from neo4j_ops import neo4j_get_graph_specific
from graph_proc import GraphProcessor
import numpy as np
import json
import os  # 修复：缺少 os 导入

bp = Blueprint('ai', __name__, url_prefix='/api')

client = OpenAI(
    api_key="sk-728123a1afe64b4bbf86859c2b39deec",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

@bp.route('/ai_ask', methods=['POST'])
def ai_ask():
    data = request.get_json() or {}
    user_question = data.get('question', '你是谁？')
    gp = GraphProcessor()
    retrieved = None
    evidence_block = ''
    nodes_and_rels = {}
    nodes = []
    emb_map = None
    graph_info = {}

    try:
        nodes_and_rels = gp.fetch_nodes_and_rels()
        nodes = nodes_and_rels.get('nodes', [])

        try:
            emb_map = gp.load_embeddings_from_neo4j('embedding')
        except Exception:
            emb_map = None
        if not emb_map:
            try:
                emb_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'export', 'embeddings.json')
                emb_file = os.path.normpath(emb_file)
                emb_map = gp.load_embeddings_from_file(emb_file)
            except Exception:
                emb_map = None

        if emb_map:
            qv = gp.embed_query(user_question)
            qv = np.array(qv, dtype=float)
            sims = []
            id_to_node = {n['id']: n for n in nodes}
            for nid, vec in emb_map.items():
                try:
                    v = np.array(vec, dtype=float)
                    sim = float(np.dot(qv, v) / (np.linalg.norm(qv) * np.linalg.norm(v) + 1e-12))
                except Exception:
                    sim = 0.0
                sims.append((sim, nid))
            sims.sort(key=lambda x: x[0], reverse=True)
            top = [nid for s, nid in sims[:6] if nid in id_to_node]
            retrieved_texts = []
            for nid in top:
                n = id_to_node.get(nid, {})
                props = n.get('properties', {}) or {}  # 修复：应为 properties
                name = props.get('name') or props.get('label') or ''
                desc = props.get('description') or props.get('bio') or props.get('summary') or ''
                txt = f"姓名：{name}；描述：{desc}" if name or desc else str(nid)
                retrieved_texts.append(txt)
            if retrieved_texts:
                retrieved = retrieved_texts
                evidence_block = '\n'.join(retrieved)
        else:
            try:
                graph_info = neo4j_get_graph_specific(query=user_question, k=6)
            except Exception:
                graph_info = neo4j_get_graph_specific()
            retrieved = graph_info.get('retrieved') if isinstance(graph_info, dict) else None
            if retrieved:
                evidence_block = '\n'.join(retrieved)
            nodes = graph_info.get('corpus') if isinstance(graph_info, dict) else []

    except Exception as e:
        # 捕获 fetch_nodes_and_rels 失败
        nodes_and_rels = {}
        nodes = []
        emb_map = None

    try:
        graph_json = json.dumps(nodes_and_rels if nodes_and_rels else graph_info, ensure_ascii=False)
    except Exception:
        graph_json = '[]'
    user_prompt_parts = []
    if evidence_block:
        user_prompt_parts.append(f"参考证据（与问题最相关的句子）：\n{evidence_block}")
    user_prompt_parts.append(f"完整图语料（供参考）：\n{graph_json}")
    user_prompt_parts.append(f"用户问题：{user_question}")
    user_prompt = "\n\n".join(user_prompt_parts)

    try:
        completion = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是一个基于知识图谱的中文问答助手。输入是一份完整的图数据库导出（包含所有节点、标签、属性、关系及其属性）。"
                        " 严格规则：\n"
                        "1) 只能用简洁的中文自然语言回答，禁止以任何结构化格式（如 JSON、YAML、表格）输出答案。\n"
                        "2) 回答必须基于图中事实，不得凭空编造信息。可以做有限的合情合理推理，但不得引入图中不存在的实体。\n"
                        "3) 回答中请至少包含一条证据说明（例如：引用相关人物的描述或关系），以证明答案的正确性。\n"
                        "4) 若图中无法确定答案，应直接用中文说明无法确认并给出原因（例如：缺少相关节点/关系）。\n"
                        "5) 回答尽量简洁，先给结论，再用一两句说明依据。"
                        "6) 使用纯中文回答，禁止使用任何其他语言。"
                        "7) 禁止在回答中出现任何节点编号、id、elementId、编号等技术性内容，只能用自然语言描述。"
                    )
                },
                {"role": "user", "content": user_prompt},
            ],
        )
        answer = completion.choices[0].message.content if completion.choices else "无回答"
        # 后处理：自动去除节点号、id等技术性内容
        import re
        # 常见技术性内容正则
        answer = re.sub(r"[（(]?(节点|id|编号|elementId)[：: ]?\d+[)）]?", "", answer, flags=re.IGNORECASE)
        answer = re.sub(r"(节点|id|编号|elementId)[：: ]*\w+", "", answer, flags=re.IGNORECASE)
        # 去除多余空格和标点
        answer = re.sub(r"[，,。]{2,}", "。", answer)
        answer = answer.replace("  ", " ").strip()
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500