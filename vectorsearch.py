from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
from datetime import datetime
import os
from langgraph.graph import StateGraph
from rich import print as rprint
from langchain_community.tools import TavilySearchResults
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
# from backend.env import get_env_vars
from typing import Literal

from langchain_core.tools import tool
load_dotenv()

if not os.environ.get("TAVILY_API_KEY"):
    os.environ("TAVILY_API_KEY") == os.getenv("TAVILY_API_KEY")

PINECONE_API_KEY = os.getenv("API_KEY")
PINECONE_ENV = "us-east-1" # Pinecone 환경 설정 (api 환경 확인 필요)
# print(PINECONE_API_KEY)
# Pinecone 초기화
pc = Pinecone(api_key=PINECONE_API_KEY)

index_name = "tourlist"

# 인덱스 생성
if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=1536,  # OpenAI text-embedding-ada-002의 차원
        metric="cosine",  # 유사도 계산 기준
        spec=ServerlessSpec(
            cloud="aws",
            region=PINECONE_ENV
        )
    )

# 인덱스 연결
index = pc.Index(index_name)

from langchain_openai import OpenAIEmbeddings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# OpenAI API 키 설정
embeddings = OpenAIEmbeddings(model="text-embedding-3-small", api_key=OPENAI_API_KEY)


# 텍스트를 벡터로 변환하는 함수
def embed_text(text):
    response = embeddings.embed_query(text)
    return response


# # 벡터 데이터 업로드
# for item in test_data:
#     vector = embed_text(item["text"])  # 텍스트 임베딩
#     index.upsert([
#         (item["id"], vector, {"tags": item["tags"], "text": item["text"]})  # metadata에 text 추가
#     ])
#     print(f"Inserted: {item['id']} -> {item['text']}")

# # 벡터 생성 및 Pinecone에 삽입
# for item in test_data:
#     vector = embed_text(item['text'])  # 텍스트를 임베딩
#     index.upsert([(item['id'], vector, {"tags":item["tags"]})])  # Pinecone에 업로드
#     print(f"Inserted: {item['id']} -> {item['text']}, tags: {item['tags']}")

from keybert import KeyBERT
import re
from googletrans import Translator
import asyncio

# 사용자 요청
user_query = "부산에서 자가용으로 갈 수 있는 문화관광지와 축제를 알고 싶어요."

# Google Translate 비동기 번역 함수
async def translate_keywords(keywords):
    translator = Translator()
    # 비동기 번역 호출
    tasks = [translator.translate(kw[0], src='ko', dest='en') for kw in keywords]
    translations = await asyncio.gather(*tasks)
    return [translation.text.lower() for translation in translations]

# KeyBERT 키워드 추출
kw_model = KeyBERT()
keywords = kw_model.extract_keywords(user_query, keyphrase_ngram_range=(1, 2), stop_words=None)

# 추출된 키워드 출력
# print("Extracted Keywords:", keywords)

translated_keywords = asyncio.run(translate_keywords(keywords))

# print("Translated_keywords:", translated_keywords)
# 사전 정의된 태그와 매칭
defined_tags = ["busan", "driving", "cultural", "festival", "transportation", "public","taxi", "leisure","food", "specialties","restaurant", "rating", "kids-zone", "non-smoking", "tourist_spots", "events","July", "August", "September", "Summer"
                ,"December", "January", "February", "March", "Winter", "October", "November", "Fall", "June", "April", "May", "Spring"
                ]

# 키워드 정제 함수
def preprocess_keywords(keywords):
    # 공백 제거 및 소문자로 변환
    refined_keywords = [kw[0].lower().replace(" ", "") for kw in keywords]
    # 키워드에서 주요 단어 추출 (예: 명사, 동사 등)
    refined_keywords = [re.sub(r'[^a-zA-Z가-힣]', '', kw) for kw in refined_keywords]
    return refined_keywords

def split_translated_keywords(translated_keywords):
    # 키워드 문구를 공백 기준으로 분리하여 단일 단어 리스트 생성
    split_keywords = []
    for keyword in translated_keywords:
        split_keywords.extend(keyword.split())
    return [kw.lower() for kw in split_keywords]

# 태그 매칭 함수
def match_tags(user_query, translated_keywords, defined_tags):
    query_tags = set()
    # 사용자 요청에서 직접 태그 매칭
    query_tags.update(tag for tag in defined_tags if tag in user_query.lower())
    # 번역된 키워드 분리
    split_keywords = split_translated_keywords(translated_keywords)
    # 분리된 키워드와 태그 매칭
    query_tags.update(tag for tag in defined_tags if tag in split_keywords)
    return list(query_tags)

# query_tags = [kw[0] for kw in keywords if kw[0] in defined_tags]
query_tags = match_tags(user_query, translated_keywords, defined_tags)

