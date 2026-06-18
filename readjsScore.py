import json
from typing import Final
import os
DEFUAL_CONF:Final={"competence":{"Analyse": 0,"Apply": 0,"Create": 0,"Evaluate": 0,"Remember": 0,"Understand": 0}}
def lmsStatus(url:str, data):
    result = next((x for x in data if x["concept"] == url), DEFUAL_CONF)["competence"]
    return result

def loadData(url):
    with open(url,"r") as file:
        data=json.load(file)    
    return data["model"]


def getLmpsStatus(folder_path:str):
    lmpStatus=[]
    for filename in os.listdir(folder_path):
        full_path = os.path.join(folder_path, filename)
        with open(full_path,"r") as file:
            data=json.load(file)
            lmpStatus.append(data)
    return lmpStatus
def lmpStatus(url:str,data):
    return data.get(url, DEFUAL_CONF)["competence"]
def main():
    datas= getLmpsStatus('./lmps')
    for d in datas:
        result = lmpStatus('http://mathhub.info?a=FTML/math&p=propositions&m=prop&s=false',d)
        print(result)
if __name__ == "__main__":
    main()