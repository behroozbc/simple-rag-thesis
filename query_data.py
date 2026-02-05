import requests
import json
from collections import defaultdict


FLAMS_BASE = "https://mathhub.info"

#############################################
# Helper function to query the FLAMS SPARQL endpoint
############################################
def query_api(payload):
    query_url = f"{FLAMS_BASE}/api/backend/query"
    resp = requests.post(query_url, data=payload, headers={
            "Accept": "application/json"
        })
    resp.raise_for_status()
    return resp.json()["results"]["bindings"]


#############################################
# Fetch document uris of triggered query with ?s variable
#############################################
def fetch_doc_other_values(sparl_query):
    limit = 2000
    offset = 0
    data = []
    while True:
        query = f"""
        {sparl_query}
        LIMIT {limit}
        OFFSET {offset}
        """
        chunk = query_api(payload={"query": query})
        if not chunk:
            print(f"[done] no more data at offset {offset}")
            break
        for row in chunk:
            value = row["s"]["value"]
            data.append(value)

        print(f"[+] fetched {len(chunk)} rows (total {len(data)})")
        offset += limit

    return data

#############################################
# Fetch document reference symbols
#############################################
def fetch_document_symbols(document):
     query = f"""
        SELECT DISTINCT ?s WHERE {{
            <{document}> (ulo:contains|dc:hasPart)* ?p.
            ?p ulo:crossrefs ?s.
        }}
        order by ?s
        """
     return fetch_doc_other_values(query)

#############################################
# Fetch document reference symbols
#############################################
def fetch_document_reference_symbols(document):
     query = f"""
        SELECT DISTINCT ?s WHERE {{
            <{document}> (ulo:contains|dc:hasPart)* ?p.
            ?p ulo:crossrefs ?s.
        }}
        order by ?s
        """
     return fetch_doc_other_values(query)

#############################################
# Fetch document prerequisites
#############################################
def fetch_document_prerequisites(document):
     query = f"""
        SELECT DISTINCT ?s WHERE {{
            <{document}> (ulo:contains|dc:hasPart)* ?p.
            ?p ulo:crossrefs ?s.
            MINUS {{
                <{document}> (ulo:contains|dc:hasPart)* ?p.
                ?p ulo:defines ?s.
                }}
        }}
        order by ?s
        """
     return fetch_doc_other_values(query)

#############################################
# Fetch all documentURI's data using SPARQL
#############################################
def fetch_all_data_from_query_api():
    """POST a SPARQL query to FLAMS and return JSON."""
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
        chunk = query_api(payload={"query": query})

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
    fragment = []
    prerequisites = []
    symbols = []
    try: 
        fragment = fetch_document(node) 
    except Exception as e: 
        print(str(e))

    try:
        prerequisites= fetch_document_prerequisites(node)
    except Exception as ex:
        print(str(ex))

    try:
        symbols= fetch_document_symbols(node)
    except Exception as ex:
        print(str(ex))

    return {
        node:{
        "fragment": fragment,
        "prerequisites": prerequisites,
        "symbols": symbols,
        "children": [
            build_tree(child, children, visited.copy())
            for child in sorted(children.get(node, []))
        ]
        }
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

def fetch_document(uri):
    """
    HTML fragment representing of the given element URI    
    """
    print(f"Fetching document for URI: {uri}")
    resp = requests.get(
        f"{FLAMS_BASE}/content/fragment",
        params={"uri": uri}
    )
    resp.raise_for_status()
    return resp.json()

def main():
    
    print("=== Fetching SPARQL edges ===")
    edges = fetch_all_data_from_query_api()
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

    print("=== Writing full structured tree to file ===")
    with open("mathhub_tree.json", "w", encoding="utf-8") as f:
        json.dump(forest, f, indent=2)

    print("Wrote mathhub_tree.json")
    print("main")

if __name__ == "__main__":
    main()