# print("Matched Tags:", query_tags)

@tool
async def tavily_search(user_query: str, top_results: list|None, user_id: str): 
    """
    유사도 검색에서 결과가 없을때 검색 api 사용되서 추가 정보를 보완한다.
    user_query: 사용자의 요청사항
    top_results: 유사도 검색할 태그목록
    사용자의 요청에 따라 웹에서 필요한 정보들을 검색해 온다. 관광지의 상세정보, 출입시간, 주의사항, 필요한 요금, 주소 기반 위치정보,
    식당의 주소기반 위치정보, 식당 가격, 금연 여부, 키즈존 여부, 식당 사진, 평점,
    숙박 업소의 평점, 시즌, 비시즌에 따른 가격, 숙박 업소 사진,
    사용자가 여행하는 날짜에 따라 봄(3,4,5월), 여름(6,7,8,9월), 가을(10,11월), 겨울(12,1,2월) 으로 계절에 따른 검색 제공
    """
    

 
    print(f"User Query: {user_query}")
    print(f"Top Results: {top_results}")

    return TavilySearchResults(
        query=user_query,
        # tags=[result["metadata"]["tags"] for result in top_results],
        max_results=10,
        search_depth="advanced",
        include_answer=True,
        include_raw_content=True,
        include_images=True
    )

@tool
async def pinecone_search(user_query:str, location:str):
    """
    사용자 입력 쿼리를 Pinecone에 검색하고, 유사도가 높은 결과를 반환합니다.

    Args:
        user_query (str): 사용자가 입력한 검색 쿼리.
        pc (str): Pinecone 인덱스 이름 (기본값: index).

    Returns:
        추천 결과를 콘솔에 출력합니다.
    """    
    print(f"query:{user_query}")
    query_vector = embed_text(user_query)

    results = index.query(
        vector=query_vector, 
        top_k=10,  # 상위 10개 결과 가져오기
        include_metadata=True,  # 메타데이터 포함
        filter={"location": {"$eq": location}}  # location이 "서울"인 항목만 검색

    )
    rprint(f"results:{results}")
    # 3. 유사도 스코어 기준 필터링
    if "matches" in results and results["matches"]:
    # 안전하게 검색 결과를 처리
        filtered_results = [
            {
                "id": match.get("id", "N/A"),  # ID가 없으면 기본값 'N/A'
                "name": match.get("metadata", {}).get("name", "N/A"),  # metadata에서 name 가져오기
                "location": match.get("metadata", {}).get("location", "N/A"),
                "address": match.get("metadata", {}).get("address", "N/A"),
                "image_url": match.get("metadata", {}).get("image_url", ""),
                "score": match.get("score", 0.0),  # score가 없으면 기본값 0.0
            }
            for match in results["matches"]
        ]
    if not filtered_results:
        print("관련된 결과를 찾을 수 없습니다. 다른 키워드로 검색해주세요!")
        return
    
    filtered_results = sorted(results["matches"], key=lambda x: x["score"], reverse=True)[:10]
    # 4. 사용자에게 결과 반환 (예: JSON 형태)
    return filtered_results
    
    

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)

tools = [pinecone_search, tavily_search]

agent = create_react_agent(
    model = llm,
    tools = tools,
)

results = index.query(
    vector= embed_text(user_query),
    top_k=5,
    include_metadata=True,
    include_values=False,
    # include_values=True,
    filter={"tags": {"$in": query_tags}}
)

# print("Search Results:", results["matches"])

# 검색된 데이터를 조합하여 프롬프트 생성
# final_prompt = "\n\n".join(
#     [", ".join(match["metadata"]["tags"]) for match in results["matches"]]
# )

final_prompt = "\n\n".join([
    f"Tags: {', '.join(match['metadata']['tags'])}, Text: {match['metadata']['text']}"
    for match in results["matches"]
])

# print("Generated Prompt:\n", final_prompt)
config = {"configurable": {"thread_id:": "1"}}
# messages = [
#     {"role": "system", "content": "You are an intelligent assistant for analyzing travel tags."},
#     {"role": "user", "content": final_prompt}  # 사용자 입력 전달
# ]
prompt = final_prompt.split("\n")
# rprint("prompt:", prompt)
# response = agent.invoke({
#     "messages": [
#         {"role": "user", "content": f"{final_prompt}"},
#     ],
#     "configurable": {"thread_id": "1"}})


# 중복 제거된 Top Results 생성
seen_ids = set()
top_results = [
    {
        "tags": match["metadata"].get("tags", []),
        "text": match["metadata"].get("text", "No text available")
    }
    for match in results["matches"]
    if match["id"] not in seen_ids and not seen_ids.add(match["id"])
    # if match.get("values") is not None  # value가 None인 경우 필터링
]

