import http.client
import json5
import json
import ssl

# 从配置文件导入API相关变量
from config import API_FLOW_ID, API_KEY, API_SECRET, XUN_FEI_URL

# ssl._create_default_https_context = ssl._create_unverified_context

def call_api(payload):
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        "Authorization": "Bearer " + API_KEY + ":" + API_SECRET,
    }
    conn = http.client.HTTPSConnection(XUN_FEI_URL, timeout=120)
    conn.request(
        "POST", "/workflow/v1/chat/completions", payload, headers, encode_chunked=True
    )
    res = conn.getresponse()
    data = res.readline()    
    json_data = json.loads(data)
    result = json_data.get("choices")[0].get("delta").get("content")
    return result


def compose_payload(type,grade="",topic="",content=""):
    data = {
    "flow_id": API_FLOW_ID,
    "uid": "1234",
    "parameters": {
        "AGENT_USER_INPUT": "hello",
        "type":type,
        "grade":grade,
        "topic":topic,
        "content":content
        },
    "ext": {"bot_id": "adjfidjf", "caller": "workflow"},
    "stream": False,
    }
    return json.dumps(data)

def create_writting_topic(grade):
    payload = compose_payload("create",grade)    
    return call_api(payload)


def review_writting(topic,content):
    payload = compose_payload("review","",topic,content)    
    print(payload)
    data =  call_api(payload)
    result =  json5.loads(data)
    return result.get("score"), result.get("review_result"), result.get("suggestion")

# def select_all_writtings():
#     payload = compose_payload("select_all")
#     result =  call_api(payload)
#     print(result)
#     if len(result.strip()) == 0:
#         return []
#     else:    
#         return json5.loads(result)


#print(create_writting_topic("七年级"))

# score ,review_result,suggestion= review_writting("The Food That Brings Back Memories?","this is a test content")
# print("Score:",score)
# print("Review Result:",review_result)       
# print("Suggestion:",suggestion)       

""" 
list = select_all_writtings()
for item in list:
    print(item.get("topic") + ": " + item.get("content"))
    print("-----") """