# Set up the state
from langgraph.graph import MessagesState, START, StateGraph
from difflib import SequenceMatcher
# Set up the tool
# We will have one real tool - a search tool
# We'll also have one "fake" tool - a "ask_human" tool
# Here we define any ACTUAL tools
from langchain_core.tools import tool
from langchain.prompts import PromptTemplate
# from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain.schema import AIMessage, SystemMessage, HumanMessage
load_dotenv()
import requests
from env import get_env_vars
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import JSONResponse
from langgraph.checkpoint.memory import MemorySaver
import uuid, json, re
from rich import print as rprint
from langgraph.prebuilt import create_react_agent
from pymongo import MongoClient
from db.mongodb import get_chat_history, save_chat_message, session_manager
import os

if not os.environ.get("TAVILY_API_KEY"):
    os.environ("TAVILY_API_KEY") == os.getenv("TAVILY_API_KEY")

db = MongoClient("localhost",27017)
mongo_uri = os.getenv("MONGODB_URL")

tourg = APIRouter()

env_vars = get_env_vars()

CLIENT_ID = env_vars["NAVER_CLIENT_ID"]
CLIENT_SECRET = env_vars["NAVER_CLIENT_SECRET"]

def naver_blog_search(query: str, display: int = 10, start: int = 1):
    """네이버 블로그 검색 API를 사용하여 정보를 검색."""

    url = "https://openapi.naver.com/v1/search/blog.json"
    headers = {
        "X-Naver-Client-Id": CLIENT_ID,
        "X-Naver-Client-Secret": CLIENT_SECRET
    }
    params = {
        "query": query,
        "display": display,  # 검색 결과 개수
        "start": start,      # 시작점
        "sort": "sim"        # 유사도 순 정렬
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": response.status_code}

# OpenAI LLM 설정
llm = ChatOpenAI(model="gpt-4o-mini" ,temperature=0.5)

system_message ="너는 10년 이상 경력의 여행플래너로 사용자가 원하는 여행 정보를 틀림없이 알맞게 줄 수 있다. 지역과 장소를 사용자가 입력한 지역의 주소 기반으로 찾아서 정확하게 찾아오고 "\
"여행 경비 예산에 따라서 사용자가 원하는 여행코스에 예산에 알맞는 장소를 추천하고 사용자가 여행지에 갈 때 무엇을 타고 갈지에 따라 '대중교통(택시, 버스), 자가용"\
"비행기, 렌터카 등' 그에 알맞는 정보 즉, 대중교통이면 어떤 경로로 타고 가야하는지와 소모요금, 자가용이면 여행지까지 가는 고속도로나 톨게이트 등의 경로정보와 유류비 등"\
"을 알려준다. 여행 테마는 사용자의 입력에 따라 숙박, 관광지 ,문화관광, 호캉스, 레포츠, 드라마촬영지, 영화촬영지 등의 테마를 서로 연계하여 알려주고 주소 기반으로 알려준다. "\
"사용자의 입력에 따라 생성된 여행코스에서 식당이면 금연시설 여부, 키즈존 여부, 네이버에서 평점이 몇점인지와 메뉴 사진이 있으면 메뉴 사진을 보여주고  대표 메뉴와 가격을 알려준다."\


from langchain_community.tools import TavilySearchResults

@tool
async def toolaa():
    """
    Tavily API를 호출하여 검색 결과 중 실제로 사용 가능한 이미지 URL을 반환하세요.
    만약 URL이 없는 경우, 결과에서 이미지 데이터를 무시하고, 검색 가능한 URL만 반환하세요.
    """
    return TavilySearchResults(

        max_results=5,
        search_depth="advanced",
        include_answer=True,
        include_raw_content=True,
        include_images=True,
        # include_domains=[...],
        # exclude_domains=[...],
        # name="...",            # overwrite default tool name
        # description="...",     # overwrite default tool description
        # args_schema=...,       # overwrite default args_schema: BaseModel
    )

# Define a new graph 그래프 정의
workflow = StateGraph(state_schema=MessagesState)

@tool
def search_naver_blog(query: str):
    """네이버 블로그 검색 API를 통해 여행지 정보를 검색."""
    results = naver_blog_search(query)
    # rprint(results)
    if "error" in results:
        return f"Error: {results['error']}"
    
    # return filter_and_deduplicate_results(results)


    return filter_and_deduplicate_results(results)

tools = [toolaa]

# llm_with_tools = llm.bind_tools(tools, tool_choice="any")

# # Define the function that calls the model  모델을 호출해서 기능 정의
def call_model(state: MessagesState):
    response = llm.invoke(state["messages"])
    return {"messages": response}
# def call_model(state):
#     # Ensure `state["messages"]` is properly formatted
#     if isinstance(state["messages"], str):
#         state["messages"] = [{"role": "user", "content": state["messages"]}]

#     # Example of a system message setup
#     if not any(msg["role"] == "system" for msg in state["messages"]):
#         state["messages"].insert(0, {"role": "system", "content": "You are a travel assistant."})

#     # Call the LLM
#     response = llm.invoke(state["messages"])
#     return response


# Define the two nodes we will cycle between  두개의 노드들 간의 순서를 만든다
workflow.add_edge(START, "model")
workflow.add_node("model", call_model)

# # tools = []
# # Add memory   메모리 저장 chat bot 메모리에 저장
# memory = MemorySaver()
# app = workflow.compile(checkpointer=memory)



# langgraph_agent_executor = create_react_agent(
#     llm, tools, state_modifier=system_message, checkpointer=memory
# )
config = {"configurable": {"thread_id": "test-thread"}}


@tourg.get("/api/tour/agent")
async def tour_get_tavily(query: str, user_id: str):
    """
    FastAPI 엔드포인트: MongoDBSaver를 사용하여 agent와 연동
    """
    async def agent_task(checkpointer):
        # 1. 이전 대화 기록 로드
        history = await get_chat_history(checkpointer, user_id)
        print("[INFO] Loaded history:", history)


        system_message ="너는 10년 이상 경력의 여행플래너로 사용자가 원하는 여행 정보를 틀림없이 알맞게 줄 수 있다. 지역과 장소를 사용자가 입력한 지역의 주소 기반으로 찾아서 정확하게 찾아오고 "\
        "여행 경비 예산에 따라서 사용자가 원하는 여행코스에 예산에 알맞는 장소를 추천하고 사용자가 여행지에 갈 때 무엇을 타고 갈지에 따라 '대중교통(택시, 버스), 자가용"\
        "비행기, 렌터카 등' 그에 알맞는 정보 즉, 대중교통이면 어떤 경로로 타고 가야하는지와 소모요금, 자가용이면 여행지까지 가는 고속도로나 톨게이트 등의 경로정보와 유류비 등"\
        "을 알려준다. 여행 테마는 사용자의 입력에 따라 숙박, 관광지 ,문화관광, 호캉스, 레포츠, 드라마촬영지, 영화촬영지 등의 테마를 서로 연계하여 알려주고 주소 기반으로 알려준다. "\
        "사용자의 입력에 따라 생성된 여행코스에서 식당이면 금연시설 여부, 키즈존 여부, 네이버에서 평점이 몇점인지와 메뉴 사진이 있으면 메뉴 사진을 보여주고  대표 메뉴와 가격을 알려준다."\
        "답변을 줄때는 사용자의 요청에 따른 주소 기반의 장소 사진, 위치를"\
        "사용자의 요청:"\
        "코스 1: 이름, 다음문단 ,설명 다음문단, 위치정보 다음문단, 안내사항(입장시간이 정해져 있거나, 입장 요금이 있을때)"
        "코스 2: 이름, 다음문단, 설명 다음문단, 위치정보 다음문단, 안내사항(입장시간이 정해져 있거나, 입장 요금이 있을때)"
        "이미지는 웹에서 해당 장소로 검색해서 가져온다."
        "이런 식으로 해서 다양한 여행지 정보를 알려준다."  
        # 2. 이전 기록을 agent 초기 상태로 설정
        messages = [SystemMessage(content=system_message)]  # 시스템 메시지
        for session in history:
            for msg in session["messages"]:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))

        # 3. agent 생성
        agent = create_react_agent(
            llm, tools, checkpointer=checkpointer  # MongoDBSaver를 연결
        )
        config = {
            "configurable": {
                "thread_id": str(uuid.uuid4()),
                "checkpoint_ns": "tour_guide",
                "checkpoint_id": str(uuid.uuid4())
            }
        }

        # 4. 새로운 요청 처리
        response = await agent.ainvoke(
            {"messages": messages + [{"role": "user", "content": query}]},
            config=config
        )

        # 5. 응답에서 AIMessage 가져오기
        ai_response = [
            msg for msg in response["messages"] if isinstance(msg, AIMessage)
        ][-1].content if response else "AI 응답이 없습니다."

        # 6. 대화 저장
        await save_chat_message(checkpointer, user_id, query, ai_response)

        return ai_response

    # MongoDB 세션 관리
    try:
        response = await session_manager(mongo_uri, agent_task)
        return {"ai_response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")

