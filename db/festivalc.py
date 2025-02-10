from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
from .models import Festival

def parse_date_range(date_range: str):
    """
    날짜 범위를 파싱하여 시작일과 종료일 반환.
    Args:
        date_range (str): "YYYY.MM.DD~YYYY.MM.DD" 형식의 날짜 문자열.

    Returns:
        tuple: (start_date, end_date) 형식으로 반환 (YYYYMMDD).
    """
    try:
        start, end = date_range.split("~")
        start_date = datetime.strptime(start.strip(), "%Y.%m.%d").strftime("%Y%m%d")
        end_date = datetime.strptime(end.strip(), "%Y.%m.%d").strftime("%Y%m%d")
        return start_date, end_date
    except Exception as e:
        print(f"Error parsing date range: {date_range}, Error: {e}")
        return None, None
def crawl_festivals():
    """
    축제 데이터를 크롤링하여 리스트로 반환하는 함수.
    Returns:
        list[dict]: 크롤링된 축제 데이터 리스트.
    """
    # ChromeDriver 자동 관리
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

    # URL 열기
    driver.get("https://korean.visitkorea.or.kr/kfes/list/wntyFstvlList.do")
    time.sleep(3)  # 초기 페이지 로딩 대기

    # 축제 데이터를 저장할 리스트
    festival_data = []

    try:
        # 스크롤을 사용해 데이터 로드
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # 데이터 로드 대기
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        # 데이터 크롤링
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, '//ul[@id="fstvlList"]/li'))
        )

        # 각 축제 항목 가져오기
        festivals = driver.find_elements(By.XPATH, '//ul[@id="fstvlList"]/li')
        for festival in festivals:
            try:
                # 축제명
                title = festival.find_element(By.XPATH, './/div[@class="other_festival_content"]/strong').text.strip()
                # 날짜
                date_range = festival.find_element(By.XPATH, './/div[@class="other_festival_content"]/div[@class="date"]').text.strip()
                start_date, end_date = parse_date_range(date_range)
                # 지역
                loc = festival.find_element(By.XPATH, './/div[@class="other_festival_content"]/div[@class="loc"]').text.strip()
                # 이미지 URL
                try:
                    img_element = WebDriverWait(festival, 10).until(
                        EC.presence_of_element_located((By.XPATH, './/div[contains(@class, "other_festival_img")]/img'))
                    )
                    image_url = img_element.get_attribute("src")

                    # image_url = festival.find_element(By.XPATH, './/div[@class="other_festival_img open"]/img').get_attribute("src")
                except Exception as e:
                    image_url = "No Image Found"
                    print(f"Error finding image URL: {e}")
                # 행사 상세 페이지 링크
                detail_link = festival.find_element(By.XPATH, './/a').get_attribute("href")

                # 데이터 저장
                festival_data.append({
                    "title": title,
                    "start_date": start_date,
                    "end_date": end_date,
                    "location": loc,
                    "image_url": image_url,
                    "detail_link": detail_link,
                })

            except Exception as e:
                print(f"Error processing festival: {e}")

    except Exception as e:
        print(f"Error during crawling: {e}")

    finally:
        driver.quit()
    return festival_data

def save_festivals_to_db(festival_data, db_session):
    """
    크롤링된 데이터를 DB에 저장하거나 갱신하며, 누락된 데이터는 삭제하는 함수.
    Args:
        festival_data (list): 크롤링된 데이터 리스트.
        db_session (Session): SQLAlchemy 세션 객체.
    """
    # DB에 있는 모든 기존 데이터 가져오기
    existing_festivals = db_session.query(Festival).all()
    existing_festival_map = {festival.detail_link: festival for festival in existing_festivals}

    # 업데이트 및 삽입 작업
    for festival in festival_data:
        if festival["detail_link"] in existing_festival_map:
            # 이미 존재하는 데이터 -> 갱신
            db_festival = existing_festival_map[festival["detail_link"]]
            db_festival.title = festival["title"]
            db_festival.start_date = festival["start_date"]
            db_festival.end_date = festival["end_date"]
            db_festival.location = festival["location"]
            db_festival.image_url = festival["image_url"]
        else:
            # 새로운 데이터 -> 추가
            db_festival = Festival(
                title=festival["title"],
                start_date=festival["start_date"],
                end_date=festival["end_date"],
                location=festival["location"],
                image_url=festival["image_url"],
                detail_link=festival["detail_link"],
            )
            db_session.add(db_festival)

    # 크롤링된 데이터에 없는 기존 데이터 삭제
    crawled_links = {festival["detail_link"] for festival in festival_data}
    for festival in existing_festivals:
        if festival.detail_link not in crawled_links:
            db_session.delete(festival)

    db_session.commit()
    print("Data saved and updated in the database.")

# # 데이터 저장
# if festival_data:
#     # 데이터프레임으로 변환 후 CSV 저장
#     df = pd.DataFrame(festival_data)
#     df.to_csv("festival_list_with_links.csv", index=False, encoding="utf-8-sig")
#     print("축제 정보 저장 완료: festival_list_with_links.csv")
# else:
#     print("No data collected.")