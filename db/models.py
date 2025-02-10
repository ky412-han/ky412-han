from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import JSON  # JSON 타입 임포트
from sqlalchemy.dialects.postgresql import ARRAY
import datetime


# 모델 베이스 클래스
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
#SQLAlchemy가 PostgreSQL 데이터베이스와 연결되면,
#  primary_key=True로 설정된 Integer 컬럼은 SERIAL로 처리됩니다.
#PostgreSQL db에서는 SERIAL 타입을 사용해 기본 키 컬럼의 값을 자동 생성합니다.
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)    
    created_at = Column(DateTime, default=datetime.datetime.now)
    # 관계 설정: 사용자와 경로 간의 일대다 관계
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    # keyword = relationship("Keywords", back_populates="user", cascade="all, delete-orphan")


# class Keywords(Base):
#     __tablename__ = "keywords"
#     # 사용자가 입력한 키워드들을 저장하여 User와 1:N 연결해두고 id로 pinecone의 keyword-vector 테이블과 1:1 연결해서 데이터 참조
#     id = Column(Integer, primary_key=True, index=True)
#     user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
#     keyword = Column(ARRAY(Text), nullable=False) # PostgreSQL 배열
#     created_at = Column(DateTime, default=datetime.datetime.now)
#     user = relationship("User", back_populates="keywords")


# 채팅 테이블
class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user_message = Column(Text, nullable=False)  # 대화 내용
    ai_message = Column(Text, nullable=False)  # 대화 내용
    created_at = Column(DateTime, default=datetime.datetime.now)  # 생성 날짜

    # 관계 설정: 경로와 사용자 간의 다대일 관계
    user = relationship("User", back_populates="chats")

class AreaList(Base):
    __tablename__ = "area_list"

    areacode_id = Column(Integer, primary_key=True, index=True) #지역 코드
    area_name_kor = Column(String, nullable=False) #지역 한글이름
    area_name_eng = Column(String, nullable=True)  #지역 영문이름
    latitude = Column(Float ,nullable=True)       # 위도 (nullable)
    longitude = Column(Float ,nullable=True)      # 경도 (nullable)

    # 관계 설정: 지역코드와 도시코드 간의 일대다 관계
    cities = relationship("CityList", back_populates="area", cascade="all, delete-orphan")
   
class CityList(Base):
    __tablename__ = "city_list"

    id = Column(Integer, primary_key=True, index=True)
    sigungucode_id = Column(Integer, nullable=False) #시군구 코드
    city_name_kor = Column(String, nullable=False) #시군구 한글이름
    city_name_eng = Column(String, nullable=True)  #시군구 영문이름
    latitude = Column(Float ,nullable=True)       # 위도 (nullable)
    longitude = Column(Float ,nullable=True)      # 경도 (nullable) 
    area_areacode_id = Column(Integer, ForeignKey("area_list.areacode_id", ondelete="CASCADE"), nullable=False)
    # 관계 설정: 도시코드와 지역코드 간의 다대일 관계
    area = relationship("AreaList", back_populates="cities")
    
    __table_args__ = (
        # area_id와 sigungucode_id의 복합 고유 제약 조건 설정
        UniqueConstraint('area_areacode_id', 'sigungucode_id', name='uq_area_sigungucode'),
    )

class Festival(Base):
    __tablename__ = "festivals"

    id = Column(Integer, primary_key=True, autoincrement=True)  # 기본 키
    title = Column(String, nullable=False)                     # 축제명
    start_date = Column(String, nullable=True)                 # 시작일 (YYYYMMDD)
    end_date = Column(String, nullable=True)                   # 종료일 (YYYYMMDD)
    location = Column(String, nullable=True)                   # 지역
    image_url = Column(String, nullable=True)                  # 이미지 URL
    detail_link = Column(String, nullable=True)                # 상세 페이지 링크

class Tourlist(Base): # 상세보기 + 벡터화할 pdf 저장용
    __tablename__ = "tour_list"

    id = Column(Integer, primary_key=True, index=True)  # DB 고유 ID
    location = Column(String, nullable=True)  # 지역 위치/지리적 범위
    name = Column(String, nullable=False)  # 추천 여행지 이름 (한글)
    address = Column(String, nullable=False)  # 주소
    image_url = Column(String, nullable=True)  # 메인 이미지 URL
    description = Column(String, nullable=True)  # 장소 설명    

class Schedule(Base): # openai로 받는 여행코스 스케쥴 목록 테이블 id로 장소랑 연결
    __tablename__ = "schedule"

    id = Column(Integer, primary_key=True, index=True)  # 고유 ID
    location = Column(String, nullable=False)  # 지역 이름 (예: 서울)
    duration = Column(String, nullable=False)  # 기간 (예: 당일치기, 1박2일, 2박3일)
    day = Column(Integer, nullable=False)  # 여행 일차 (예: 1일차, 2일차)
    description = Column(String, nullable=True)  # 일정에 대한 설명 (옵션)

    spots = relationship("TourSpot", back_populates="schedule", cascade="all, delete")

class TourSpot(Base): # Schedule 테이블에 연결해서 해당 지역 일차에 장소 저장
    __tablename__ = "tour_spot"

    id = Column(Integer, primary_key=True, index=True)  # 고유 ID
    schedule_id = Column(Integer, ForeignKey("schedule.id"), nullable=False)  # Schedule과 연결
    name = Column(String, nullable=False)  # 여행지 이름
    address = Column(String, nullable=False)  # 주소
    image_url = Column(String, nullable=True)  # 이미지 URL
    description = Column(String, nullable=True)  # 여행지 설명
    latitude = Column(Float, nullable=True)  # 위도
    longitude = Column(Float, nullable=True)  # 경도

    # TourSpot에서 Schedule에 접근할 수 있도록 설정 (N:1 관계)
    schedule = relationship("Schedule", back_populates="spots")

class PickUpList(Base): #api로 뽑을 지역 목록
    __tablename__ = "pick_up_list"

    id = Column(Integer, primary_key=True, index=True) # 고유id
    area_name_kor = Column(String, nullable=False) #지역 한글이름
    area_name_eng = Column(String, nullable=True)  #지역 영문이름
    latitude = Column(Float ,nullable=True)       # 위도 (nullable)
    longitude = Column(Float ,nullable=True)      # 경도 (nullable)


# 게시판에 저장할 메타데이터, 유저정보
class TravelPosts(Base): 
    __tablename__ ="travel_posts"

    id = Column(Integer, primary_key=True, index=True) # 고유 id
    user_id = Column(String, nullable=False) # 작성자 ID
    mongo_id = Column(String, nullable=False) # MongDB 데이터 ID
    title = Column(String, nullable=False) # 제목
    create_at = Column(DateTime, default=datetime.datetime.now) # 생성 날짜
    updated_at = Column(DateTime, onupdate=datetime.datetime.now)  # 수정 날짜
    likes = Column(Integer, default=0) # 좋아요 수
    views = Column(Integer, default=0) # 조회수

