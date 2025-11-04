# 🍽️ 모범음식점 데이터 구축 과정
> 공공데이터와 네이버 API/크롤링을 기반으로 전국 모범음식점 데이터를 정제·보완·통합하는 데이터 구축 과정입니다.

---

## 📖 개요
이 저장소는 **전국 모범음식점 데이터의 구축 과정**을 기록하고 관리하기 위한 공간입니다.  
원본 공공데이터를 정제하고, 네이버 API 및 크롤링을 통해 보완 데이터를 수집하여  
최종적으로 **지도 서비스 및 공간정보 플랫폼**에서 활용 가능한 형태로 가공합니다.

---


## 🧹 1️⃣ 데이터 전처리 (`01_preprocess.py`)
> 원본 엑셀(`모범음식점_리스트_지오코딩_4326.xlsx`)을 정제하여 `restaurant_clean.csv`로 저장합니다.
- 중복 제거 (`업소명 + 주소`)
- 결측치 보완 (`category ← menu`)
- 전화번호 표준화 (`지역번호 규칙`)
- 행정구역 자동 분리 (`ctp_kor_nm`, `sig_kor_nm`)

📄 [자세히 보기](src/01_preprocess.py)

---

## 🔍 2️⃣ 네이버 API 연동 (`02_naver_api_fetch.py`)
> 네이버 Local API를 사용해 `restaurant_name + address`로 검색 후,  
> `category`, `telephone`, `link`, `mapx`, `mapy` 정보를 매칭합니다.

- API 호출 속도 조절 (`time.sleep(0.2)`)
- 카테고리 자동 분리 (`대분류 / 소분류`)
- 결과 엑셀(`output.xlsx`) 저장

📄 [자세히 보기](src/02_naver_api_fetch.py)

---

## 🕸️ 3️⃣ 네이버 플레이스 크롤링 (`03_place_crawling.py`)
> Selenium을 이용하여 네이버 플레이스의 `ID`, `리뷰` 등을 수집합니다.

- `place_id` 기반 크롤링
- `iframe` 전환 및 동적 요소 대기

📄 [자세히 보기](src/03_place_crawling.py)
