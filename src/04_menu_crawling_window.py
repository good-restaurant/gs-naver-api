# ===== 환경 세팅 (Windows 전용) =====
# pip install selenium webdriver-manager pandas

import re
import time
import random
from typing import List, Dict, Tuple, Optional

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service


# ========= 공통: Selenium 드라이버 =========
def build_driver(headless: bool = True) -> Tuple[webdriver.Chrome, WebDriverWait]:
    chrome_options = Options()

    if headless:
        chrome_options.add_argument("--headless=new")

    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--lang=ko-KR")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    wait = WebDriverWait(driver, 15)

    return driver, wait


# ========= 유틸 =========
def human_sleep(a=0.6, b=1.4):
    time.sleep(random.uniform(a, b))


def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def extract_price_num(price_str: str) -> Optional[int]:
    if not price_str:
        return None
    m = re.search(r"(\d[\d,]*)", price_str.replace(" ", ""))
    if not m:
        return None
    return int(m.group(1).replace(",", ""))


# ========= 페이지 이동 및 메뉴 탐색 =========
def open_place_and_go_menu(driver: webdriver.Chrome, wait: WebDriverWait, place_id: str) -> Dict:
    info = {"loaded": False, "menu_text_available": False, "image_menu_only": False, "error": None}

    home_url = f"https://pcmap.place.naver.com/restaurant/{place_id}/home"
    driver.get(home_url)

    try:
        wait.until(EC.presence_of_element_located((By.ID, "app-root")))
        info["loaded"] = True
    except Exception as e:
        info["error"] = f"home load fail: {e}"
        return info

    human_sleep()

    opened_menu = False

    try:
        candidates = driver.find_elements(
            By.XPATH,
            "//a[(contains(., '메뉴') and (@role='tab' or contains(@href, '/menu')))] | //button[contains(., '메뉴')]"
        )
        if candidates:
            candidates[0].click()
            opened_menu = True
            human_sleep(0.8, 1.6)
    except Exception:
        pass

    if not opened_menu:
        try:
            for _ in range(6):
                driver.execute_script("window.scrollBy(0, 800);")
                human_sleep(0.3, 0.6)
                header = driver.find_elements(By.XPATH, "//h2[contains(normalize-space(.), '메뉴')]")
                if header:
                    opened_menu = True
                    break
        except Exception:
            pass

    try:
        img_menu_btn = driver.find_elements(By.XPATH, "//*[contains(., '메뉴판 이미지로 보기')]")
        if img_menu_btn and not opened_menu:
            info["image_menu_only"] = True
            return info
    except Exception:
        pass

    try:
        menu_section = driver.find_elements(
            By.XPATH, "//h2[contains(., '메뉴')]/following-sibling::*[1]"
        )
        if menu_section:
            lis = driver.find_elements(
                By.XPATH, "//div[contains(@class,'place_section_content')]//li"
            )
            info["menu_text_available"] = len(lis) > 0
        else:
            if driver.find_elements(By.XPATH, "//*[contains(., '메뉴판 이미지로 보기')]"):
                info["image_menu_only"] = True
    except Exception:
        pass

    return info


# ========= 메뉴 파싱 =========
def parse_menu_items(driver: webdriver.Chrome) -> List[Tuple[str, Optional[str]]]:
    results = []

    items = driver.find_elements(
        By.XPATH,
        "//div[contains(@class,'place_section_content')]//li"
    )

    if not items:
        return []

    for li in items:
        raw = clean_text(li.text)
        if not raw:
            continue
        lines = [clean_text(x) for x in raw.split("\n") if x.strip()]
        if not lines:
            continue

        price_line = None
        for line in reversed(lines):
            if "원" in line and re.search(r"\d", line):
                price_line = line
                break

        if price_line:
            name_line = next((l for l in lines if l != price_line), price_line)
            results.append((name_line, price_line))
        else:
            results.append((lines[0], None))

    return results


# ========= 전체 크롤링 =========
def crawl_naver_menu(place_ids: List[str], headless: bool = True) -> pd.DataFrame:
    driver, wait = build_driver(headless=headless)
    rows = []

    try:
        for pid in place_ids:
            try:
                meta = open_place_and_go_menu(driver, wait, pid)

                if not meta["loaded"]:
                    rows.append({
                        "place_id": pid, "menu": None, "price": None,
                        "price_num": None, "currency": "KRW",
                        "note": "페이지 로딩 실패"
                    })
                    continue

                if meta["image_menu_only"]:
                    rows.append({
                        "place_id": pid, "menu": None, "price": None,
                        "price_num": None, "currency": "KRW",
                        "note": "메뉴판 이미지 전용"
                    })
                    continue

                items = parse_menu_items(driver)

                if not items:
                    rows.append({
                        "place_id": pid, "menu": None, "price": None,
                        "price_num": None, "currency": "KRW",
                        "note": "텍스트 메뉴 없음"
                    })
                    continue

                for name, price in items:
                    rows.append({
                        "place_id": pid,
                        "menu": name,
                        "price": price,
                        "price_num": extract_price_num(price) if price else None,
                        "currency": "KRW",
                        "note": None
                    })

            except Exception as e:
                rows.append({
                    "place_id": pid, "menu": None, "price": None,
                    "price_num": None, "currency": "KRW",
                    "note": f"ERROR: {e}"
                })

            human_sleep(0.8, 1.6)

    finally:
        driver.quit()

    df = pd.DataFrame(rows)
    return df


# ========= 실행 =========
if __name__ == "__main__":

    # CSV 절대경로 (Windows)
    csv_path = r"C:\All4land_Project\good_restaurant_placeid_temp.csv"

    print(f"CSV 읽는 중: {csv_path}")

    # place_id 컬럼 읽기
    df_in = pd.read_csv(csv_path)

    if "place_id" not in df_in.columns:
        raise Exception("CSV에 'place_id' 컬럼이 없습니다!")

    # place_id 리스트로 변환
    place_ids = df_in["place_id"].astype(str).dropna().tolist()

    print(f"총 {len(place_ids)}개의 place_id 읽음")

    # 크롤링 실행
    result = crawl_naver_menu(place_ids, headless=True)

    # 결과 저장 경로 지정
    output_path = r"C:\All4land_Project\naver_menu_result.csv"
    result.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"✔ 크롤링 완료 → 저장됨: {output_path}")

