import json
from typing import Final, List
import os
DEFUAL_CONF:Final={"competence":{"Analyse": 0,"Apply": 0,"Create": 0,"Evaluate": 0,"Remember": 0,"Understand": 0}}
class LmpUser(object):
    id="unknow"
    learnerobjs=[]
    def __init__(self,id:str,learnerobjs:list):
        self.id=id
        self.learnerobjs=learnerobjs
    def lmpStatus(self,url:str):
        return self.learnerobjs.get(url, DEFUAL_CONF)["competence"]

def lmsStatus(url:str, data):
    result = next((x for x in data if x["concept"] == url), DEFUAL_CONF)["competence"]
    return result

def loadData(url):
    with open(url,"r") as file:
        data=json.load(file)    
    return data["model"]


def getLmpsStatus(folder_path:str):
    lmpStatus:List[LmpUser]=[]
    for filename in os.listdir(folder_path):
        full_path = os.path.join(folder_path, filename)
        with open(full_path,"r") as file:
            data=json.load(file)
            lmpStatus.append(LmpUser(filename.removesuffix('.json'),data))
    return lmpStatus
def lmpStatus(url:str,data):
    return data.get(url, DEFUAL_CONF)["competence"]
def main():
    datas= getLmpsStatus('./lmps')
    for d in datas:
        result = d.lmpStatus('http://mathhub.info?a=FTML/math&p=propositions&m=prop&s=false')
        print(d.id + str( result))
if __name__ == "__main__":
    main()