# rprint(top_results)
# 비동기 호출
# async def invoke_agent():
#     response = await agent.ainvoke({
#         "messages": [
#             # {"role": "system", "content": "You are an intelligent assistant for analyzing travel tags."},
#             {"role": "user", "content": user_query}  # 사용자 입력 그대로 전달
#         ],
#         "top_results": top_results,
#         "tags": query_tags,  # 필터링된 태그 전달
#     })
#     return response


# 비동기 호출 함수
# async def invoke_agent():
#     if not top_results:  # Top Results가 비어 있는 경우 방지
#         print("No valid results found to process.")
#         return

#     response = await agent.ainvoke({
#         "messages": [
#             {"role": "user", "content": user_query}
#         ],
#         "top_results": top_results,
#         "tags": query_tags,
#     })
#     return response

# response = asyncio.run(invoke_agent())

# response = asyncio.run(invoke_agent())

# rprint(response)

# api_data = response

# summary_prompt = f"""
# Tavily API로부터 받은 데이터를 사용자의 요청에 맞게 요약하세요.
# 사용자 요청: 금연, 예산 1인당 15만원, 3인, 자가용, 1박2일
# API 응답 데이터: {api_data}

# 요약 규칙:
# 1. 사용자가 요청한 조건(교통수단, 예산, 금연 여부 등)에 맞는 데이터만 표시합니다.
# 2. 레포츠 장소와 관련된 정보를 먼저 요약합니다.
# 3. 숙소 정보를 금연 여부와 키즈존 여부를 기준으로 정리합니다.
# 4. 대중교통 경로와 소요 비용도 함께 포함하세요.
# """


# # OpenAI를 사용해 요약 생성
# summary_response = llm(summary_prompt)
# print(summary_response)



def store_user_keywords(user_id, keywords):
    """
    사용자 키워드와 검색 타임스탬프를 Pinecone에 저장
    """
    timestamp = datetime.now().isoformat()
    for keyword in keywords:
        # 키워드를 임베딩
        vector = embed_text(keyword)
        # Pinecone에 저장 (user_id 기반으로 ID 생성)
        index.upsert(
            [
                (
                    f"{user_id}-{timestamp}",
                    vector,
                    {"keyword": keyword, "user_id": user_id, "timestamp": timestamp}
                )
            ]
        )



def get_user_recommendations(user_id, query):
    """
    사용자 키워드를 기반으로 새로운 검색 요청 처리
    """
    # 현재 검색어를 임베딩
    query_vector = embed_text(query)

    # Pinecone에서 사용자와 관련된 데이터를 검색
    results = index.query(
        vector=query_vector,
        top_k=5,
        include_metadata=True,
        filter={"user_id": user_id}  # 사용자의 키워드만 필터링
    )
    for match in results["matches"]:
        print(f"ID: {match['id']}, Metadata: {match['metadata']}, Score: {match['score']}")

    # 유사도 기반으로 상위 추천 키워드 가져오기
    recommended_keywords = [
        {"keyword": match["metadata"]["keyword"], "similarity": match["score"]}
        for match in results["matches"]
    ]
    return recommended_keywords



@tool
async def tavily(user_query: str, user_id: str, pinecone_results: list):
    """
    사용자 요청과 기존 키워드를 Tavily 검색에 활용
    """
    # # 현재 검색어에서 키워드 추출 및 추천 키워드 가져오기
    # keywords = [kw[0] for kw in KeyBERT().extract_keywords(user_query)]
    # recommendations = get_user_recommendations(user_id, user_query)

    # # 추천 키워드 추가
    # all_keywords = list(set(keywords + [rec["keyword"] for rec in recommendations]))

    # # 검색 쿼리 생성
    # query_with_recommendations = f"{user_query} {' '.join(all_keywords)}"

    # Pinecone 결과에서 키워드 추출
    pinecone_tags = [result["metadata"]["keyword"] for result in pinecone_results]
    
    # Tavily 쿼리 생성
    query_with_context = f"{user_query} {' '.join(pinecone_tags)}"
    
    print(f"Enhanced Tavily Query: {query_with_context}")

    # Tavily 검색 호출
    return TavilySearchResults(
        # query=query_with_recommendations,
        # tags=all_keywords,
        query=query_with_context,
        tags=pinecone_tags,
        max_results=5,
        search_depth="advanced",
        include_answer=True,
        include_raw_content=True,
        include_images=True
    )

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
tools = [pinecone_search ,tavily_search]

agent = create_react_agent(
    model=llm,
    tools=tools,
)


test_data = [
    {"id": "user123_1", "text": "서울 관광지", "created_at": datetime.now().isoformat(), "keyword":"서울,식당", "user_id": "user123"},
    {"id": "user123_2", "text": "서울 자연관광", "created_at": datetime.now().isoformat(), "keyword":"서울,관광지", "user_id": "user123"},
    {"id": "user123_3", "text": "금연시설, 한식, 삼겹살, 3인여행", "created_at": datetime.now().isoformat(), "keyword":"서울,호텔,금연,3인", "user_id": "user123"},
]

