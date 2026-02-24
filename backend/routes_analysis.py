
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta

from neo4j_ops import neo4j_driver

bp = Blueprint('analysis', __name__)


@bp.route('/api/graph/stats', methods=['GET'])
def get_graph_stats():
    with neo4j_driver.session() as session:
        try:
            result = session.run(
                """
                MATCH (p:Person)
                WITH count(p) as nodeCount
                OPTIONAL MATCH ()-[r]-()
                WITH nodeCount, count(r) as totalRelCount
                RETURN nodeCount, totalRelCount as relationshipCount
                """
            ).single()

            node_count = result['nodeCount']
            rel_count = result['relationshipCount']

            degree_result = session.run(
                """
                MATCH (p:Person)
                OPTIONAL MATCH (p)-[]-()
                WITH p, count(*) as degree
                RETURN avg(degree) as avgDegree, max(degree) as maxDegree, min(degree) as minDegree
                """
            ).single()

            avg_degree = degree_result['avgDegree'] or 0
            max_degree = degree_result['maxDegree'] or 0
            min_degree = degree_result['minDegree'] or 0

            if node_count <= 1:
                density = 0
            else:
                density = rel_count / (node_count * (node_count - 1))

            all_nodes_result = session.run(
                "MATCH (p:Person) RETURN elementId(p) as id, p.name as name, p.occupation as occupation"
            )
            all_nodes = {record['id']: {'id': record['id'], 'name': record['name'], 'occupation': record['occupation']}
                        for record in all_nodes_result}

            edges_result = session.run(
                "MATCH (a:Person)-[:RELATES]-(b:Person) RETURN DISTINCT elementId(a) as source, elementId(b) as target"
            )
            edges = [(record['source'], record['target']) for record in edges_result]

            parent = {node_id: node_id for node_id in all_nodes.keys()}

            def find(x):
                if parent[x] != x:
                    parent[x] = find(parent[x])
                return parent[x]

            def union(x, y):
                px, py = find(x), find(y)
                if px != py:
                    parent[px] = py

            for source, target in edges:
                if source in parent and target in parent:
                    union(source, target)

            component_groups = {}
            for node_id in all_nodes.keys():
                root = find(node_id)
                if root not in component_groups:
                    component_groups[root] = []
                component_groups[root].append(node_id)

            components = []
            for idx, (root, node_ids) in enumerate(sorted(component_groups.items(), key=lambda x: len(x[1]), reverse=True)):
                nodes = [all_nodes[node_id] for node_id in sorted(node_ids, key=lambda x: all_nodes[x]['name'])]
                components.append({'id': idx + 1, 'size': len(nodes), 'nodes': nodes})

            response = {
                'nodeCount': node_count,
                'relationshipCount': rel_count,
                'avgDegree': float(avg_degree),
                'maxDegree': max_degree,
                'minDegree': min_degree,
                'density': float(density),
                'components': components,
                'componentCount': len(components)
            }

            return jsonify(response), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@bp.route('/api/ranking/centrality', methods=['GET'])
def get_centrality_ranking():
    limit = request.args.get('limit', 20, type=int)
    with __import__('neo4j_ops').neo4j_driver.session() as session:
        try:
            max_result = session.run(
                """
                MATCH (p:Person)
                OPTIONAL MATCH (p)-[]-()
                WITH p, count(*) as degree
                RETURN max(degree) as maxDegree
                """
            ).single()

            max_degree = max_result['maxDegree'] or 1

            result = session.run(
                """
                MATCH (p:Person)
                OPTIONAL MATCH (p)-[]-()
                WITH p, count(*) as degree
                ORDER BY degree DESC
                LIMIT {limit}
                RETURN p.id as id, p.name as name, degree as degree, 
                       (CASE WHEN $maxDegree = 0 THEN 0 ELSE toFloat(degree) / $maxDegree END) as centrality
                """.format(limit=limit),
                {'maxDegree': max_degree}
            )
            ranking = [dict(record) for record in result]
            return jsonify(ranking), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500


