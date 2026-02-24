import json
import os
import sys
from typing import List, Dict, Any, Optional

import networkx as nx

try:
    from backend.neo4j_ops import neo4j_driver
except Exception:
    try:
        from neo4j_ops import neo4j_driver
    except Exception:
        # 作为最后手段，将项目根加入 sys.path 后重试
        _this_dir = os.path.dirname(__file__)
        _backend_dir = os.path.dirname(_this_dir)
        _project_root = os.path.dirname(_backend_dir)
        if _project_root not in sys.path:
            sys.path.insert(0, _project_root)
        try:
            from neo4j_ops import neo4j_driver
        except Exception as e:
            raise ImportError(f"无法导入 neo4j_ops：{e}")

# 尝试加载 sentence-transformers；不可用时回退到 sklearn 的 TF-IDF
try:
    from sentence_transformers import SentenceTransformer
    _has_sbert = True
except Exception:
    _has_sbert = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    _has_sklearn = True
except Exception:
    _has_sklearn = False


class GraphProcessor:
    """从 Neo4j 提取图并对节点文本进行向量化的工具类。

    行为：
    - 优先使用 `sentence-transformers` 生成语义向量；若不可用，则使用 TF-IDF 回退。
    - 使用 `networkx` 构建图并计算常见中心性指标。
    """

    def __init__(self, driver=None, embedding_model_name: str = "all-MiniLM-L6-v2"):
        self.driver = driver or neo4j_driver
        self.embedding_model_name = embedding_model_name
        self._embed_model = None
        if _has_sbert:
            try:
                self._embed_model = SentenceTransformer(self.embedding_model_name)
            except Exception:
                self._embed_model = None

    def fetch_nodes_and_rels(self) -> Dict[str, Any]:
        """从 Neo4j 获取人物节点与关系（返回原始属性）。"""
        with self.driver.session() as session:
            nodes_result = session.run(
                "MATCH (p:Person) RETURN elementId(p) as id, properties(p) as props"
            )
            nodes = []
            for r in nodes_result:
                rec = dict(r)
                nodes.append({'id': rec.get('id'), 'props': rec.get('props') or {}})

            rels_result = session.run(
                "MATCH (a:Person)-[r]->(b:Person) RETURN elementId(r) as id, elementId(a) as source, elementId(b) as target, type(r) as rel_label, properties(r) as props"
            )
            rels = []
            for r in rels_result:
                rec = dict(r)
                rels.append({
                    'id': rec.get('id'),
                    'source': rec.get('source'),
                    'target': rec.get('target'),
                    'label': rec.get('rel_label'),
                    'props': rec.get('props') or {}
                })

        return {'nodes': nodes, 'relationships': rels}

    def to_networkx(self, nodes: List[Dict[str, Any]], rels: List[Dict[str, Any]], directed: bool = False) -> nx.Graph:
        G = nx.DiGraph() if directed else nx.Graph()
        for n in nodes:
            nid = n.get('id')
            attrs = n.get('props', {}).copy()
            attrs['label'] = attrs.get('name') or attrs.get('label') or str(nid)
            G.add_node(nid, **attrs)

        for r in rels:
            s = r.get('source')
            t = r.get('target')
            edata = r.get('props', {}).copy()
            edata['label'] = r.get('label') or edata.get('type')
            if G.has_node(s) and G.has_node(t):
                G.add_edge(s, t, **edata)

        return G

    def compute_centrality(self, G: nx.Graph) -> Dict[str, Dict[Any, float]]:
        """计算一组常见的中心性指标并将其返回为字典。"""
        result = {}
        result['degree'] = dict(nx.degree(G))
        try:
            result['betweenness'] = nx.betweenness_centrality(G)
        except Exception:
            result['betweenness'] = {}
        try:
            result['closeness'] = nx.closeness_centrality(G)
        except Exception:
            result['closeness'] = {}
        try:
            if G.number_of_nodes() > 0:
                result['eigenvector'] = nx.eigenvector_centrality_numpy(G)
            else:
                result['eigenvector'] = {}
        except Exception:
            result['eigenvector'] = {}

        # 将中心性写回节点属性便于后续展示
        for metric, scores in result.items():
            if isinstance(scores, dict):
                for nid, sc in scores.items():
                    if G.has_node(nid):
                        G.nodes[nid][f'centrality_{metric}'] = float(sc)

        return result

    def embed_texts(self, texts: List[str]):
        """对文本列表进行向量化：优先使用 SBERT，否则回退到 TF-IDF。

        返回 numpy 数组或等效的二维列表（每行一个向量）。
        """
        cleaned = [t if t is not None else "" for t in texts]
        if self._embed_model is not None:
            try:
                emb = self._embed_model.encode(cleaned, show_progress_bar=False, convert_to_numpy=True)
                return emb
            except Exception:
                pass

        if _has_sklearn:
            vect = TfidfVectorizer(max_features=512)
            X = vect.fit_transform(cleaned).toarray()
            return X

        raise RuntimeError("没有可用的向量化工具：请安装 'sentence-transformers' 或 'scikit-learn'。")

    def embed_query(self, text: str):
        """为单条查询生成向量（返回一维向量）。"""
        res = self.embed_texts([text])
        try:
            return res[0]
        except Exception:
            return list(res[0])

    def load_embeddings_from_neo4j(self, prop_name: str = 'embedding') -> Dict[Any, List[float]]:
        """从 Neo4j 读取指定节点属性名的 embeddings，返回 id->vector 映射。

        会在无法连接 Neo4j 时抛出 RuntimeError。
        """
        if not self.driver:
            raise RuntimeError('Neo4j driver 未初始化，无法读取数据库')

        with self.driver.session() as session:
            try:
                res = session.run(
                    "MATCH (p:Person) WHERE exists(p[$prop]) RETURN elementId(p) as id, p[$prop] as vec",
                    prop=prop_name
                )
                out = {}
                for r in res:
                    rec = dict(r)
                    out[rec.get('id')] = rec.get('vec')
                return out
            except Exception as e:
                raise RuntimeError(f"从 Neo4j 读取 embeddings 失败: {e}")

    def load_embeddings_from_file(self, path: str) -> Dict[Any, List[float]]:
        """从 JSON 文件读取 embeddings（键为字符串 node id）。"""
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        out = {}
        for k, v in data.items():
            # 尝试将 key 转为 int
            try:
                ik = int(k)
            except Exception:
                ik = k
            out[ik] = v
        return out

    def node_embeddings(self, nodes: List[Dict[str, Any]], field_priority: Optional[List[str]] = None):
        """为每个节点生成文本表示并返回 embeddings 映射 node_id->vector。

        field_priority: 节点属性中按优先级使用的文本字段列表，缺省为 ['description','bio','summary','name']。
        """
        if field_priority is None:
            field_priority = ['description', 'bio', 'summary', 'name']

        texts = []
        ids = []
        for n in nodes:
            nid = n.get('id')
            props = n.get('props', {}) or {}
            text = ''
            for f in field_priority:
                v = props.get(f)
                if v:
                    text = str(v)
                    break
            if not text:
                text = props.get('name') or ''
            ids.append(nid)
            texts.append(text)

        embs = self.embed_texts(texts)

        # 返回 dict: id -> vector (list)
        out = {}
        try:
            for i, nid in enumerate(ids):
                out[nid] = embs[i].tolist()
        except Exception:
            # embs 可能已经是 list-of-lists
            for i, nid in enumerate(ids):
                out[nid] = list(embs[i])

        return out

    def export_graph_json(self, G: nx.Graph, path: str):
        from networkx.readwrite import json_graph
        data = json_graph.node_link_data(G)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def persist_embeddings_to_neo4j(self, emb_map: Dict[Any, List[float]], prop_name: str = 'embedding') -> None:
        """将节点向量写入 Neo4j 节点属性 `prop_name`。

        emb_map: dict of node_id -> vector (list of floats)
        如果没有可用的 Neo4j 连接会抛出 RuntimeError。
        """
        if not self.driver:
            raise RuntimeError('Neo4j driver 未初始化，无法写入数据库')

        # 构造参数列表
        rows = []
        for nid, vec in emb_map.items():
            try:
                rid = int(nid)
            except Exception:
                rid = nid
            rows.append({'id': rid, 'vec': vec})

        # 使用 UNWIND 批量写入
        with self.driver.session() as session:
            try:
                session.run(
                    "UNWIND $rows AS r\n"
                    "MATCH (p) WHERE elementId(p) = r.id\n"
                    "SET p[$prop] = r.vec",
                    rows=rows,
                    prop=prop_name
                )
            except Exception as e:
                raise RuntimeError(f"写入 Neo4j 失败: {e}")

    def save_embeddings_to_file(self, emb_map: Dict[Any, List[float]], path: str) -> None:
        """将 embeddings 导出为 JSON 文件，格式为 {node_id: [vec]}。"""
        # 确保目录存在
        d = os.path.dirname(path)
        if d and not os.path.exists(d):
            os.makedirs(d, exist_ok=True)
        # 转为可 JSON 序列化的结构（字符串化 key）
        serial = {str(k): v for k, v in emb_map.items()}
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(serial, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    gp = GraphProcessor()
    try:
        data = gp.fetch_nodes_and_rels()
        G = gp.to_networkx(data['nodes'], data['relationships'])
        c = gp.compute_centrality(G)
        print(f"Loaded graph: nodes={G.number_of_nodes()}, edges={G.number_of_edges()}")
    except Exception as e:
        print(f"GraphProcessor 示例运行异常（可能是环境/依赖或数据库）：{e}")
