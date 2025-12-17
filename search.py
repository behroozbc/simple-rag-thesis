from typing import List
from typing import Any
from dataclasses import dataclass
import requests

from data import FLAMS_BASE, fetch_fragment

@dataclass
class SearchResult:
    MyArray: List[List[object]]

    @staticmethod
    def from_dict(obj: Any) -> 'SearchResult':
        _MyArray = [y.from_dict(y) for y in obj.get("MyArray")]
        return SearchResult(_MyArray)
def TextSearch(query:str,/,num_results=20,allow_documents:bool=False,allow_paragraphs:bool=False,allow_definitions:bool=False,allow_examples:bool=False,allow_assertions:bool=False,allow_problems:bool=False,definition_like_only:bool=False):
    data={
        "query": query,
        "opts[allow_documents]": str(allow_documents).lower(),
        "opts[allow_paragraphs]":str(allow_paragraphs).lower(),
        "opts[allow_definitions]":str(allow_definitions).lower(),
        "opts[allow_examples]":str(allow_examples).lower(),
        "opts[allow_assertions]":str(allow_assertions).lower(),
        "opts[allow_problems]":str(allow_problems).lower(),
        "opts[definition_like_only]":str(definition_like_only).lower(),
        "num_results": num_results
        }
    response = requests.post(
    FLAMS_BASE+"/api/search",
        data=data
    )
    response=response.json()
    uri_content_list=[]
    for item in response:
        item= item[1]
        
        uri= item.get("Document",None)
        if uri ==None:
            uri= item.get("Paragraph",None)
            uri=uri["uri"]
        if uri!=None:
            content= fetch_fragment(uri)
            uri_content_list.append({
                "uri":uri,
                "content":content[2]
            })
    return uri_content_list
def main():
    print( len( TextSearch("f")))
    
     
if __name__ == "__main__":
    main()