@bp.route('/api/debug/relationships', methods=['GET'])
def debug_relationships():
    with __import__('neo4j_ops').neo4j_driver.session() as session:
        try:
            result = session.run(
                """
                MATCH ()-[r]->()
                RETURN type(r) as type, count(r) as count
                """
            )
            rel_types = [dict(record) for record in result]

            degree_result = session.run(
                """
                MATCH (p:Person)
                OPTIONAL MATCH (p)-[]-()
                WITH p.name as name, count(*) as degree
                OPTIONAL MATCH (p:Person {name: name})-[:RELATES]->()
                WITH name, degree, count(*) as outDegree
                OPTIONAL MATCH (p:Person {name: name})<-[:RELATES]-()
                WITH name, degree, outDegree, count(*) as inDegree
                RETURN name, degree, outDegree, inDegree
                ORDER BY degree DESC
                LIMIT 20
                """
            )
            degree_dist = [dict(record) for record in degree_result]

            zero_degree = session.run(
                """
                MATCH (p:Person)
                OPTIONAL MATCH (p)-[]-()
                WITH p, count(*) as degree
                WHERE degree = 0
                RETURN count(p) as zeroDegreeCount
                """
            ).single()

            total_rels = session.run(
                """
                MATCH ()-[r]->()
                RETURN count(r) as totalRels
                """
            ).single()

            return jsonify({
                'relationshipTypes': rel_types,
                'personDegrees': degree_dist,
                'zeroDegreeCount': zero_degree['zeroDegreeCount'],
                'totalRelationships': total_rels['totalRels']
            }), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500


@bp.route('/api/network/centrality', methods=['GET'])
def get_centrality():
    metric = request.args.get('metric', 'degree')
    limit = request.args.get('limit', default=10, type=int)
    with __import__('neo4j_ops').neo4j_driver.session() as session:
        if metric == 'degree':
            result = session.run(
                """
                MATCH (p:Person)
                WITH p, size([(p)-[]-() | 1]) as degree
                RETURN elementId(p) as id, p.name as name, degree
                ORDER BY degree DESC
                LIMIT $limit
                """,
                limit=limit
            )
        elif metric == 'betweenness':
            result = session.run(
                """
                MATCH (p:Person)
                WITH p, 
                     size([(p)-[*]-(other:Person) WHERE p <> other | 1]) as pathCount
                RETURN elementId(p) as id, p.name as name, pathCount as betweenness
                ORDER BY betweenness DESC
                LIMIT $limit
                """,
                limit=limit
            )
        elif metric == 'closeness':
            result = session.run(
                """
                MATCH (p:Person)
                WITH p, 
                     avg(size([(p)-[*]-(other:Person) WHERE p <> other | 1])) as avgDistance
                WHERE avgDistance > 0
                RETURN elementId(p) as id, p.name as name, 
                       1.0 / avgDistance as closeness
                ORDER BY closeness DESC
                LIMIT $limit
                """,
                limit=limit
            )
        else:
            return jsonify({'error': '不支持的中心性指标'}), 400

        nodes = [dict(record) for record in result]
        return jsonify({'metric': metric, 'nodes': nodes})


@bp.route('/api/network/communities', methods=['GET'])
def detect_communities():
    with __import__('neo4j_ops').neo4j_driver.session() as session:
        result = session.run(
            """
            MATCH (p:Person)
            OPTIONAL MATCH (p)-[r:RELATES*]-(connected:Person)
            WITH p, collect(DISTINCT connected) + [p] as component
            WITH component, size(component) as size
            WHERE size > 0
            UNWIND component as person
            WITH component, size, collect({
                id: elementId(person), 
                name: person.name,
                age: person.age,
                occupation: person.occupation
            }) as members
            RETURN members, size
            ORDER BY size DESC
            """
        )

        communities = []
        seen_members = set()
        for record in result:
            members = record['members']
            member_ids = tuple(sorted([m['id'] for m in members]))
            if member_ids not in seen_members:
                seen_members.add(member_ids)
                communities.append({'size': record['size'], 'members': members})

        return jsonify({'totalCommunities': len(communities), 'communities': communities})


@bp.route('/api/network/triangles', methods=['GET'])
def find_triangles():
    with __import__('neo4j_ops').neo4j_driver.session() as session:
        result = session.run(
            """
            MATCH (a:Person)-[r1:RELATES]-(b:Person)-[r2:RELATES]-(c:Person)-[r3:RELATES]-(a)
            WHERE elementId(a) < elementId(b) AND elementId(b) < elementId(c)
            RETURN DISTINCT
                elementId(a) as id_a, a.name as name_a,
                elementId(b) as id_b, b.name as name_b,
                elementId(c) as id_c, c.name as name_c,
                r1.type as type_ab, r2.type as type_bc, r3.type as type_ca
            LIMIT 50
            """
        )
        triangles = [dict(record) for record in result]
        return jsonify({'count': len(triangles), 'triangles': triangles})


