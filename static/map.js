var container = document.getElementById('map');  // 지도 표시 div
var options = {
    center: new kakao.maps.LatLng(37.5665, 126.9780), // 지도 초기 중심 좌표 (서울)
    level: 3
};
var map = new kakao.maps.Map(container, options); // 지도 생성
var marker; // 마커 

    // 장소 검색 함수
function searchLocation() {
    const query = document.getElementById('searchQuery').value;
    const resultDiv = document.getElementById('result'); // 결과 표시 영역
    
    resultDiv.innerHTML = ''; // 이전 결과 제거
    clearMarkers(); // 기존 마커 제거

    if (!query) {
        alert('검색어를 입력하세요.');
        return;
    }

     // 서버에서 장소 검색
    fetch(`/api/search_location?query=${query}`)
        .then(response => response.json())
        .then(data => {
            console.log("검색 결과:", data);
            if (data.lat && data.lng) {
                const position = new kakao.maps.LatLng(data.lat, data.lng);               
                
                // 새로운 마커 추가
                marker = new kakao.maps.Marker({
                    position: position,
                    map: map
                });

                
                // 지도 위치 이동
                map.setCenter(position);

                // 지도 URL 및 길찾기 URL 생성
                const mapUrl = createMapUrl(data.name, data.lat, data.lng);
                const routeUrl = createRouteUrl(data.name, data.lat, data.lng);

                // 결과 표시 및 링크 추가
                resultDiv.innerHTML = `
                    <strong>${data.name}</strong><br>
                    <a href="${mapUrl}" target="_blank">지도 보기</a> | 
                    <a href="${routeUrl}" target="_blank">길찾기</a>`;


            } else {
                alert('위치를 찾을 수 없습니다.');
            }
        })
        .catch(error => console.error('Error:', error));
}

// 지도 URL 생성 함수
function createMapUrl(name, lat, lng) {
    if (name && lat && lng) {
        // 이름, 위도, 경도 기반 지도 URL
        return `https://map.kakao.com/link/map/${encodeURIComponent(name)},${lat},${lng}`;
    } else if (lat && lng) {
        // 위도, 경도 기반 지도 URL
        return `https://map.kakao.com/link/map/${lat},${lng}`;
    }
    return null;
}

// 길찾기 URL 생성 함수
function createRouteUrl(name, lat, lng) {
    if (name && lat && lng) {
        // 이름, 위도, 경도 기반 길찾기 URL
        return `https://map.kakao.com/link/to/${encodeURIComponent(name)},${lat},${lng}`;
    }
    return null;
}

 // 기존 마커 제거
 function clearMarkers() {
    if (marker) {
        marker.setMap(null);
        marker = null;
    }
}

function goToLogin() {
    window.location.href = "/login";
}