# @tourg.get("/api/tour/agent")
# async def tour_get_tavily(query: str):
#     """
#     Tavily API를 사용하여 서울의 자연관광지 정보를 가져오세요.
#     각 결과에 포함된 이미지 링크를 JSON 형식으로 반환하세요.
#     Tavily API를 사용하여 여행 정보를 생성하고, MongoDB에 저장.
#     """
#     print(query)
#     thread_id = str(uuid.uuid4())  # thread_id는 문자열로 변환

#     system_message ="너는 10년 이상 경력의 여행플래너로 사용자가 원하는 여행 정보를 틀림없이 알맞게 줄 수 있다. 지역과 장소를 사용자가 입력한 지역의 주소 기반으로 찾아서 정확하게 찾아오고 "\
#     "여행 경비 예산에 따라서 사용자가 원하는 여행코스에 예산에 알맞는 장소를 추천하고 사용자가 여행지에 갈 때 무엇을 타고 갈지에 따라 '대중교통(택시, 버스), 자가용"\
#     "비행기, 렌터카 등' 그에 알맞는 정보 즉, 대중교통이면 어떤 경로로 타고 가야하는지와 소모요금, 자가용이면 여행지까지 가는 고속도로나 톨게이트 등의 경로정보와 유류비 등"\
#     "을 알려준다. 여행 테마는 사용자의 입력에 따라 숙박, 관광지 ,문화관광, 호캉스, 레포츠, 드라마촬영지, 영화촬영지 등의 테마를 서로 연계하여 알려주고 주소 기반으로 알려준다. "\
#     "사용자의 입력에 따라 생성된 여행코스에서 식당이면 금연시설 여부, 키즈존 여부, 네이버에서 평점이 몇점인지와 메뉴 사진이 있으면 메뉴 사진을 보여주고  대표 메뉴와 가격을 알려준다."\
#     "답변을 줄때는 사용자의 요청에 따른 주소 기반의 장소 사진, 위치를"\
#     "사용자의 요청:"\
#     "코스 1: 사진, \n설명 \n 위치정보 \n 안내사항(입장시간이 정해져 있거나, 입장 요금이 있을때)"
#     "코스 2: 사진, \n설명 \n 위치정보 \n 안내사항(입장시간이 정해져 있거나, 입장 요금이 있을때)"
#     "이미지는 웹에서 해당 장소로 검색해서 가져온다."
#     "이런 식으로 해서 다양한 여행지 정보를 알려준다."  