@bp.route('/api/network/influence', methods=['GET'])
def calculate_influence():
    person_id = request.args.get('id')
    depth = request.args.get('depth', default=3, type=int)
    if not person_id:
        return jsonify({'error': 'ID不能为空'}), 400
    with __import__('neo4j_ops').neo4j_driver.session() as session:
        result = session.run(
            f"""
            MATCH path = (start:Person)-[*1..{depth}]-(influenced:Person)
            WHERE elementId(start) = $person_id
            WITH influenced, 
                 min(length(path)) as distance,
                 count(DISTINCT path) as pathCount
            RETURN elementId(influenced) as id, 
                   influenced.name as name,
                   distance,
                   pathCount,
                   1.0 / distance as influence
            ORDER BY influence DESC, pathCount DESC
            LIMIT 20
            """,
            person_id=person_id
        )
        influenced = [dict(record) for record in result]
        return jsonify({'sourceId': person_id, 'depth': depth, 'influencedNodes': influenced})


@bp.route('/api/network/all-paths', methods=['GET'])
def find_all_paths():
    start_id = request.args.get('start')
    end_id = request.args.get('end')
    max_length = request.args.get('maxLength', default=4, type=int)
    if not start_id or not end_id:
        return jsonify({'error': '起点和终点ID不能为空'}), 400
    with __import__('neo4j_ops').neo4j_driver.session() as session:
        result = session.run(
            f"""
            MATCH path = (a:Person)-[*1..{max_length}]-(b:Person)
            WHERE elementId(a) = $start AND elementId(b) = $end
            WITH path, length(path) as pathLength, 
                 [node in nodes(path) | {{id: elementId(node), name: node.name}}] as pathNodes,
                 [rel in relationships(path) | rel.type] as relTypes
            RETURN pathLength, pathNodes, relTypes
            ORDER BY pathLength
            LIMIT 10
            """,
            start=start_id,
            end=end_id
        )
        paths = [dict(record) for record in result]
        return jsonify({'start': start_id, 'end': end_id, 'totalPaths': len(paths), 'paths': paths})


@bp.route('/api/network/recommend', methods=['GET'])
def recommend_connections():
    person_id = request.args.get('id')
    if not person_id:
        return jsonify({'error': 'ID不能为空'}), 400
    with __import__('neo4j_ops').neo4j_driver.session() as session:
        result = session.run(
            """
            MATCH (p:Person)-[:RELATES*2]-(recommended:Person)
            WHERE elementId(p) = $person_id 
              AND NOT (p)-[:RELATES]-(recommended)
              AND p <> recommended
            WITH recommended, count(*) as mutualFriends
            MATCH (recommended)-[:RELATES]-(mutual:Person)-[:RELATES]-(p:Person)
            WHERE elementId(p) = $person_id
            WITH recommended, mutualFriends, collect(DISTINCT mutual.name) as mutualNames
            RETURN elementId(recommended) as id,
                   recommended.name as name,
                   recommended.age as age,
                   recommended.occupation as occupation,
                   mutualFriends,
                   mutualNames[0..5] as mutualFriendNames
            ORDER BY mutualFriends DESC
            LIMIT 10
            """,
            person_id=person_id
        )
        recommendations = [dict(record) for record in result]
        return jsonify({'personId': person_id, 'recommendations': recommendations})


@bp.route('/api/network/pattern', methods=['GET'])
def find_pattern():
    pattern_type = request.args.get('type', 'chain')
    with __import__('neo4j_ops').neo4j_driver.session() as session:
        if pattern_type == 'chain':
            result = session.run(
                """
                MATCH path = (a:Person)-[:RELATES]->(b:Person)-[:RELATES]->(c:Person)-[:RELATES]->(d:Person)
                WHERE a <> b AND b <> c AND c <> d AND a <> c AND a <> d AND b <> d
                RETURN 
                    [node in nodes(path) | {id: elementId(node), name: node.name}] as chain,
                    [rel in relationships(path) | rel.type] as relationTypes
                LIMIT 20
                """
            )
        elif pattern_type == 'star':
            result = session.run(
                """
                MATCH (center:Person)
                WITH center, [(center)-[:RELATES]-(leaf:Person) | leaf] as leaves
                WHERE size(leaves) >= 3
                RETURN elementId(center) as centerId, 
                       center.name as centerName,
                       [leaf in leaves | {id: elementId(leaf), name: leaf.name}] as connectedNodes,
                       size(leaves) as degree
                ORDER BY degree DESC
                LIMIT 10
                """
            )
        elif pattern_type == 'cycle':
            result = session.run(
                """
                MATCH path = (a:Person)-[:RELATES*3..5]-(a)
                WHERE length(path) >= 3
                WITH path, 
                     [node in nodes(path) | {id: elementId(node), name: node.name}] as cycle
                RETURN DISTINCT cycle, length(path) as cycleLength
                LIMIT 20
                """
            )
        else:
            return jsonify({'error': '不支持的模式类型'}), 400

        patterns = [dict(record) for record in result]
        return jsonify({'patternType': pattern_type, 'count': len(patterns), 'patterns': patterns})


