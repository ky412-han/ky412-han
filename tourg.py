# Set up the state
from langgraph.graph import MessagesState, START, END, StateGraph
from langgraph.graph.message import add_messages
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
from typing import Annotated, TypedDict
import os
import logging as logger



if not os.environ.get("TAVILY_API_KEY"):
    os.environ("TAVILY_API_KEY") == os.getenv("TAVILY_API_KEY")

db = MongoClient("localhost",27017)
mongo_uri = os.getenv("MONGODB_URL")

tourg = APIRouter()

env_vars = get_env_vars()

CLIENT_ID = env_vars["NAVER_CLIENT_ID"]
CLIENT_SECRET = env_vars["NAVER_CLIENT_SECRET"]

@tool
def naver_local_search(query: str, display: int = 10) -> list[dict]:
    """
    네이버 지역 검색 API에 query를 전달해 결과를 리스트로 반환한다.
    display: 검색 결과 개수 (최대 10)
    """
    url = "https://openapi.naver.com/v1/search/local.json"
    headers = {
        "X-Naver-Client-Id": CLIENT_ID,
        "X-Naver-Client-Secret": CLIENT_SECRET
    }
    params = {
        "query": query,
        "display": display
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        items = data.get("items", [])

        results = []
        for item in items:
            title = item.get("title", "").replace("<b>", "").replace("</b>", "")
            category = item.get("category", "")
            address = item.get("address", "")
            telephone = item.get("telephone", "")
            link = item.get("link", "")

            results.append({
                "title": title,
                "category": category,
                "address": address,
                "telephone": telephone,
                "link": link
            })
        logger.info(f"API 호출 성공: {len(results)}개 결과 반환")
        return results
    else:
        # 에러 처리 (로깅을 사용하는 것이 좋습니다)
        logger.error(f"Error({response.status_code}): {response.text}")
        return []


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

@tool
def search_travel_info(query: str):
    """여행 데이터를 검색합니다."""
    # 예: 네이버 API 호출
    if query.lower() == "서울":
        return [{"title": "경복궁", "description": "서울의 대표적인 역사 유적지"}]
    return [{"title": "기타 지역", "description": "기타 지역에 대한 정보"}]

# OpenAI LLM 설정
llm = ChatOpenAI(model="gpt-4o-mini" ,temperature=0.5)



# system_message ="너는 10년 이상 경력의 여행플래너로 사용자가 원하는 여행 정보를 틀림없이 알맞게 줄 수 있다. 지역과 장소를 사용자가 입력한 지역의 주소 기반으로 찾아서 정확하게 찾아오고 "\
# "여행 경비 예산에 따라서 사용자가 원하는 여행코스에 예산에 알맞는 장소를 추천하고 사용자가 여행지에 갈 때 무엇을 타고 갈지에 따라 '대중교통(택시, 버스), 자가용"\
# "비행기, 렌터카 등' 그에 알맞는 정보 즉, 대중교통이면 어떤 경로로 타고 가야하는지와 소모요금, 자가용이면 여행지까지 가는 고속도로나 톨게이트 등의 경로정보와 유류비 등"\
# "을 알려준다. 여행 테마는 사용자의 입력에 따라 숙박, 관광지 ,문화관광, 호캉스, 레포츠, 드라마촬영지, 영화촬영지 등의 테마를 서로 연계하여 알려주고 주소 기반으로 알려준다. "\
# "사용자의 입력에 따라 생성된 여행코스에서 식당이면 금연시설 여부, 키즈존 여부, 네이버에서 평점이 몇점인지와 메뉴 사진이 있으면 메뉴 사진을 보여주고  대표 메뉴와 가격을 알려준다."\


from langchain_community.tools import TavilySearchResults, Tool
from typing import Optional, List, Dict
from pydantic import BaseModel
from langgraph.prebuilt import ToolNode

class Location(TypedDict):
    """사용자에게 지역을 입력받고, 몇박 몇일 여행할지 입력받고,
    여행 인원이 총 몇명인지 입력받고 네이버 지역 api tool에 연결 해준다.
    """
    messages: Annotated[list, add_messages]
    location: str
    travel_days: str
    travel_num: int

# 사용자 입력 데이터 스키마 정의
class UserInput(BaseModel):
    user_input: str
    config: Dict[str, Dict[str, str]]

tools = [naver_local_search]

# LLM 모델 정의
llm_with_tools = llm.bind_tools(tools)

# 프롬프트 템플릿 정의
prompt_template = PromptTemplate(
    input_variables=["user_input"],
    template="""
    사용자의 입력에서 지역, 여행 기간(며칠), 그리고 인원을 추출하세요.
    응답 형식은 JSON으로 제공하세요:
    {{
        "location": "<지역>",
        "travel_days": "<며칠>",
        "travel_num": <인원 수>
    }}
    사용자 입력: {user_input}
    """
)
state = StateGraph(Location)

def dummy(state:Location):
    """초기 입력값 설정"""
    return {"messages": []}

def extract_location(user_input: str)-> Location:
    """LLM을 이용해 사용자 입력에서 Location 정보를 추출"""
    prompt = prompt_template.format(user_input=user_input)
    response = llm.invoke(prompt)  # LLM으로부터 응답 받기

    return {"messages": [response]}

# 상태를 처리하는 함수 정의
def process(state: Location):
    print(f"{state.location}에서 {state.travel_days} 동안 {state.travel_num}명이 여행합니다.")

def chatbot(state: Location):
    # LLM 도구 호출을 통한 응답 생성
    response = llm_with_tools.invoke(state["messages"])


    # 메시지와 ask_human 상태 반환
    return {"messages": [response]}

# 노드 추가: 사용자 입력을 받아 상태 생성
def input_processing(state: Location):
    message = state.get("messages")
    print(f"message:{message}")
    user_input = [msg for msg in message if isinstance(msg, HumanMessage)][-1]
    print(user_input)
    return extract_location(user_input)

# 노드 추가: 상태를 처리
def process_location(state: Location) -> Location:
    print(f"state: {state}")
    print(type(state))

    response = [item.content for item in state["messages"] if isinstance(item, AIMessage)

    ]
    
    print(f"response:{response}")

    # print(type(response[0].content))
    # res = response[0].content
    print(type(response))
    print(type(response[0]))

    if response:  # 응답이 비어 있지 않을 경우
        clean_content = response[0].strip("```json").strip("```").strip()  # JSON 문자열 추출
        parsed_data = json.loads(clean_content)  # JSON 파싱
        print(f"parsed_data: {parsed_data}")
        return {
            "location": parsed_data["location"],
            "travel_days": parsed_data["travel_days"],
            "travel_num": parsed_data["travel_num"]
        }       
    
    return {"messages":parsed_data}



# LangGraph 워크플로우 정의
workflow = StateGraph(Location)



workflow.add_node("dummy", dummy)
workflow.add_node("chatbot", chatbot)
workflow.add_node("input_processing", input_processing)
workflow.add_node("process_location", process_location)
workflow.add_node("tools", ToolNode(tools=tools))

# 두 노드를 연결
workflow.add_edge(START, "dummy")
workflow.add_edge("dummy", "input_processing" )
workflow.add_edge("input_processing", "process_location")
workflow.add_edge("process_location", "chatbot")
workflow.add_edge("tools", "chatbot")
workflow.add_edge("chatbot", END)
# workflow.add_edge("input_processing", END)
# workflow.add_edge("process_location", END)

# 조건부 엣지를 정의하는 함수
def conditional_edge_logic(state: dict) -> str:
    """
    조건부 로직 정의: 특정 조건에 따라 다음 노드를 결정
    """
    if "use_tool" in state and state["use_tool"]:
        return "tools"  # 'tools' 노드로 이동
    else:
        return END  # END로 이동
    
# 조건부 엣지 추가
# workflow.add_conditional_edges(
#     "chatbot",  # 현재 노드 이름
#     {"tools": conditional_edge_logic, END: conditional_edge_logic}  # 조건부 엣지 정의
# )

graph = workflow.compile()

# user_input = input("지역, 일정, 인원을 입력해주세요 (서울 1박2일 3명)")

config = {"configurable": {"thread_id": "2"}}
# 워크플로우 실행
# graph.invoke({"messages": user_input} ,config, stream_mode="values")
# print(graph)
import asyncio

@tourg.post("/api/workflow")
def tour_work(input_data: UserInput):
    user_input=input_data.user_input
    config = input_data.config
    # 비동기 값일 경우 await로 처리
    # if asyncio.iscoroutine(user_input):
    #     user_input = await user_input

    print(f"user_input: {user_input}", f"config: {config}")

    
    response = graph.invoke({"messages": [user_input]} ,config, stream_mode="values")
    print(f"response:{response}")
    return response






@tool
def search_naver_blog(query: str):
    """네이버 블로그 검색 API를 통해 여행지 정보를 검색."""
    results = naver_blog_search(query)
    # rprint(results)
    if "error" in results:
        return f"Error: {results['error']}"
    
    # return filter_and_deduplicate_results(results)


    return filter_and_deduplicate_results(results)

# tools = [toolaa]


@tourg.get("/api/tour/agent")
async def tour_get_tavily(query: str, user_id: str):
    """
    FastAPI 엔드포인트: MongoDBSaver를 사용하여 agent와 연동
    """
    async def agent_task(checkpointer):
        # 1. 이전 대화 기록 로드
        history = await get_chat_history(checkpointer, user_id)
        print("[INFO] Loaded history:", history)


        system_message =(
            "당신은 여행 플래너 역할의 GPT입니다. "
            "사용자가 여행 지역, 일정, 인원, 취향 등을 입력하면 최적의 여행 일정을 생성하고, "
            "맛집/카페 정보와 교통 정보를 포함해 완벽하게 제공해야 합니다."
        )

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
            # llm, tools, checkpointer=checkpointer  # MongoDBSaver를 연결
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