#     import httpx # 외부 API 호출용
#     agent = create_react_agent(
#         llm, tools, checkpointer=memory
#     )
#     config = {
#     "configurable": {
#         "thread_id": str(uuid.uuid4()),  # 고유 thread ID 생성
#         "checkpoint_ns": "tour_guide",  # 네임스페이스 설정
#         "checkpoint_id": str(uuid.uuid4())  # 고유 checkpoint ID 생성
#     }
# }
#     response = await agent.ainvoke({
#        "messages":[{"role":"system","content":system_message}, {"role": "user", "content": query}],
        
#     },config=config)
#     print("Response type:", type(response))
#     print(response)
#      # 응답 메시지 변환
#     response_dict = response["messages"] 
#     print(f"response_dict:{response_dict}")
#     # AIMessage 객체 필터링
#     ai_messages = [msg for msg in response_dict if isinstance(msg, AIMessage)]

#     print(f"ai_messages:{ai_messages}")
    

#     # AIMessage가 존재하는 경우 처리
#     if ai_messages:
#         # 첫 번째 AIMessage의 content 가져오기
#         ai_response = ai_messages[-1].content  # 가장 마지막 AIMessage의 content
#         print(f"AI Response: {ai_response}")
#     else:
#         ai_response = "AI 응답이 없습니다."
#         print("No AIMessage found in the response.")

