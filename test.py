import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from fastapi import FastAPI

app = FastAPI()

@app.get("/get/tour")
def get_tour():
    api_url = "http://api.kcisa.kr/openapi/API_CNV_061/request"
    query_params = {
        "serviceKey": "12312a79-0c4d-4eda-9750-0329c54a3f76",
        "numOfRows": 20,
        "pageNo": 1
    }

    # API 요청
    api_response = requests.get(api_url, params=query_params)
    if api_response.status_code != 200:
        return {"error": "Failed to fetch data from API"}

    # XML 데이터 파싱
    import xml.etree.ElementTree as ET
    root = ET.fromstring(api_response.content)
    items = root.find('.//items')
    if items is None:
        return {"error": "No items found in XML data"}

    # 여행지와 이미지 매칭
    results = []
    for item in items.findall('item'):
        title = item.find('title').text
        detail_url = item.find('url').text

        try:
            detail_response = requests.get(detail_url)
            soup = BeautifulSoup(detail_response.text, 'html.parser')

            # 이미지 태그 찾기
            image_div = soup.find('div', class_='culture_view_img')
            if image_div:
                image_tag = image_div.find('img')
                if image_tag and 'src' in image_tag.attrs:
                    image_url = urljoin(detail_url, image_tag['src'])  # 절대 경로 변환
                else:
                    image_url = "No Image Found"
            else:
                image_url = "No Image Found"

        except Exception as e:
            image_url = f"Error fetching image: {str(e)}"

        results.append({'title': title, 'image_url': image_url})
    # 결과 출력
    for result in results:
        print(f"Title: {result['title']}, Image URL: {result['image_url']}")

    return results

# FastAPI 애플리케이션 실행
if __name__ == '__main__':
    # 테이블 생성
    import uvicorn
    uvicorn.run(app, host="localhost", port=5000)