@bp.route('/api/network/similarity', methods=['GET'])
def calculate_similarity():
    person_id = request.args.get('id')
    if not person_id:
        return jsonify({'error': 'ID不能为空'}), 400
    with __import__('neo4j_ops').neo4j_driver.session() as session:
        result = session.run(
            """
            MATCH (p:Person) WHERE elementId(p) = $person_id
            MATCH (p)-[:RELATES]-(neighbor1:Person)
            WITH p, collect(DISTINCT neighbor1) as neighbors1
            
            MATCH (other:Person) WHERE other <> p
            MATCH (other)-[:RELATES]-(neighbor2:Person)
            WITH p, neighbors1, other, collect(DISTINCT neighbor2) as neighbors2
            
            WITH p, other, neighbors1, neighbors2,
                 [n in neighbors1 WHERE n in neighbors2] as common,
                 neighbors1 + [n in neighbors2 WHERE NOT n in neighbors1] as union
            WHERE size(common) > 0
            
            RETURN elementId(other) as id,
                   other.name as name,
                   other.occupation as occupation,
                   size(common) as commonNeighbors,
                   size(union) as totalNeighbors,
                   toFloat(size(common)) / size(union) as similarity
            ORDER BY similarity DESC
            LIMIT 10
            """,
            person_id=person_id
        )
        similar = [dict(record) for record in result]
        return jsonify({'personId': person_id, 'similarNodes': similar})


@bp.route('/api/network/bridges', methods=['GET'])
def find_bridges():
    with __import__('neo4j_ops').neo4j_driver.session() as session:
        result = session.run(
            """
            MATCH (a:Person)-[r:RELATES]-(b:Person)
            WITH a, b, r,
                 size([(a)-[:RELATES]-(other:Person) WHERE other <> b | 1]) as a_degree,
                 size([(b)-[:RELATES]-(other:Person) WHERE other <> a | 1]) as b_degree
            WHERE a_degree = 0 OR b_degree = 0
            RETURN elementId(a) as id_a, a.name as name_a,
                   elementId(b) as id_b, b.name as name_b,
                   r.type as relationType,
                   elementId(r) as relId
            LIMIT 20
            """
        )
        bridges = [dict(record) for record in result]
        return jsonify({'count': len(bridges), 'bridges': bridges})


@bp.route('/api/network/density', methods=['GET'])
def calculate_density():
    with __import__('neo4j_ops').neo4j_driver.session() as session:
        stats = session.run(
            """
            MATCH (p:Person)
            WITH count(p) as nodeCount
            MATCH ()-[r:RELATES]->()
            WITH nodeCount, count(r) as edgeCount
            WITH nodeCount, edgeCount,
                 toFloat(edgeCount) / (nodeCount * (nodeCount - 1)) as density
            
            MATCH (p:Person)
            OPTIONAL MATCH (p)-[:RELATES]-(neighbor:Person)
            WITH nodeCount, edgeCount, density, 
                 p, collect(DISTINCT neighbor) as neighbors
            WITH nodeCount, edgeCount, density,
                 avg(size(neighbors)) as avgDegree
            
            RETURN nodeCount, edgeCount, density, avgDegree
            """
        ).single()

        clustering = session.run(
            """
            MATCH (p:Person)-[:RELATES]-(neighbor:Person)
            WITH p, collect(DISTINCT neighbor) as neighbors
            WHERE size(neighbors) > 1
            UNWIND neighbors as n1
            UNWIND neighbors as n2
            WITH p, neighbors, n1, n2
            WHERE elementId(n1) < elementId(n2)
            OPTIONAL MATCH (n1)-[r:RELATES]-(n2)
            WITH p, 
                 size(neighbors) as neighborCount,
                 count(r) as connectedPairs
            WITH p, neighborCount, connectedPairs,
                 toFloat(2 * connectedPairs) / (neighborCount * (neighborCount - 1)) as localClustering
            RETURN avg(localClustering) as avgClustering,
                   max(localClustering) as maxClustering
            """
        ).single()

        return jsonify({
            'nodeCount': stats['nodeCount'],
            'edgeCount': stats['edgeCount'],
            'density': float(stats['density']) if stats['density'] else 0,
            'avgDegree': float(stats['avgDegree']) if stats['avgDegree'] else 0,
            'avgClustering': float(clustering['avgClustering']) if clustering['avgClustering'] else 0,
            'maxClustering': float(clustering['maxClustering']) if clustering['maxClustering'] else 0
        })