#     # MongoDB에 데이터 저장
#     try:
#         async with httpx.AsyncClient() as client:
#             save_response = await client.post(
#                 "http://localhost:5000/api/db/mongodb_save",  # MongoDB 저장 엔드포인트
#                 json={
#                     "user_id": "user113",  # 실제 사용자 ID로 대체
#                     "user_message": query,
#                     "ai_response": ai_response
#                 }
#             )
#             save_response.raise_for_status()  # HTTP 에러 처리
#             print("Saved to MongoDB:", save_response.json())
#     except Exception as e:
#         print(f"Error saving to MongoDB: {e}")
#     finally:
#         print("[DEBUG] HTTPX client session closed.")
#     return ai_response
    



# The thread id is a unique key that identifies
# this particular conversation.
# We'll just generate a random uuid here.
# thread_id  설정 
thread_id = uuid.uuid4()
config = {"configurable": {"thread_id": thread_id}}


def remove_duplicates(results, similarity_threshold=0.8):
    """
    검색 결과에서 중복된 항목 제거.
    - similarity_threshold: 제목 또는 내용의 유사도를 판단하는 기준 (0.8 = 80%)
    """
    unique_results = []
    seen_links = set()

    for item in results.get("items", []):
        title = item["title"].replace("<b>", "").replace("</b>", "").strip()
        link = item["link"].strip()
        description = item["description"].replace("<b>", "").replace("</b>", "").strip()

        # URL 중복 제거
        if link in seen_links:
            continue

        # 제목과 설명 유사도 비교
        is_duplicate = False
        for unique_item in unique_results:
            title_similarity = SequenceMatcher(None, title, unique_item["title"]).ratio()
            desc_similarity = SequenceMatcher(None, description, unique_item["description"]).ratio()

            # 중복 조건: 제목 또는 설명이 유사하거나 링크가 동일
            if title_similarity > similarity_threshold or desc_similarity > similarity_threshold:
                is_duplicate = True
                break

        if not is_duplicate:
            seen_links.add(link)
            unique_results.append({
                "title": title,
                "link": link,
                "description": description
            })

    return unique_results


def filter_and_deduplicate_results(results, max_results=15):
    """검색 결과를 필터링하고 중복 제거."""
    deduplicated_results = remove_duplicates(results)

    # 상위 max_results만 반환
    return deduplicated_results[:max_results]






