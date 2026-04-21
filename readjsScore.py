import json
from typing import Final

DEFUAL_CONF:Final={"confidences":{"Analyse": 0,"Apply": 0,"Create": 0,"Evaluate": 0,"Remember": 0,"Understand": 0}}
def lmsStatus(url:str, data):
    result = next((x for x in data if x["concept"] == url), DEFUAL_CONF)["confidences"]
    return result
    
def loadData(url):
    with open(url,"r") as file:
        data=json.load(file)    
    return data["model"]