# 벡터 데이터 업로드
# for item in test_data:
#     vector = embed_text(item["text"])  # 텍스트 임베딩
#     index.upsert([
#         (item["id"], vector, {"created_at": item["created_at"], "text": item["text"],"keyword": item["keyword"],"user_id": item["user_id"]})  # metadata에 text 추가
#     ])
#     print(f"Inserted: {item['id']} -> {item['keyword']}")


# 사용자 요청 처리
async def invoke_agent(user_query, user_id,location):
    # Pinecone에서 사용자 데이터 검색
    # recommandations = get_user_recommendations(user_id, user_query)
    # print(f"recommand: {recommandations}")
    # rec = ""
    # for recommand in recommandations:
    #     rec += recommand["keyword"] + ", "  # keyword 값을 누적하고 콤마로 구분
    # rec = rec.rstrip(", ")  # 마지막 콤마와 공백 제거

    # final_query = user_query+" "+rec

    system_message ="너는 10년 이상 경력의 여행플래너로 사용자가 원하는 여행 정보를 틀림없이 알맞게 줄 수 있다. 지역과 장소를 사용자가 입력한 지역의 주소 기반으로 찾아서 정확하게 찾아오고 "\
    "여행 경비 예산에 따라서 사용자가 원하는 여행코스에 예산에 알맞는 장소를 추천하고 사용자가 여행지에 갈 때 무엇을 타고 갈지에 따라 '대중교통(택시, 버스), 자가용"\
    "비행기, 렌터카 등' 그에 알맞는 정보 즉, 대중교통이면 어떤 경로로 타고 가야하는지와 소모요금, 자가용이면 여행지까지 가는 고속도로나 톨게이트 등의 경로정보와 유류비 등"\
    "을 알려준다. 여행 테마는 사용자의 입력에 따라 숙박, 관광지 ,문화관광, 호캉스, 레포츠, 드라마촬영지, 영화촬영지 등의 테마를 서로 연계하여 알려주고 주소 기반으로 알려준다. "\
    "사용자의 입력에 따라 생성된 여행코스에서 식당이면 금연시설 여부, 키즈존 여부, 네이버에서 평점이 몇점인지와 메뉴 사진이 있으면 메뉴 사진을 보여주고  대표 메뉴와 가격을 알려준다."\
    "답변을 줄때는 사용자의 요청에 따른 주소 기반의 장소 사진, 위치를"\
    "사용자의 요청:"\
    "코스 1: 사진, \n설명 \n 위치정보 \n 안내사항(입장시간이 정해져 있거나, 입장 요금이 있을때)"
    "코스 2: 사진, \n설명 \n 위치정보 \n 안내사항(입장시간이 정해져 있거나, 입장 요금이 있을때)"
    "유사도 검색으로 pinecone에서 지역 이름으로 저장된 장소를 찾아 사용자의 요청과 유사도가 제일 유사한 걸로 장소의 이름과 이미지등을 가져온다"
    "여행지 정보에 식당이나 숙박정보가 없으면 그런 정보들을 tavily api를 사용해 보강해 준다."

    response = await agent.ainvoke({
        "messages": [
            {"role": "system", "content": system_message },
            {"role": "user", "content": user_query}
        ],
        "location": location,  # Pinecone 결과 전달
        "user_id": user_id,
    })
    if response.get("finish_reason") == "stop":
        print("Agent finished successfully.")
    else:
        print("Repeating agent call.")
    return response

# # 테스트 호출
location =["서울", "부산", "대구","춘천","강릉","공주","전주","경주","통영","제주특별자치도"]
user_query = f"{location[1]}에서 갈 만한 장소를 추천해주세요."
user_id = "user123"  # 사용자 식별 ID
response = asyncio.run(invoke_agent(user_query, user_id, location))
# if response.get("finish_reason") == "stop":
#     print("Agent finished successfully.")
# else:
#     print("Repeating agent call.")
rprint(response)

# pinecone_results = index.query(
#         vector=embed_text(user_query),
#         top_k=5,
#         include_metadata=True,
#         include_values=True,
#         filter={"user_id": user_id}  # 사용자 ID로 필터링
#     )["matches"]  # 검색 결과 매치 데이터만 추출

# rprint(pinecone_results)

def summarize_results(response, user_id):
    """
    검색 결과 요약 및 사용자 맞춤형 데이터 생성
    """
    recommendations = get_user_recommendations(user_id, response["query"])
    return {
        "query": response["query"],
        "results": response["results"],
        "personalized_recommendations": recommendations
    }