# FastAPI 애플리케이션 실행
# if __name__ == '__main__':
    
    # import uvicorn
    # uvicorn.run(main, host="localhost", port=5000)

    # response_style_template = PromptTemplate(
    # input_variables=["purpose"],
    # template=""" 
    # You are an AI assistant designed for {purpose}.
    # Your responses should be friendly, concise, and informative.
    # Always use examples when explaining technical concepts.
    # 다음과 같은 간단한 응답을 처리합니다: '네', '아니오', '이전', '다음', '없음', '괜찮아', '알겠어', '중지'.
    # 대화 흐름이 비정상적으로 중단되었거나 예상치 못한 입력이 발생할 경우, "다시 한 번 입력해주세요." 라고 응답합니다.
    # "너는 10년 이상 경력의 여행플래너로 사용자가 원하는 여행 정보를 틀림없이 알맞게 줄 수 있다. 지역과 장소를 사용자가 입력한 지역의 주소 기반으로 찾아서 정확하게 찾아오고 "\
    # "여행 경비 예산에 따라서 사용자가 원하는 여행코스에 예산에 알맞는 장소를 추천하고 사용자가 여행지에 갈 때 무엇을 타고 갈지에 따라 '대중교통(택시, 버스), 자가용"\
    # "비행기, 렌터카 등' 그에 알맞는 정보 즉, 대중교통이면 어떤 경로로 타고 가야하는지와 소모요금, 자가용이면 여행지까지 가는 고속도로나 톨게이트 등의 경로정보와 유류비 등"\
    # "을 알려준다. 여행 테마는 사용자의 입력에 따라 숙박, 관광지 ,문화관광, 호캉스, 레포츠, 드라마촬영지, 영화촬영지 등의 테마를 서로 연계하여 알려주고 주소 기반으로 알려준다. "\
    # "사용자의 입력에 따라 생성된 여행코스에서 식당이면 금연시설 여부, 키즈존 여부, 네이버에서 평점이 몇점인지와 메뉴 사진이 있으면 메뉴 사진을 보여주고  대표 메뉴와 가격을 알려준다."\

    # 대화 흐름:
    # \"start\": \"안녕하세요! 여행 가이드를 도와드릴게요. 여행하고 싶은 지역은 어디인가요?\",
    # \"ask_days\": \"여행 일정은 어떻게 되시나요? 예: 당일치기, 1박2일, 1월 1일부터 1월 4일까지.\",
    # \"ask_theme\": \"여행 테마나 유형(예: 힐링, 맛집 탐방, 자연경관 등)을 알려주세요. 없다면 임의로 추천해드릴게요.\",
    # \"list_places\": \"다음은 추천드릴 여행지 10개입니다:\",
    # \"ask_selected\": \"위 리스트 중 가고자 하는 곳을 모두 알려주세요. 여행지간에 ',' 로 구분해주세요!\",
    # \"confirm_selection\": \"모두 입력되었는지 확인 부탁드립니다. 계속 입력하시겠습니까?\",
    # \"ask_custom_places\": \"리스트에 없지만 가고 싶은 장소가 있다면 알려주세요. 없으면 Enter 또는 '없음'을 입력해주세요.\",
    # \"show_final_list\": \"입력하신 모든 장소는 다음과 같습니다:\",
    # \"ask_starting_point\": \"여행을 시작할 장소(선택 도시 내)를 정해주세요. 없으면 Enter 또는 '없음'을 입력해주세요.\",
    # \"ask_ending_point\": \"여행을 마칠 장소(선택 도시 내)를 정해주세요. 없으면 Enter 또는 '없음'을 입력해주세요.\",
    # \"offer_shortest_path\": \"최단거리 여행 코스를 만들어 드리겠습니다.\",
    # \"create_itinerary\": \"최단거리 여행 코스를 생성 중입니다...\",
    # \"final_itinerary\": \"생성된 최단거리 여행 코스는 다음과 같습니다:\",
    # \"ask_feedback\": \"생성된 코스에 대해 의견이나 수정 요청이 있으면 말씀해주세요. 없으면 '괜찮아'라고 답해주세요.\"
    # """
    # )   
    # template = response_style_template.format(purpose="providing travel guidance")
    # print(template)
    # system_message = template