from flask import Blueprint, request, jsonify
from datetime import datetime

from neo4j_ops import neo4j_get_graph

bp = Blueprint('analysis', __name__)


@bp.route('/api/graph/stats', methods=['GET'])
def get_graph_stats():
    from neo4j_ops import neo4j_driver
    try:
        with neo4j_driver.session() as session:
            result = session.run(
                """
                MATCH (p:Person)
                WITH count(p) as nodeCount
                OPTIONAL MATCH ()-[r]-()
                WITH nodeCount, count(r) as totalRelCount
                RETURN nodeCount, totalRelCount as relationshipCount
                """
            ).single()

            node_count = result['nodeCount']
            rel_count = result['relationshipCount']

            degree_result = session.run(
                """
                MATCH (p:Person)
                OPTIONAL MATCH (p)-[]-()
                WITH p, count(*) as degree
                RETURN avg(degree) as avgDegree, max(degree) as maxDegree, min(degree) as minDegree
                """
            ).single()

            avg_degree = degree_result['avgDegree'] or 0
            max_degree = degree_result['maxDegree'] or 0
            min_degree = degree_result['minDegree'] or 0

            if node_count <= 1:
                density = 0
            else:
                density = rel_count / (node_count * (node_count - 1))

            all_nodes_result = session.run(
                "MATCH (p:Person) RETURN elementId(p) as id, p.name as name, p.occupation as occupation"
            )
            all_nodes = {record['id']: {'id': record['id'], 'name': record['name'], 'occupation': record['occupation']} 
                        for record in all_nodes_result}

            edges_result = session.run(
                "MATCH (a:Person)-[:RELATES]-(b:Person) RETURN DISTINCT elementId(a) as source, elementId(b) as target"
            )
            edges = [(record['source'], record['target']) for record in edges_result]

            parent = {node_id: node_id for node_id in all_nodes.keys()}

            def find(x):
                if parent[x] != x:
                    parent[x] = find(parent[x])
                return parent[x]

            def union(x, y):
                px, py = find(x), find(y)
                if px != py:
                    parent[px] = py

            for source, target in edges:
                if source in parent and target in parent:
                    union(source, target)

            component_groups = {}
            for node_id in all_nodes.keys():
                root = find(node_id)
                if root not in component_groups:
                    component_groups[root] = []
                component_groups[root].append(node_id)

            components = []
            for idx, (root, node_ids) in enumerate(sorted(component_groups.items(), key=lambda x: len(x[1]), reverse=True)):
                nodes = [all_nodes[node_id] for node_id in sorted(node_ids, key=lambda x: all_nodes[x]['name'])]
                components.append({'id': idx + 1, 'size': len(nodes), 'nodes': nodes})

            response = {
                'nodeCount': node_count,
                'relationshipCount': rel_count,
                'avgDegree': float(avg_degree),
                'maxDegree': max_degree,
                'minDegree': min_degree,
                'density': float(density),
                'components': components,
                'componentCount': len(components)
            }

            return jsonify(response), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/ranking/centrality', methods=['GET'])
def get_centrality_ranking():
    limit = request.args.get('limit', 20, type=int)
    from neo4j_ops import neo4j_driver
    try:
        with neo4j_driver.session() as session:
            max_result = session.run(
                """
                MATCH (p:Person)
                OPTIONAL MATCH (p)-[]-()
                WITH p, count(*) as degree
                RETURN max(degree) as maxDegree
                """
            ).single()
            max_degree = max_result['maxDegree'] or 1
            result = session.run(
                """
                MATCH (p:Person)
                OPTIONAL MATCH (p)-[]-()
                WITH p, count(*) as degree
                ORDER BY degree DESC
                LIMIT {limit}
                RETURN p.id as id, p.name as name, degree as degree, 
                       (CASE WHEN $maxDegree = 0 THEN 0 ELSE toFloat(degree) / $maxDegree END) as centrality
                """.format(limit=limit),
                {'maxDegree': max_degree}
            )
            ranking = [dict(record) for record in result]
            return jsonify(ranking), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/debug/relationships', methods=['GET'])
