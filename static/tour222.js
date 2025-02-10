document.addEventListener('DOMContentLoaded', function(){
    fetchRegions();

    const regionSelect = document.getElementById('region');
    regionSelect.addEventListener('change', (e) => {
        const regionCode = e.target.value;
        fetchCities(regionCode);
    });
    document.getElementById('searchBtn').addEventListener('click', async () => {
        searchKeyword()
    });

})

// 지역 데이터 가져오기
async function fetchRegions() {
    try {
        const response = await fetch('/api/regions');
        const regions = await response.json();
        const regionSelect = document.getElementById('region');

        regionSelect.innerHTML = '<option value="">지역 선택</option>'; // 옵션 초기화
        regions.forEach(region => {
            const option = document.createElement('option');
            option.value = region.code; // 지역 코드
            option.textContent = region.name; // 지역 이름
            option.setAttribute('data-name', region.name); // 지역 이름을 data-name 속성으로 저장
            regionSelect.appendChild(option);
        });
    } catch (error) {
        console.error('지역 데이터를 불러오는 중 오류 발생:', error);
        alert('지역 정보를 불러오는 데 실패했습니다.');
    }
}

// 도시 데이터 가져오기
async function fetchCities(regionCode) {
    const citySelect = document.getElementById('city');
    citySelect.innerHTML = '<option value="">로딩 중...</option>'; // 옵션 초기화
    citySelect.disabled = true;

    if (!regionCode) {
        citySelect.innerHTML = '<option value="">지역을 먼저 선택하세요</option>';
        return;
    }

    try {
        const response = await fetch(`/api/cities/${regionCode}`);
        const cities = await response.json();

        citySelect.innerHTML = '<option value="">도시 선택</option>'; // 옵션 초기화
        cities.forEach(city => {
            const option = document.createElement('option');
            option.value = city.code; // 도시 코드
            option.textContent = city.name; // 도시 이름
            citySelect.appendChild(option);
        });

        citySelect.disabled = false;
    } catch (error) {
        console.error('도시 데이터를 불러오는 중 오류 발생:', error);
        alert('도시 정보를 불러오는 데 실패했습니다.');
    }
}

// 키워드 검색
async function searchKeyword() {
    
        try {
            // 선택된 지역 이름 가져오기
            const regionSelect = document.getElementById('region');
            const selectedOption = regionSelect.options[regionSelect.selectedIndex];
            const regionName = selectedOption ? selectedOption.getAttribute('data-name') : null;
            console.log(regionName)
            // API 요청
            const response = await fetch(`/api/keyword_search?keyword=${encodeURIComponent(regionName)}`);
            console.log("response" + response)
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            // result.html로 데이터 전달
            const queryParams = new URLSearchParams({ keyword: regionName }).toString();
            window.location.href = `/result.html?${queryParams}`;

            // const results = await response.json();
            // const resultsDiv = document.getElementById('results');
            // resultsDiv.innerHTML = '';

            // results.forEach(item => {
            //     const resultCard = `
            //         <div class="card mt-3">
            //             <img src="${item.firstimage2 || 'placeholder.jpg'}" class="card-img-top" alt="${item.title}">
            //             <div class="card-body">
            //                 <h5 class="card-title">${item.title}</h5>
            //                 <p class="card-text">${item.addr1 || '주소 정보 없음'}</p>
            //                 <button class="btn btn-info" onclick="viewDetail('${item.contentid}')">자세히 보기</button>
            //             </div>
            //         </div>`;
            //     resultsDiv.innerHTML += resultCard;
            // });
        } catch (error) {
            console.error('키워드 검색 중 오류 발생:', error);
            document.getElementById('results').innerHTML = '<p>검색 결과를 불러오는 데 실패했습니다.</p>';
        }
    
}

// 상세 보기
async function viewDetail(contentId) {
    try {
        const response = await fetch(`/api/detail_view?content_id=${contentId}`);
        const data = await response.json();
        const detail = data[0];

        alert(`제목: ${detail.title}\n개요: ${detail.overview}`);
    } catch (error) {
        console.error('상세보기 중 오류 발생:', error);
        alert('상세 정보를 불러오는 데 실패했습니다.');
    }
}
