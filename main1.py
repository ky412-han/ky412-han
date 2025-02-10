import requests
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage
from env import get_env_vars
from db.db import engine, SessionLocal
from db.models import Base, TourSchedule
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from rich import print as rprint
import json
import os, urllib.request
import urllib.parse
# from urllib.parse import quote

load_dotenv()

# 2번 여행 스케쥴 openai로 만들어서 db에 저장하고 화면에 당일, 1박2일, 2박3일 여행지
# 보여주기

env_vars = get_env_vars()

app = FastAPI()




# OpenAI LLM 초기화
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # React 개발 서버 도메인
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메소드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)

NAVER_CLIENT_ID = env_vars["NAVER_CLIENT_ID"]
NAVER_CLIENT_SECRET = env_vars["NAVER_CLIENT_SECRET"]

def naver_image_search(query):
    """
    네이버 검색 API를 사용하여 이미지 검색
    :param query: 검색할 키워드
    :return: 첫 번째 이미지 URL
    """
    url = "https://openapi.naver.com/v1/search/image"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    params = {
        "query": query,
        "display": 1,
        "sort": "sim"
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        if data['items']:
            return data['items'][0]['link']
        else:
            return "이미지를 찾을 수 없습니다."
    elif response.status_code == 401:
        return "API 인증 실패: 네이버 API 키를 확인하세요."
    else:
        return f"HTTP Error {response.status_code}: {response.text}"

def search_img(query: str = Query(...)):
       
    params = urllib.parse.quote(query)
    print(params)
    url = "https://openapi.naver.com/v1/search/image?query=" + params
    request = urllib.request.Request(url)
    request.add_header("X-Naver-Client-Id",NAVER_CLIENT_ID)
    request.add_header("X-Naver-Client-Secret",NAVER_CLIENT_SECRET)
    response = urllib.request.urlopen(request)
    rescode = response.getcode()
    if rescode == 200:
        # 데이터를 JSON으로 변환
        response_body = response.read()
        data = json.loads(response_body)        
        
        if 'items' in data and data['items']:
                # 첫 번째 검색 결과의 이미지 반환
                img = data["items"][0]  # 딕셔너리에서 'items' 키 접근
                # print(img)
                return {
                    "thumbnail_url": img.get("thumbnail"),
                    "image_url": img.get("link"),
                }                  
        else:
            return JSONResponse(content={"message": "Location not found"}, status_code=404)
    else:        
        return JSONResponse(content={"message": "Failed to connect to Naver API"}, status_code=500)

def generate_travel_plan(location, duration):
    """
    OpenAI 모델을 사용하여 여행 계획 생성
    :param location: 여행지
    :param duration: 여행 기간
    :return: 생성된 여행 계획
    """
    #2박3일의 경우 1일 5개 여행지, 2일 5개 여행지, 3일 5개 여행지를 생성해 주세요.
    prompt = f"""
    {location}를(을) 여행할 계획입니다. {duration} 일정으로 여행 코스를 1개 생성해 주세요.
    {duration}에 해당하는 여행 코스만 작성해 주세요. 다른 일정(예: 1박 2일, 2박 3일 등)은 포함하지 마세요.
    1박2일의 경우 1일 5개 여행지, 2일 5개 여행지를 생성해 주세요.
     
    여행지는 카카오 map api에서 찾을 수 있는 지명으로 적어줘, 그리고 무슨무슨거리 등은 지도에서 찾을수 있는 곳만 알려주고 지도에서 찾을수 없는 곳은 제외하고 찾아줘
    각 코스는 주요 관광지와 활동을 포함하고 아래 포맷으로만 생성해줘, 간단한 설명 추가해서요. 언어는 한글로만 해줘
    대답은 json형식으로 해줘

    포맷:
    {{
      "location": "{location} ({duration})",
      "여행코스": {{
        "1일": [
          {{
            "여행지": "(여행지 이름)",
            "설명": "(간단한 설명)",
            "주소": "(주소)",
            "좌표": "위도, 경도"
          }},
          ...
        ]
      }}
    }}
    """
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        if response and response.content:
            return response.content.strip()
        else:
            print("Error: OpenAI 응답이 비어 있습니다.")
            return None
    except Exception as e:
        print(f"Error: OpenAI 호출 중 문제가 발생했습니다 - {e}")
        return None


# # 여행 계획 생성 및 네이버 이미지 검색
# locations = ["대구"]
# durations = ["당일치기"]

def create_travel_plan(location, duration):

    print(f"\n=== {location} ({duration}) ===\n")
    
    # GPT 여행 계획 생성
    plans = generate_travel_plan(location, duration)
    
    # 디버깅용 출력
    rprint("Generated Plans:\n", plans)
    
    # JSON 파싱
    try:
        # OpenAI 응답에서 JSON 코드 블록 추출
        if plans.startswith("```json") and plans.endswith("```"):
            plans = plans.strip("```json").strip("```")
        print(plans)
        json_data = json.loads(plans)
        return json_data
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        print("응답 내용:", plans)  # 디버깅용 출력
        return None

# JSON 데이터를 데이터베이스에 저장하는 함수
def save_travel_data(json_data):
    db = SessionLocal()
    try:
        # 데이터 파싱
        location = json_data["location"]
        travel_courses = json_data.get("여행코스", {})

        for day_key, courses in travel_courses.items():
            schedule = int(day_key.replace("일", ""))  # "1일" -> 1

            for course in courses:
                lat, lon = map(float, course["좌표"].split(", "))
                loc = course["여행지"]
                print(loc)
                imageUrl = search_img(loc)            
                print(imageUrl)
                tour_schedule = TourSchedule(
                    location=location,
                    address=course["주소"],
                    tour_name_kor=course["여행지"],
                    description=course.get("설명"),
                    latitude=lat,
                    longitude=lon,
                    schedule=schedule,
                    image_url= imageUrl["image_url"],
                )
                db.add(tour_schedule)
        # 커밋하여 저장
        db.commit()
        print("데이터 저장 완료!")
    except Exception as e:
        db.rollback()
        print(f"오류 발생: {e}")
    finally:
        db.close()

# FastAPI 애플리케이션 실행
if __name__ == '__main__':
    # 테이블 생성
    Base.metadata.create_all(engine)
    # 여행 계획 생성 및 처리
    locations = ["대구"]
    durations = ["당일치기"]

    for location in locations:
        for duration in durations:
            schedule = create_travel_plan(location, duration)
            save_travel_data(schedule)
    import uvicorn
    uvicorn.run(app, host="localhost", port=5000)