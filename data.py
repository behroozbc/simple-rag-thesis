import requests
from urllib.parse import urlencode, quote_plus
import xml.etree.ElementTree as ET
import json
import re

FLAMS_BASE = "https://mathhub.info"
COURSE_URI = (
    "http://mathhub.info"
    "?a=courses/FAU/AI/course"
    "&p=course/notes&d=notes1&l=en"
)

def fetch_toc(uri: str):
    """Fetch the table-of-contents structure (fragment URIs in order)."""
    url = f"{FLAMS_BASE}/content/toc"
    params = { "uri": uri }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    # The response is HTML — parse it to extract all fragment links in order
    return resp.json()

def fetch_fragment(uri, context_uri):
    """
    Parse the TOC HTML and extract the URIs of all content fragments in the order they appear.
    """
    resp = requests.get(
        f"{FLAMS_BASE}/content/fragment",
        params={"uri": uri, "context": context_uri}
    )
    resp.raise_for_status()
    return resp.json()

def extract_html_titles(node, results, files, context):
    """Recursively extract all `title` fields containing HTML tags."""
    if isinstance(node, dict):
        next_context = None
        uri = None
        if "uri" in node: uri = node['uri']
        if "id" in node: next_context = f"{COURSE_URI}&e={node['id']}" 
       
        # if "title" in node:
        #     title = node["title"]
        #     # Check if it contains HTML (very simple tag check)
        #     if isinstance(title, str) and re.search(r"<[^>]+>", title):
        #         results.append(title.strip())
        if uri is not None:
            print("rere")
            frag = fetch_fragment(node['uri'], context)
            results.append(frag[2])
            for link in frag[1]:
                files.add(link['Link'])

        # Recurse into children
        for key, value in node.items():
            extract_html_titles(value, results, files, next_context)

    elif isinstance(node, list):
        for item in node:
            extract_html_titles(item, results,files, context)

def main():
    files = set()
    print("Fetching TOC …")
    toc_html = fetch_toc(COURSE_URI)

    titles_with_html = []
    extract_html_titles(toc_html, titles_with_html, files, COURSE_URI)


    # -----------------------------
    # # Build HTML content
    # # # -----------------------------
    head_content = ""
    # Add CSS links
    for css in files:
        head_content += f'<link rel="stylesheet" href="{css}">\n'
    
    # # Add JS links
    # for js in js_links:
    #     head_content += f'<script src="{js}"></script>\n'
    
    # Create body content from titles
    body_content = "\n".join(titles_with_html)
    
    # Final HTML Document
    html_output = f"""<!DOCTYPE html>
    <html lang="en"><head>	<meta charset="UTF-8">
    <style>.ftml-section{{& .ftml-title-section{{&::before{{content: counter(ftml-chapter) "." counter(ftml-section) " ";}}}}}}</style>
    <style>.ftml-subsection{{& .ftml-title-subsection{{&::before{{content: counter(ftml-chapter) "." counter(ftml-section) "." counter(ftml-subsection) " ";}}}}}}</style>
    <style>.ftml-subsubsection{{& .ftml-title-subsubsection{{&::before{{content: counter(ftml-chapter) "." counter(ftml-section) "." counter(ftml-subsection) "." counter(ftml-subsubsection) " ";}}}}}}</style>
    <style>.ftml-assertion-theorem{{& .ftml-title-paragraph {{display:inline-block; font-weight: bold;font-size:inherit;&::before {{content: "Theorem" " " counter(ftml-chapter) "." counter(ftml-section) "." counter(ftml-para);}}&::after {{content:". ";}}}}}}</style>
    <style>.ftml-assertion-observation{{& .ftml-title-paragraph {{display:inline-block; font-weight: bold;font-size:inherit;&::before {{content: "Observation" " " counter(ftml-chapter) "." counter(ftml-section) "." counter(ftml-para);}}&::after {{content:". ";}}}}}} </style>
    <style>.ftml-assertion-corollary{{& .ftml-title-paragraph {{display:inline-block; font-weight: bold;font-size:inherit;&::before {{content: "Corollary" " " counter(ftml-chapter) "." counter(ftml-section) "." counter(ftml-para);}}&::after {{content:". ";}}}}}}</style>
    <style>.ftml-assertion-lemma{{& .ftml-title-paragraph {{display:inline-block; font-weight: bold;font-size:inherit;&::before {{content: "Lemma" " " counter(ftml-chapter) "." counter(ftml-section) "." counter(ftml-para);}}&::after {{content:". ";}}}}}}</style>
    <style>.ftml-assertion-axiom{{& .ftml-title-paragraph {{display:inline-block; font-weight: bold;font-size:inherit;&::before {{content: "Axiom" " " counter(ftml-chapter) "." counter(ftml-section) "." counter(ftml-para);}}&::after {{content:". ";}}}}}}</style>
    <style>.ftml-assertion-remark{{& .ftml-title-paragraph {{display:inline-block; font-weight: bold;font-size:inherit;&::before {{content: "Remark" " " counter(ftml-chapter) "." counter(ftml-section) "." counter(ftml-para);}}&::after {{content:". ";}}}}}}</style>
    <style>.ftml-paragraph-remark{{& .ftml-title-paragraph {{display:inline-block; font-weight: bold;font-size:inherit;&::before {{content: "Remark" " " counter(ftml-chapter) "." counter(ftml-section) "." counter(ftml-para);}}&::after {{content:". ";}}}}}}</style>
    <style>.ftml-definition{{& .ftml-title-paragraph {{display:inline-block; font-weight: bold;font-size:inherit;&::before {{content: "Definition" " " counter(ftml-chapter) "." counter(ftml-section) "." counter(ftml-para);}}&::after {{content:". ";}}}}}}</style>
    <style>.ftml-example{{& .ftml-title-paragraph {{display:inline-block; font-weight: bold;font-size:inherit;&::before {{content: "Example" " " counter(ftml-chapter) "." counter(ftml-section) "." counter(ftml-para);}}&::after {{content:". ";}}}}}}</style>
    {head_content}
    </head>
    <body class="rustex-body" style="--rustex-text-width:636.87927;--rustex-page-width:921.44238;font-family:Computer Modern Serif;font-size:15px;">

    \n{body_content}
      </body></html>
    """
    print(files)
    

    with open("course_full.ftml", "w", encoding="utf-8") as f:
        f.write(html_output)
    print("Wrote course_full.ftml")

if __name__ == "__main__":
    main()
