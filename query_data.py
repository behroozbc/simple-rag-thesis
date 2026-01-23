import requests
import json
from collections import defaultdict


FLAMS_BASE = "https://mathhub.info"
COURSE_URI = (
    "http://mathhub.info"
    "?a=courses/FAU/AI/course"
    "&p=course/notes&d=notes1&l=en"
) 

def fetch_query_data():
    """POST a SPARQL query to FLAMS and return JSON."""
    url = f"{FLAMS_BASE}/api/backend/query"
    limit = 2000
    offset = 0

    all_edges = []

    while True:
        query = f"""
        SELECT DISTINCT ?parent ?child 
        WHERE {{
          GRAPH ?g {{
            ?parent ulo:contains ?child .
          }}
        }}
        ORDER BY ?parent ?child
        LIMIT {limit}
        OFFSET {offset}
        """
        payload = {"query": query}

        resp = requests.post(url, data=payload, headers={
            "Accept": "application/json"
        })
        resp.raise_for_status()

        chunk = resp.json()["results"]["bindings"]
        if len(all_edges) >= 50000:
            print(f"[done] no more data at offset {offset}")
            break

        if not chunk:
            print(f"[done] no more data at offset {offset}")
            break
        for row in chunk:
            parent = row["parent"]["value"]
            child = row["child"]["value"]
            all_edges.append((parent, child))

        print(f"[+] fetched {len(chunk)} rows (total {len(all_edges)})")
        offset += limit

    return all_edges

def build_graph(edges):
    children = defaultdict(set)
    parents = defaultdict(set)
    nodes = set()

    for p, c in edges:
        children[p].add(c)
        parents[c].add(p)
        nodes.add(p)
        nodes.add(c)

    return children, parents, nodes

############################################
# Find root nodes (Main parents)
############################################

def find_roots(children, parents):
    # roots = nodes that are parents but never children
    roots = []
    for p in children:
        if p not in parents:
            roots.append(p)
    return roots


############################################
# Build recursive tree
############################################

def build_tree(node, children, visited):
    if node in visited:
        return {"uri": node, "cycle": True}

    visited.add(node)
    
    # Fetch fragment for this node 
    try: 
        fragment = fetch_document(node) 
    except Exception as e: 
        fragment = {"error": str(e)}

    return {
        "uri": node,
        "fragment": fragment,
        "children": [
            build_tree(child, children, visited.copy())
            for child in sorted(children.get(node, []))
        ]
    }


############################################
# Pretty print tree (for debugging)
############################################

def print_tree(tree, indent=0, max_depth=10):
    if indent > max_depth:
        print("  " * indent + "...")
        return

    print("  " * indent + tree["uri"])
    for child in tree.get("children", []):
        print_tree(child, indent + 1, max_depth)


def fetch_fragment(uri, context_uri=None):
    """
    HTML fragment representing the given element URI    
    """
    resp = requests.get(
        f"{FLAMS_BASE}/content/fragment",
        params={"uri": uri, "context": context_uri}
    )
    resp.raise_for_status()
    return resp.json()
def fetch_document(uri):
    """
    HTML fragment representing the given element URI    
    """
    print(f"Fetching document for URI: {uri}")
    resp = requests.get(
        f"{FLAMS_BASE}/content/document",
        params={"uri": uri}
    )
    resp.raise_for_status()
    return resp.json()

def main():
    print("=== Fetching SPARQL edges ===")
    edges = fetch_query_data()
    print(f"Total edges: {len(edges)}")

    print("=== Building graph ===")
    children, parents, nodes = build_graph(edges)


    print("=== Finding root nodes ===")
    roots = find_roots(children, parents)
    print(f"Found {len(roots)} root nodes")

    # Optional: focus on flams://archives as main root
    main_roots = [r for r in roots if "flams://archives" in r]
    if main_roots:
        roots = main_roots
        print("Using flams://archives as root")

    print("=== Building trees ===")
    forest = []
    for r in roots:
        tree = build_tree(r, children, set())
        forest.append(tree)

    print("=== Example printed tree (depth-limited) ===")
    for tree in forest:
        print_tree(tree, max_depth=6)

    print("=== Writing full structured tree to file ===")
    with open("mathhub_tree_1.json", "w", encoding="utf-8") as f:
        json.dump(forest, f, indent=2)

    print("Wrote mathhub_tree_1.json")

    print("main")

if __name__ == "__main__":
    main()
