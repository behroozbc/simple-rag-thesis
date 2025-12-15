from typing import List
from typing import Any
from dataclasses import dataclass
import json
import requests

from data import FLAMS_BASE

@dataclass
class SearchResult:
    MyArray: List[List[object]]

    @staticmethod
    def from_dict(obj: Any) -> 'SearchResult':
        _MyArray = [y.from_dict(y) for y in obj.get("MyArray")]
        return SearchResult(_MyArray)
def search(query:str,/,num_results=20,allow_documents:bool=False,allow_paragraphs:bool=False,allow_definitions:bool=False,allow_examples:bool=False,allow_assertions:bool=False,allow_problems:bool=False,definition_like_only:bool=False):
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
    return response.json()
    
for x in search("f"):
    print(x[1])