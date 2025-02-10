from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
from datetime import datetime
# from backend.tourg import tour_get_tavily
import os
from .models import Tourlist
from .db import SessionLocal
# from backend.env import get_env_vars
from sqlalchemy.orm import Session
load_dotenv()


PINECONE_API_KEY = os.getenv("API_KEY")
PINECONE_ENV = "us-east-1" # Pinecone 환경 설정 (api 환경 확인 필요)
# print(PINECONE_API_KEY)
# Pinecone 초기화
pc = Pinecone(api_key=PINECONE_API_KEY)


index_name = "tourlist"
# index_name = "keyword-vector"

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

# 인덱스 리스트 확인
# print(pinecone.list_indexes())

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

# theme = "자연관광"
# user_query = f"""서울의 {theme} 여행지 정보를 중복 없이 가져다줘. 주소기반의 여행지 주소랑
# 여행지 사진이나 이미지링크, 여행지 상세정보(요금이나 입장시간 등), 그리고 여행지 근처의 식당이나
# 숙박 업소 정보들도 평점이랑 사진 가져다가줘 tavily api에서 웹링크만 가져오는건 안되고
# 가져온 정보를 아래처럼 정리해서 json 형식으로 줘
# 여행지 이름
# 여행지 사진
# 여행지 주소
# 여행지 정보
# 여행지 근처 정보
# vector db에 저장할때 metadata로 쓸거니까 잘 정리해서 줘.
# """
# import asyncio

# response = asyncio.run(tour_get_tavily(query=user_query))
# print(response)

# db에서 Tourlist 테이블 가져오는 함수
def get_tour_list(db = Session, ):
    tour_list = db.query(Tourlist).all()

    tours = [
        {
            "id": tour.id,
            "location": tour.location,
            "name": tour.name,
            "address": tour.address,
            "image_url": tour.image_url,
            "description": tour.description,
        }
        for tour in tour_list
    ]
    # print(tours)
    return tours


# Tourlist pinecone에 저장
def job_fetch_get_tour_list():
    db = SessionLocal()
    try:
        data = get_tour_list(db)
        # Pinecone 업로드
        for item in data:
            # 임베딩할 텍스트 생성 (name, address, image_url, description)
            text_to_embed = f"{item['name']} {item['address']} {item['image_url']} {item['description']}"
            vector = embed_text(text_to_embed)

            # Pinecone에 업로드 (id와 메타데이터 포함)
            metadata = {
                "location": item["location"],
                "name": item["name"],
                "address": item["address"],
                "image_url": item["image_url"],
                "created_at": datetime.now().isoformat(),  # 생성 시간
            }

            index.upsert([(str(item["id"]), vector, metadata)])
            print(f"Inserted: {item['id']} -> Vector with metadata: {metadata}")
    finally:
        db.close()

# db에 저장
# job_fetch_get_tour_list()

# # 벡터 생성 및 Pinecone에 삽입
# for item in data:
#     vector = embed_text(item['text'])  # 텍스트를 임베딩
#     index.upsert([(item['id'], vector, {"created_at":item["created_at"]})])  # Pinecone에 업로드
#     print(f"Inserted: {item['id']} -> {item['text']}, created_at: {item['created_at']}")




# 1. Pinecone에서 사용자 관련 메타데이터 가져오기
async def get_user_metadata(user_id):
    response = index.query(
        vector=embeddings.embed_query("서울"),  # 검색 기준 텍스트
        top_k=2,  # 가장 유사한 하나의 결과
        include_metadata=True,
        # filter={"ID": user_id}
    )
    print(response)  # 전체 응답 확인
    if response["matches"]:
        return response["matches"][0]["metadata"]
    return {}

# import asyncio
# asyncio.run(get_user_metadata("user223_1"))

## postgresql 에서 키워드 리스트 가져와서 텍스트 벡터로 변환하고 메타데이터로 키워드+ 키워드 생성된 시간+사용자id 넣어줘서 나중에 검색에 활용
# keywords = #postgresql 에서 키워드 정보 가져오기
# for keyword in keywords:
#     vector = embed_text(keyword.keyword)  # 텍스트를 벡터로 변환
#     metadata = {
#         "keyword": keyword.keyword,       # PostgreSQL 키워드
#         "user_id": keyword.user_id,       # 사용자 ID
#         "created_at": str(keyword.created_at),  # 키워드 생성 시간 (선택)
#     }
#     index.upsert([(str(keyword.id), vector, metadata)])  # 벡터, ID, 메타데이터 업로드
#     print(f"Inserted keyword ID {keyword.id} with metadata: {metadata}")


# # 검색 쿼리 벡터 생성
# query_vector = embed_text("서울")

# # Pinecone 검색
# result = index.query(query_vector, top_k=5, include_metadata=True)

# # 결과 출력
# for match in result["matches"]:
#     print(f"ID: {match['id']}, Score: {match['score']}, Metadata: {match['metadata']}")

# result = index.query(
#     query_vector,
#     top_k=5,
#     include_metadata=True,
#     filter={"user_id": "user223"}  # 특정 사용자 ID 필터링
# )

from datetime import datetime, timedelta

# # 최근 한 달 기준 날짜 계산
# one_month_ago = (datetime.now() - timedelta(days=30)).isoformat()

# # Pinecone 쿼리
# result = index.query(
#     query_vector,
#     top_k=5,
#     include_metadata=True,
#     filter={
#         "user_id": 1,
#         "created_at": {"$gte": one_month_ago}  # 'created_at'이 최근 한 달 이상인 데이터
#     }
# )