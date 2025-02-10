from pymongo import AsyncMongoClient
from dotenv import load_dotenv
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver
from datetime import datetime
import asyncio
import os

load_dotenv()
### MongoDB 세션 생성 함수에 CRUD 함수 넣어서 사용

# mongo_db_url = os.getenv("MONGODB_URL")


mongo_uri = os.getenv("MONGODB_URL")

# db = mongo_db['chatbot_all_messages']
# collection = db['messages']


# MongoDB에 대화 저장
async def save_chat_message(checkpointer, user_id, user_message, ai_response):
    """
    MongoDB에 유저와 AI 간 대화를 하나의 묶음으로 저장.
    :param checkpointer: AsyncMongoDBSaver 인스턴스
    :param user_id: 사용자 ID
    :param user_message: 유저의 메시지
    :param ai_response: AI의 응답
    """
    data = {
        "user_id": user_id,
        "conversation_id": str(datetime.now().timestamp()),  # 세션 ID 또는 대화 ID
        "messages": [
            {"role": "user", "content": user_message, "timestamp": datetime.now()},
            {"role": "assistant", "content": ai_response, "timestamp": datetime.now()},
        ],
    }
    collection = checkpointer.client["chatbot_all_messages"]["conversations"]
    result = await collection.insert_one(data)
    print(f"[INFO] Conversation saved. ID: {result.inserted_id}")

# MongoDB에서 대화 세션 조회
async def  get_chat_history(checkpointer, user_id):
    """
    MongoDB에서 특정 유저의 모든 대화를 조회.
    :param checkpointer: AsyncMongoDBSaver 인스턴스
    :param user_id: 사용자 ID
    :return: 유저의 대화 세션 리스트
    """
    collection = checkpointer.client["chatbot_all_messages"]["conversations"]
    cursor = collection.find({"user_id": user_id}).sort("conversation_id", 1)
    history = await cursor.to_list(length=None)  # 모든 세션 데이터를 리스트로 변환
    return history


async def session_manager(mongo_uri, task_fn, *args, **kwargs):
    """
    세션 관리 함수
    :param mongo_uri: MongoDB URI
    :param task_fn: 작업 함수 (콜백)
    :param args: 작업 함수에 전달할 위치 인자
    :param kwargs: 작업 함수에 전달할 키워드 인자
    """
    async_mongodb_client = None
    try:
        # 세션 생성
        async_mongodb_client = AsyncMongoClient(mongo_uri)
        checkpointer = AsyncMongoDBSaver(async_mongodb_client)

        # 작업 함수 호출
        return await task_fn(checkpointer, *args, **kwargs)
    
    except Exception as e:
        # 예외 처리
        print(f"세션관리 에러: {e}" )
        raise
    finally:
        # 세션 닫기
        if async_mongodb_client:
            await async_mongodb_client.close()
            print("MongoDB session closed")

async def session_main(user_id, user_message, ai_response):
    """
    사용자 ID와 대화 내용을 받아 MongoDB에 저장하고 히스토리를 관리.
    :param user_id: 사용자 ID
    :param user_message: 유저의 메시지
    :param ai_response: AI의 응답
    """
    async def save_and_get_history(checkpointer):
        # 대화 저장
        await save_chat_message(checkpointer, user_id, user_message, ai_response)
        # 대화 히스토리 조회
        history = await get_chat_history(checkpointer, user_id=user_id)
        return history

    # 단일 세션으로 저장 및 조회 처리
    history = await session_manager(mongo_uri, save_and_get_history)

    print("[INFO] User Chat History:")
    for session in history:
        print(session)

