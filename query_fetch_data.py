import requests
import json
from collections import defaultdict, OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from bs4 import BeautifulSoup
import re


FLAMS_BASE = "https://mathhub.info"

#############################################
# HTML → Clean text (strip at fetch time)
#############################################
NOISE_CLASSES = {
    "rustex-vskip", "rustex-hskip", "rustex-box-vv", "rustex-box-vhc",
    "rustex-box-after-v", "rustex-scalewidth", "rustex-box-vh",
    "rustex-box-hh", "rustex-vbox-to",
}
 
def clean_html_to_text(html: str) -> dict:
    """
    Extract only semantic content from rustex HTML.
    Returns a dict with 'term', 'definition', and 'text' keys.
    """
    if not html or not isinstance(html, str):
        return None
 
    soup = BeautifulSoup(html, "html.parser")
 
    # 1. Remove layout/noise divs by class
    for tag in soup.find_all(True):
        classes = tag.get("class", [])
        if any(c in NOISE_CLASSES for c in classes):
            tag.decompose()
 
    # 2. Remove all display:none elements (counter spans, style spans)
    for tag in soup.find_all(style=lambda s: s and "display:none" in s):
        tag.decompose()
 
    # 3. Remove <a> anchors that are just page markers (id only, no text)
    for tag in soup.find_all("a", id=True):
        if not tag.get_text(strip=True):
            tag.decompose()
 
    # 4. Extract the defined term
    definiendum = soup.find(attrs={"data-ftml-definiendum": True})
    term = definiendum.get_text(strip=True) if definiendum else ""
 
    # 5. Extract definition body
    definition_div = soup.find(attrs={"data-ftml-definition": True})
    definition_text = definition_div.get_text(separator=" ", strip=True) if definition_div else ""
 
    # 6. Fallback: get all remaining text if no semantic tags found
    if not definition_text:
        definition_text = soup.get_text(separator=" ", strip=True)
 
    # 7. Clean up artifacts: "ist . . ." means content is incomplete
    definition_text = re.sub(r"\s*\.\s*\.\s*\.\s*", " [incomplete] ", definition_text).strip()
    definition_text = re.sub(r"\s{2,}", " ", definition_text)
 
    if not term and not definition_text:
        return None
 
    return {
        "term": term,
        "text": f"Term: {term}\n{definition_text}".strip() if term else definition_text,
    }
 
 
def parse_content_field(raw_content):
    """
    Your content array: [uri, [links], html_string]
    Cleans HTML and returns only text. Returns None if nothing useful.
    """
    if not raw_content or not isinstance(raw_content, list) or len(raw_content) < 3:
        return None
 
    html = raw_content[2]
    if not isinstance(html, str):
        return None
 
    return clean_html_to_text(html)

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
     document = document.replace(" ","%20")
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
     document = document.replace(" ","%20")
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
     document = document.replace(" ","%20")
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
            nodes[p] = {"uri": p,"content": None, "symbols": [], "prerequisites": [], "children": [], "_child_set": set()}
        if c not in nodes:
            nodes[c] = {"uri": c, "content": None, "symbols": [], "prerequisites": [], "children": [], "_child_set": set()}
        if c not in nodes[p]["_child_set"]:
            nodes[p]["_child_set"].add(c)
            nodes[p]["children"].append(c)

    for n in nodes.values():
        n.pop("_child_set", None)
    return nodes


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

def fetch_all_documents(nodes, max_workers=32, per_uri_workers=32):
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

        raw = fetch_document(uri)
        if not raw:
            return uri, None, [], []
 
        # ---- Clean HTML at fetch time, never store raw HTML ----
        cleaned = parse_content_field(raw)
        content = cleaned["text"] if cleaned else None

        # try:
        #     content = fetch_document(uri)
        # except Exception:
        #     content = None

        # # If content missing, skip the other two calls
        # if not content:
        #     return uri, None, [], []
        
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

    return list(nodes.values())

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

if __name__ == "__main__":
    main()