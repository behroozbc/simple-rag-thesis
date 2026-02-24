import requests
import json
from collections import defaultdict, OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache




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
            ?p ulo:defines ?s.
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
    edges = []

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
            edges.append((row["parent"]["value"], row["child"]["value"]))

        offset += limit
        print(f"[+] fetched {len(chunk)} rows (total edges {len(edges)})")

    return edges

def build_nodes_from_edges(edges):
    nodes = OrderedDict()
    for p, c in edges:
        if p not in nodes:
            nodes[p] = {"uri": p, "content": None, "symbols": [], "prerequisites": [], "children": [], "_child_set": set()}
        if c not in nodes:
            nodes[c] = {"uri": c, "content": None, "symbols": [], "prerequisites": [], "children": [], "_child_set": set()}
        if c not in nodes[p]["_child_set"]:
            nodes[p]["_child_set"].add(c)
            nodes[p]["children"].append(c)

    for n in nodes.values():
        n.pop("_child_set", None)
    return nodes

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

    if fragment:
        try:
            prerequisites= fetch_document_prerequisites(node)
        except Exception as ex:
            print(str(ex))
        
        try:
            symbols= fetch_document_reference_symbols(node)
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


@lru_cache(maxsize=200_000)
def fetch_document(uri):
    """
    HTML fragment representing of the given element URI    
    """
    print(f"Fetching document for URI: {uri}")
    try:
        resp = requests.get(
        f"{FLAMS_BASE}/content/fragment",
        params={"uri": uri}
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Error Fetching document for URI: {uri} - {str(e)}")
        return None


def fetch_all_symbols():
    return list(map(lambda x:x["x"]["value"],query_api({"query": "SELECT ?x WHERE { ?x rdf:type ulo:declaration .}"})))

def fetch_all_documents(nodes, max_workers=32, per_uri_workers=2):
    """
    nodes: dict uri -> node
    Fetch content once per uri, in parallel.
    """
    uris = list(nodes.keys())

    def fetch_symbols(uri):
        try:
            return fetch_document_reference_symbols(uri) or []
        except Exception:
            return []

    def fetch_prereqs(uri):
        try:
            return fetch_document_prerequisites(uri) or []
        except Exception:
            return []

    def work(uri):
        try:
            content = fetch_document(uri)
        except Exception:
            content = None

        # If content missing, skip the other two calls
        if not content:
            return uri, None, [], []
        
       # 2) symbols & prereqs in parallel (so they don't add sequential latency)
        with ThreadPoolExecutor(max_workers=per_uri_workers) as ex2:
            f_sym = ex2.submit(fetch_symbols, uri)
            f_pre = ex2.submit(fetch_prereqs, uri)
            symbols = f_sym.result()
            prereqs = f_pre.result()

        return uri, content, symbols, prereqs

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(work, uri) for uri in uris]
        for i, fut in enumerate(as_completed(futures), 1):
            uri, content, symbols, prereqs = fut.result()
            nodes[uri]["content"] = content
            nodes[uri]["symbols"] = symbols if symbols is not None else []
            nodes[uri]["prerequisites"] = prereqs if prereqs is not None else []
            if i % 1000 == 0:
                print(f"[docs] fetched {i}/{len(uris)}")

    return nodes

def main():

    print("=== Fetching SPARQL edges ===")
    edges = fetch_all_data_from_query_api()
    print(f"Total edges: {len(edges)}")

    nodes = build_nodes_from_edges(edges)
    nodes = fetch_all_documents(nodes, max_workers=32)

    with open("course_full_edges.json", "w", encoding="utf-8") as f:
        json.dump(edges, f)
    print("Wrote course_full_edges.json")

    with open("course_full.json", "w", encoding="utf-8") as f:
        json.dump(nodes, f)
    print("Wrote course_full.json")
    
    exit(0)
    exit()
    exit()




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
