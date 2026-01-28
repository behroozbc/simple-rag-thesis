import json

def lmsStatus(url:str, data):
    result = next((x for x in data if x["concept"] == url), None)
    return result
    
def main():
    print(lmsStatus("http://mathhub.info?a=courses/FAU/AI/course&p=csp/slides&m=constraints-types&s=higher-order",loadData("F:\Downloads\yx53utuz-lms-1769525124917.json")))
def loadData(url):
    with open(url,"r") as file:
        data=json.load(file)    
    return data["model"]
if __name__ == "__main__":
    main()
