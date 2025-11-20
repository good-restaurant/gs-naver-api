# ===== 1️⃣ 환경 세팅 (Windows 전용) =====
import pandas as pd
import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Chrome 자동 경로 관리
chrome_service = Service(ChromeDriverManager().install())
chrome_options = Options()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--start-maximized")
chrome_options.add_argument("--lang=ko-KR")
chrome_options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# ※ headless 모드는 개발 중 비활성화 권장
# chrome_options.add_argument("--headless=new")

driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
wait = WebDriverWait(driver, 15)
print("✅ ChromeDriver 실행 완료")


# ===== 2️⃣ 공통 함수 =====
def switch_left():
    """왼쪽 검색결과 iframe 전환"""
    driver.switch_to.default_content()
    wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "searchIframe")))


def switch_right():
    """오른쪽 상세정보 iframe 전환"""
    driver.switch_to.default_content()
    wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "entryIframe")))


# ===== 3️⃣ Place ID 크롤러 =====
def crawl_place_id(name, sig, emd):
    query = name if ("점" in name and "반점" not in name) else f"{name} {sig} {emd}"
    print(f"🔍 검색 중: {query}")

    result = {
        "restaurant_name": name,
        "sig_kor_nm": sig,
        "emd_kor_nm": emd,
        "place_id": None,
    }

    try:
        driver.get("https://map.naver.com/v5/search/" + query)
        time.sleep(2.5)

        # ✅ CASE 1: 검색 결과 리스트 존재 시 첫 항목 클릭
        try:
            switch_left()
            items = driver.find_elements(By.XPATH, '//*[@id="_pcmap_list_scroll_container"]/ul/li')
            if items:
                items[0].find_element(By.TAG_NAME, "a").send_keys(Keys.ENTER)
                switch_right()
        except:
            # ✅ CASE 2: 바로 상세 페이지 진입
            switch_right()

        # 🔹 URL에서 place_id 추출
        current_url = driver.current_url
        match = re.search(r"place/(\d+)", current_url)
        if match:
            result["place_id"] = match.group(1)

        print(f"✅ 완료: {name} (placeId={result['place_id']})")

    except Exception as e:
        print(f"⚠️ 예외 발생: {e}")

    return result


# ===== 4️⃣ 실행 및 저장 =====
file_path = r"C:\All4land_Project\good_restaurant_temp.csv"  # ✅ 로컬 파일 경로
df = pd.read_csv(file_path, encoding="utf-8")
print(f"📄 총 {len(df)}개 데이터 로드 완료")

results = []
for i, row in df.iterrows():
    res = crawl_place_id(row["restaurant_name"], row["sig_kor_nm"], row["emd_kor_nm"])
    results.append(res)

output = pd.DataFrame(results)
output_path = r"C:\All4land_Project\good_restaurant_placeid.csv"
output.to_csv(output_path, index=False, encoding="utf-8-sig")

print(f"🎉 크롤링 완료 → {output_path} 저장 완료")
driver.quit()
