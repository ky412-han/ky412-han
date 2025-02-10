document.addEventListener("DOMContentLoaded", async () => {
  // 슬라이드 데이터를 가져오는 함수
  async function fetchSlides(duration) {
    const response = await fetch(`/api/tour/spot/${duration}`);
    if (!response.ok) throw new Error("Failed to fetch slides");
    const data = await response.json();
    console.log("API Response:", data);
    return data;
  }

  function groupByLocation(data) {
    return data.reduce((grouped, item) => {
      // item.location을 키로 사용하여 그룹화
      if (!grouped[item.location]) {
        grouped[item.location] = [];
      }
      grouped[item.location].push(item);
      return grouped;
    }, {}); // 초기값은 빈 객체
  }

  function createSlide(location, schedules) {
    let imagesHTML = "";
    let namesHTML = "";
    let day = schedules[0].day
    
    schedules.forEach(schedule => {
      if (schedule.spots && Array.isArray(schedule.spots)) {
        schedule.spots.slice(0, 5).forEach(spot => {
          imagesHTML += `<img src="${spot.image_url || '/static/images/default.jpg'}" alt="${spot.name || 'No Name'}">`;
          namesHTML += `<span style="flex: 1; text-align: center;">${spot.name || 'No Name'}</span>`;
        });
      }
    });

    return `
      <div class="swiper-slide">
        <p>${location} 여행 일정 day-${day}</p>
        <div>${imagesHTML}</div>
        <p style="display: flex; justify-content: space-between; width: 1500px; margin: 0 auto;">
          ${namesHTML}
        </p>
      </div>
    `;
  }
  // function createSwiperContainer(location) {
  //   const container = document.createElement("div");
  //   container.classList.add(`swiper-container-${location}`, "swiper-container");

  //   container.innerHTML = `
  //     <div class="swiper-wrapper"></div>
  //     <div class="swiper-button-prev"></div>
  //     <div class="swiper-button-next"></div>
  //     <div class="swiper-pagination"></div>
  //   `;

  //   const pageContent = document.getElementById("page2-content");
  //   if (!pageContent) {
  //     console.error("Page content container not found");
  //     return;
  //   }

  //   pageContent.appendChild(container);
  // }

  function addSlide(swiperInstance, schedule) {
    if (!swiperInstance || typeof swiperInstance.appendSlide !== "function") {
      console.error("Invalid Swiper instance:", swiperInstance);
      return;
    }
  
    const slide = `
      <div class="swiper-slide">
        <p>${schedule.description || 'No Description'}, ${schedule.day}일차</p>
        <div>
          <img src="${schedule.spots[0].image_url}">
          <img src="${schedule.spots[1].image_url}">
          <img src="${schedule.spots[2].image_url}">
          <img src="${schedule.spots[3].image_url}">
          ${schedule.spots[4] ? `<img src="${schedule.spots[4].image_url}">` : ''}
        </div>
        <p style="display: flex; justify-content: space-between; width: 1500px; margin: 0 auto; margin-right:25px;"> 
          <span style="flex: 1; text-align: center;">${schedule.spots[0].name}</span>
          <span style="flex: 1; text-align: center;">${schedule.spots[1].name}</span>
          <span style="flex: 1; text-align: center;">${schedule.spots[2].name}</span>
          <span style="flex: 1; text-align: center;">${schedule.spots[3].name}</span>
          ${schedule.spots[4] ? `<span style="flex: 1; text-align: center;">${schedule.spots[4].name}</span>` : ''}      
        </p>
      </div>
    `;
  
    swiperInstance.appendSlide(slide);
    swiperInstance.update();
  }

  async function initializeSwiper(duration) {
    const schedules = await fetchSlides(duration);
    const regionData = Object.values(schedules);
    const groupedByLocation = groupByLocation(regionData);

    const swiperWrapper = document.querySelector(".swiper-wrapper");
    if (!swiperWrapper) {
      console.error("Swiper wrapper not found!");
      return;
    }

    Object.entries(groupedByLocation).forEach(([location, schedules]) => {
      const slideHTML = createSlide(location, schedules);
      swiperWrapper.innerHTML += slideHTML;
    });

    new Swiper(".swiper-container", {
      loop: false,
      slidesPerView: 1,
      slidesPerGroup: 1,
      spaceBetween: 20,
      navigation: {
        nextEl: ".swiper-button-next",
        prevEl: ".swiper-button-prev",
      },
      pagination: {
        el: ".swiper-pagination",
        clickable: true,
      },
      autoplay: {
        delay: 3000,
        disableOnInteraction: false,
      },
    });
  }


  // await initializeSwiper("당일치기");
  await initializeSwiper("1박2일");
  await initializeSwiper("2박3일");
});
    // // 지역별로 Swiper 컨테이너 생성 및 초기화
    // Object.entries(groupedByLocation).forEach(([location, schedules]) => {
    //   console.log(`Initializing Swiper for location: ${location}`);

    //   // 동적으로 Swiper 컨테이너 생성
    //   createSwiperContainer(location);

    //   const containerSelector = `.swiper-container-${location}`;
    //   const container = document.querySelector(containerSelector);

    //   if (!container) {
    //     console.error(`Swiper container not found for location: ${location}`);
    //     return;
    //   }
    //   // Swiper 중복 초기화 방지
    //   if (container.swiper) {
    //     console.warn(`Swiper already initialized for container: ${containerSelector}`);
    //     return;
    //   }
    //   const swiper = new Swiper(containerSelector, {
    //     loop: false,
    //     slidesPerView: 1, // 한 화면에 보이는 슬라이드 수
    //     slidesPerGroup: 1,
    //     spaceBetween: 20,
    //     observer: true,
    //     observeParents: true,
    //     navigation: {
    //       nextEl: `${containerSelector} .swiper-button-next`,
    //       prevEl: `${containerSelector} .swiper-button-prev`,
    //     },
    //     pagination: {
    //       el: `${containerSelector} .swiper-pagination`,
    //       clickable: true,
    //     },
    //     autoplay: {
    //       delay: 3000,
    //       disableOnInteraction: false,
    //     },
    //   });

    //   // 슬라이드 추가
    //   schedules.forEach(schedule => addSlide(swiper, schedule));
    // });
 
 
  // // 슬라이드 추가 함수
  // function addSlide(swiperInstance, spot) {
  //   const slide = `
  //     <div class="swiper-slide">
  //       <img src="${spot.image_url || '/static/images/default.jpg'}" alt="${spot.name || 'No Name'}">
  //       <p>${spot.name || 'No Name'}</p>
  //       <p>${spot.description || 'No Description'}</p>
  //     </div>
  //   `;
  
  //   // console.log("Adding slide:", slide);
  
  //   // Swiper에 슬라이드 추가
  //   swiperInstance.appendSlide(slide);
  
  //   // Swiper 강제 업데이트
  //   swiperInstance.update();
  // }

  // // Swiper 초기화 및 슬라이드 추가
  // async function initializeSwiper(duration) {
  //   const groupedSchedules = await fetchSlides(duration);    
  //   console.log("groupedSchedules:", groupedSchedules);
  //   const regionData = Object.values(groupedSchedules);

  //   const groupedByLocation = groupByLocation(regionData);
  //   console.log("groupedByLocation:", groupedByLocation);

  //   // 각 지역별로 Swiper 초기화
    
     
  //     const swiper = new Swiper(containerSelector, {
  //       loop: false,
  //       slidesPerView: Object.keys(groupedByLocation).length >= 5 ? 5 : Object.keys(groupedByLocation).length,
  //         navigation: {
  //           nextEl: `${containerSelector} .swiper-button-next`,
  //           prevEl: `${containerSelector} .swiper-button-prev`,
  //         },
  //         pagination: {
  //           el: `${containerSelector} .swiper-pagination`,
  //           clickable: true,
  //         },
  //         slidesPerGroup: Object.keys(groupedByLocation).length >= 5 ? 5 : Object.keys(groupedByLocation).length, // 5개 이상이면 5개, 아니면 데이터 개수만큼, // 한 번에 넘기는 슬라이드 수
  //         observer: true, // DOM 변화를 감지
  //         observeParents: true, // 부모 요소의 DOM 변화를 감지
  //         spaceBetween: 20, // 슬라이드 간 간격(px)
  //         autoplay: {
  //           delay: 3000, // 자동 넘김 시간
  //           disableOnInteraction: false,
  //         },
  //       });
  //       // 슬라이드 추가
  //     Object.entries(groupedByLocation).forEach(([location, schedules]) => {
  //       console.log(`Adding slides for location: ${location}`);
  //       schedules.forEach(schedule => {
  //         if (schedule.spots && Array.isArray(schedule.spots)) {
  //           schedule.spots.forEach(spot => {
  //             addSlide(swiper, spot);
  //           });
  //         }
  //       });
  //     });
    
  //     swiper.update(); // Swiper 강제 업데이트
  // }

  // Swiper 초기화 호출
  // await initializeSwiper("당일치기");
  // await initializeSwiper("1박2일");
  // await initializeSwiper("2박3일");
  // await initializeSwiper(".swiper-container-1", "당일치기");
  // await initializeSwiper(".swiper-container-2", "1박2일");
  // await initializeSwiper(".swiper-container-3", "2박3일");