def debug_relationships():
    from neo4j_ops import neo4j_driver
    try:
        with neo4j_driver.session() as session:
            result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as type, count(r) as count
                """)
            rel_types = [dict(record) for record in result]

            degree_result = session.run("""
                MATCH (p:Person)
                OPTIONAL MATCH (p)-[]-()
                WITH p.name as name, count(*) as degree
                OPTIONAL MATCH (p:Person {name: name})-[:RELATES]->()
                WITH name, degree, count(*) as outDegree
                OPTIONAL MATCH (p:Person {name: name})<-[:RELATES]-()
                WITH name, degree, outDegree, count(*) as inDegree
                RETURN name, degree, outDegree, inDegree
                ORDER BY degree DESC
                LIMIT 20
                """)
            degree_dist = [dict(record) for record in degree_result]

            zero_degree = session.run("""
                MATCH (p:Person)
                OPTIONAL MATCH (p)-[]-()
                WITH p, count(*) as degree
                WHERE degree = 0
                RETURN count(p) as zeroDegreeCount
                """).single()

            total_rels = session.run("""
                MATCH ()-[r]->()
                RETURN count(r) as totalRels
                """).single()

            return jsonify({
                'relationshipTypes': rel_types,
                'personDegrees': degree_dist,
                'zeroDegreeCount': zero_degree['zeroDegreeCount'],
                'totalRelationships': total_rels['totalRels']
            }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/network/centrality', methods=['GET'])
def get_centrality():
    metric = request.args.get('metric', 'degree')
    limit = request.args.get('limit', default=10, type=int)
    from neo4j_ops import neo4j_driver
    with neo4j_driver.session() as session:
        if metric == 'degree':
            result = session.run(
                """
                MATCH (p:Person)
                WITH p, size([(p)-[]-() | 1]) as degree
                RETURN elementId(p) as id, p.name as name, degree
                ORDER BY degree DESC
                LIMIT $limit
                """,
                limit=limit
            )
        elif metric == 'betweenness':
            result = session.run(
                """
                MATCH (p:Person)
                WITH p, 
                     size([(p)-[*]-(other:Person) WHERE p <> other | 1]) as pathCount
                RETURN elementId(p) as id, p.name as name, pathCount as betweenness
                ORDER BY betweenness DESC
                LIMIT $limit
                """,
                limit=limit
            )
        elif metric == 'closeness':
            result = session.run(
                """
                MATCH (p:Person)
                WITH p, 
                     avg(size([(p)-[*]-(other:Person) WHERE p <> other | 1])) as avgDistance
                WHERE avgDistance > 0
                RETURN elementId(p) as id, p.name as name, 
                       1.0 / avgDistance as closeness
                ORDER BY closeness DESC
                LIMIT $limit
                """,
                limit=limit
            )
        else:
            return jsonify({'error': '不支持的中心性指标'}), 400
        nodes = [dict(record) for record in result]
        return jsonify({'metric': metric, 'nodes': nodes})


@bp.route('/api/network/communities', methods=['GET'])
def detect_communities():
    from neo4j_ops import neo4j_driver
    with neo4j_driver.session() as session:
        result = session.run(
            """
            MATCH (p:Person)
            OPTIONAL MATCH (p)-[r:RELATES*]-(connected:Person)
            WITH p, collect(DISTINCT connected) + [p] as component
            WITH component, size(component) as size
            WHERE size > 0
            UNWIND component as person
            WITH component, size, collect({
                id: elementId(person), 
                name: person.name,
                age: person.age,
                occupation: person.occupation
            }) as members
            RETURN members, size
            ORDER BY size DESC
            """
        )
        communities = []
        seen_members = set()
        for record in result:
            members = record['members']
            member_ids = tuple(sorted([m['id'] for m in members]))
            if member_ids not in seen_members:
                seen_members.add(member_ids)
                communities.append({'size': record['size'], 'members': members})
        return jsonify({'totalCommunities': len(communities), 'communities': communities})


@bp.route('/api/network/triangles', methods=['GET'])
def find_triangles():
    from neo4j_ops import neo4j_driver
    with neo4j_driver.session() as session:
        result = session.run(
            """
            MATCH (a:Person)-[r1:RELATES]-(b:Person)-[r2:RELATES]-(c:Person)-[r3:RELATES]-(a)
            WHERE elementId(a) < elementId(b) AND elementId(b) < elementId(c)
            RETURN DISTINCT
                elementId(a) as id_a, a.name as name_a,
                elementId(b) as id_b, b.name as name_b,
                elementId(c) as id_c, c.name as name_c,
                r1.type as type_ab, r2.type as type_bc, r3.type as type_ca
            LIMIT 50
            """
        )
        triangles = [dict(record) for record in result]
        return jsonify({'count': len(triangles), 'triangles': triangles})


@bp.route('/api/network/influence', methods=['GET'])
def calculate_influence():
    person_id = request.args.get('id')
    depth = request.args.get('depth', default=3, type=int)
    if not person_id:
        return jsonify({'error': 'ID不能为空'}), 400
    from neo4j_ops import neo4j_driver
    with neo4j_driver.session() as session:
        result = session.run(
            f"""
            MATCH path = (start:Person)-[*1..{depth}]-(influenced:Person)
            WHERE elementId(start) = $person_id
            WITH influenced, 
                 min(length(path)) as distance,
                 count(DISTINCT path) as pathCount
            RETURN elementId(influenced) as id, 
                   influenced.name as name,
                   distance,
                   pathCount,
                   1.0 / distance as influence
            ORDER BY influence DESC, pathCount DESC
            LIMIT 20
            """,
            person_id=person_id
        )
        influenced = [dict(record) for record in result]
        return jsonify({'sourceId': person_id, 'depth': depth, 'influencedNodes': influenced})


@bp.route('/api/network/all-paths', methods=['GET'])
def find_all_paths():
    start_id = request.args.get('start')
    end_id = request.args.get('end')
    max_length = request.args.get('maxLength', default=4, type=int)
    if not start_id or not end_id:
        return jsonify({'error': '起点和终点ID不能为空'}), 400
    from neo4j_ops import neo4j_driver
    with neo4j_driver.session() as session:
        result = session.run(
            f"""
            MATCH path = (a:Person)-[*1..{max_length}]-(b:Person)
            WHERE elementId(a) = $start AND elementId(b) = $end
            WITH path, length(path) as pathLength, 
                 [node in nodes(path) | {{id: elementId(node), name: node.name}}] as pathNodes,
                 [rel in relationships(path) | rel.type] as relTypes
            RETURN pathLength, pathNodes, relTypes
            ORDER BY pathLength
            LIMIT 10
            """,
            start=start_id,
            end=end_id
        )
        paths = [dict(record) for record in result]
        return jsonify({'start': start_id, 'end': end_id, 'totalPaths': len(paths), 'paths': paths})


@bp.route('/api/network/recommend', methods=['GET'])
def recommend_connections():
    person_id = request.args.get('id')
    if not person_id:
        return jsonify({'error': 'ID不能为空'}), 400
    from neo4j_ops import neo4j_driver
    with neo4j_driver.session() as session:
        result = session.run(
            """
            MATCH (p:Person)-[:RELATES*2]-(recommended:Person)
            WHERE elementId(p) = $person_id 
              AND NOT (p)-[:RELATES]-(recommended)
              AND p <> recommended
            WITH recommended, count(*) as mutualFriends
            MATCH (recommended)-[:RELATES]-(mutual:Person)-[:RELATES]-(p:Person)
            WHERE elementId(p) = $person_id
            WITH recommended, mutualFriends, collect(DISTINCT mutual.name) as mutualNames
            RETURN elementId(recommended) as id,
                   recommended.name as name,
                   recommended.age as age,
                   recommended.occupation as occupation,
                   mutualFriends,
                   mutualNames[0..5] as mutualFriendNames
            ORDER BY mutualFriends DESC
            LIMIT 10
            """,
            person_id=person_id
        )
        recommendations = [dict(record) for record in result]
        return jsonify({'personId': person_id, 'recommendations': recommendations})


@bp.route('/api/network/pattern', methods=['GET'])
def find_pattern():
    pattern_type = request.args.get('type', 'chain')
    from neo4j_ops import neo4j_driver
    with neo4j_driver.session() as session:
        if pattern_type == 'chain':
            result = session.run(
                """
                MATCH path = (a:Person)-[:RELATES]->(b:Person)-[:RELATES]->(c:Person)-[:RELATES]->(d:Person)
                WHERE a <> b AND b <> c AND c <> d AND a <> c AND a <> d AND b <> d
                RETURN 
                    [node in nodes(path) | {id: elementId(node), name: node.name}] as chain,
                    [rel in relationships(path) | rel.type] as relationTypes
                LIMIT 20
                """
            )
        elif pattern_type == 'star':
            result = session.run(
                """
                MATCH (center:Person)
                WITH center, [(center)-[:RELATES]-(leaf:Person) | leaf] as leaves
                WHERE size(leaves) >= 3
                RETURN elementId(center) as centerId, 
                       center.name as centerName,
                       [leaf in leaves | {id: elementId(leaf), name: leaf.name}] as connectedNodes,
                       size(leaves) as degree
                ORDER BY degree DESC
                LIMIT 10
                """
            )
        elif pattern_type == 'cycle':
            result = session.run(
                """
                MATCH path = (a:Person)-[:RELATES*3..5]-(a)
                WHERE length(path) >= 3
                WITH path, 
                     [node in nodes(path) | {id: elementId(node), name: node.name}] as cycle
                RETURN DISTINCT cycle, length(path) as cycleLength
                LIMIT 20
                """
            )
        else:
            return jsonify({'error': '不支持的模式类型'}), 400
        patterns = [dict(record) for record in result]
        return jsonify({'patternType': pattern_type, 'count': len(patterns), 'patterns': patterns})


@bp.route('/api/network/similarity', methods=['GET'])
def calculate_similarity():
    person_id = request.args.get('id')
    if not person_id:
        return jsonify({'error': 'ID不能为空'}), 400
    from neo4j_ops import neo4j_driver
    with neo4j_driver.session() as session:
        result = session.run(
            """
            MATCH (p:Person) WHERE elementId(p) = $person_id
            MATCH (p)-[:RELATES]-(neighbor1:Person)
            WITH p, collect(DISTINCT neighbor1) as neighbors1
            
            MATCH (other:Person) WHERE other <> p
            MATCH (other)-[:RELATES]-(neighbor2:Person)
            WITH p, neighbors1, other, collect(DISTINCT neighbor2) as neighbors2
            
            WITH p, other, neighbors1, neighbors2,
                 [n in neighbors1 WHERE n in neighbors2] as common,
                 neighbors1 + [n in neighbors2 WHERE NOT n in neighbors1] as union
            WHERE size(common) > 0
            
            RETURN elementId(other) as id,
                   other.name as name,
                   other.occupation as occupation,
                   size(common) as commonNeighbors,
                   size(union) as totalNeighbors,
                   toFloat(size(common)) / size(union) as similarity
            ORDER BY similarity DESC
            LIMIT 10
            """,
            person_id=person_id
        )
        similar = [dict(record) for record in result]
        return jsonify({'personId': person_id, 'similarNodes': similar})


@bp.route('/api/network/bridges', methods=['GET'])
def find_bridges():
    from neo4j_ops import neo4j_driver
    with neo4j_driver.session() as session:
        result = session.run(
            """
            MATCH (a:Person)-[r:RELATES]-(b:Person)
            WITH a, b, r,
                 size([(a)-[:RELATES]-(other:Person) WHERE other <> b | 1]) as a_degree,
                 size([(b)-[:RELATES]-(other:Person) WHERE other <> a | 1]) as b_degree
            WHERE a_degree = 0 OR b_degree = 0
            RETURN elementId(a) as id_a, a.name as name_a,
                   elementId(b) as id_b, b.name as name_b,
                   r.type as relationType,
                   elementId(r) as relId
            LIMIT 20
            """
        )
        bridges = [dict(record) for record in result]
        return jsonify({'count': len(bridges), 'bridges': bridges})


@bp.route('/api/network/density', methods=['GET'])
def calculate_density():
    from neo4j_ops import neo4j_driver
    with neo4j_driver.session() as session:
        stats = session.run(
            """
            MATCH (p:Person)
            WITH count(p) as nodeCount
            MATCH ()-[r:RELATES]->()
            WITH nodeCount, count(r) as edgeCount
            WITH nodeCount, edgeCount,
                 toFloat(edgeCount) / (nodeCount * (nodeCount - 1)) as density
            
            MATCH (p:Person)
            OPTIONAL MATCH (p)-[:RELATES]-(neighbor:Person)
            WITH nodeCount, edgeCount, density, 
                 p, collect(DISTINCT neighbor) as neighbors
            WITH nodeCount, edgeCount, density,
                 avg(size(neighbors)) as avgDegree
            
            RETURN nodeCount, edgeCount, density, avgDegree
            """
        ).single()

        clustering = session.run(
            """
            MATCH (p:Person)-[:RELATES]-(neighbor:Person)
            WITH p, collect(DISTINCT neighbor) as neighbors
            WHERE size(neighbors) > 1
            UNWIND neighbors as n1
            UNWIND neighbors as n2
            WITH p, neighbors, n1, n2
            WHERE elementId(n1) < elementId(n2)
            OPTIONAL MATCH (n1)-[r:RELATES]-(n2)
            WITH p, 
                 size(neighbors) as neighborCount,
                 count(r) as connectedPairs
            WITH p, neighborCount, connectedPairs,
                 toFloat(2 * connectedPairs) / (neighborCount * (neighborCount - 1)) as localClustering
            RETURN avg(localClustering) as avgClustering,
                   max(localClustering) as maxClustering
            """
        ).single()

        return jsonify({
            'nodeCount': stats['nodeCount'],
            'edgeCount': stats['edgeCount'],
            'density': float(stats['density']) if stats['density'] else 0,
            'avgDegree': float(stats['avgDegree']) if stats['avgDegree'] else 0,
            'avgClustering': float(clustering['avgClustering']) if clustering['avgClustering'] else 0,
            'maxClustering': float(clustering['maxClustering']) if clustering['maxClustering'] else 0
        })
