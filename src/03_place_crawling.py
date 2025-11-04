# ===== 1️⃣ 환경 세팅 (Colab 한정) =====
# !apt-get update -qq
# !apt-get install -y unzip > /dev/null 2>&1
# !wget -q https://storage.googleapis.com/chrome-for-testing-public/131.0.6778.85/linux64/chrome-linux64.zip
# !wget -q https://storage.googleapis.com/chrome-for-testing-public/131.0.6778.85/linux64/chromedriver-linux64.zip
# !unzip -q chrome-linux64.zip
# !unzip -q chromedriver-linux64.zip
# !mv chrome-linux64 /usr/local/chrome
# !mv chromedriver-linux64/chromedriver /usr/local/bin/chromedriver
# !chmod +x /usr/local/bin/chromedriver
# !pip install selenium==4.25.0 pandas -q


# ===== 2️⃣ 드라이버 및 공통 함수 =====
import pandas as pd, re, time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

chrome_service = Service('/usr/local/bin/chromedriver')
chrome_options = Options()
chrome_options.binary_location = '/usr/local/chrome/chrome'
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--window-size=1920,1080')

driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
wait = WebDriverWait(driver, 15)
print("✅ ChromeDriver 실행 완료")

def switch_left():
    """왼쪽 검색결과 iframe 전환"""
    driver.switch_to.default_content()
    wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "searchIframe")))

def switch_right():
    """오른쪽 상세정보 iframe 전환"""
    driver.switch_to.default_content()
    wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "entryIframe")))

# ===== 3️⃣ 상세페이지 크롤러 (메뉴, 리뷰, 별점, 편의시설) =====
def crawl_place_details(driver):
    """현재 entryIframe 안에서 메뉴, 편의시설, 리뷰, 별점을 모두 크롤링"""
    data = {
        "menus": [],
        "facilities": [],
        "reviews": [],
        "rating": None
    }

    # ⭐ 별점
    try:
        data["rating"] = driver.find_element(By.CLASS_NAME, "PXMot").text.strip()
    except:
        data["rating"] = None

    # 🍽 메뉴 + 가격
    try:
        menu_section = driver.find_element(
            By.XPATH, "//div[contains(@class,'place_section') and .//div[text()='메뉴']]"
        )
        menu_items = menu_section.find_elements(By.TAG_NAME, "li")
        for item in menu_items:
            try:
                name = item.find_element(By.XPATH, ".//a[contains(@href, '/menu/')]").text.strip()
            except:
                name = None
            try:
                price = item.find_element(By.XPATH, ".//div[contains(text(),'원')]").text.strip()
            except:
                price = None
            if name or price:
                data["menus"].append(f"{name} ({price})" if price else name)
    except:
        data["menus"] = []

    # 🏪 편의시설
    try:
        facilities_section = driver.find_element(
            By.XPATH, "//div[contains(@class,'place_section') and .//div[contains(text(),'편의시설')]]"
        )
        facility_items = facilities_section.find_elements(By.XPATH, ".//span")
        for f in facility_items:
            text = f.text.strip()
            if text:
                data["facilities"].append(text)
    except:
        data["facilities"] = []

    # 💬 방문자 리뷰
    try:
        review_section = driver.find_element(
            By.XPATH, "//div[contains(@class,'place_section') and .//div[contains(text(),'리뷰')]]"
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", review_section)
        time.sleep(1.5)
        review_texts = driver.find_elements(By.XPATH, "//span[contains(@class,'zPfVt')]")
        for r in review_texts:
            text = r.text.strip()
            if text and len(text) > 3:
                data["reviews"].append(text)
    except:
        data["reviews"] = []

    return data

# ===== 4️⃣ 메인 크롤러 (검색 → 상세 진입 → 데이터 수집) =====
def crawl_store_info(name, sig, emd):
    # 🔹 "점" 예외처리
    query = name if ("점" in name and "반점" not in name) else f"{name} {sig} {emd}"

    print(f"🔍 검색 중: {query}")
    result = {
        "restaurant_name": name,
        "sig_kor_nm": sig,
        "emd_kor_nm": emd,
        "place_id": None,
        "rating": None,
        "menus": None,
        "facilities": None,
        "reviews": None
    }

    try:
        driver.get("https://map.naver.com/v5/search/" + query)
        time.sleep(2)

        # ✅ CASE 1: 검색 결과 리스트 존재
        try:
            switch_left()
            items = driver.find_elements(By.XPATH, '//*[@id="_pcmap_list_scroll_container"]/ul/li')
            if items:
                items[0].find_element(By.TAG_NAME, "a").send_keys(Keys.ENTER)
                switch_right()
        except:
            # ✅ CASE 2: 바로 상세페이지로 진입
            print("ℹ️ 리스트 없이 상세페이지로 바로 이동 감지")
            switch_right()

        # ===== 상세 정보 수집 =====
        current_url = driver.current_url
        if m := re.search(r'place/(\d+)', current_url):
            result["place_id"] = m.group(1)

        details = crawl_place_details(driver)
        result.update({
            "rating": details["rating"],
            "menus": ", ".join(details["menus"]) if details["menus"] else None,
            "facilities": ", ".join(details["facilities"]) if details["facilities"] else None,
            "reviews": " | ".join(details["reviews"][:5]) if details["reviews"] else None
        })

        print(f"✅ 완료: {name} (placeId={result['place_id']})")
        return result

    except Exception as e:
        print(f"⚠️ 예외 발생: {e}")
        return result


# ===== 5️⃣ 전체 CSV 실행 및 저장 =====
df = pd.read_csv("good_restaurant_temp.csv", encoding="utf-8")
print(f"📄 총 {len(df)}개 데이터 로드 완료")

results = []
for i, row in df.iterrows():
    res = crawl_store_info(row["restaurant_name"], row["sig_kor_nm"], row["emd_kor_nm"])
    results.append(res)

output = pd.DataFrame(results)
output.to_csv("good_restaurant_detail.csv", index=False, encoding="utf-8-sig")
print("🎉 크롤링 완료 → good_restaurant_detail.csv 저장 완료")

driver.quit()
