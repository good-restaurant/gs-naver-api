# ===== 환경 세팅 (Colab 한정) =====
# !pip install selenium

import re
import time
import random
from typing import List, Dict, Tuple, Optional

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


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

    # chromedriver 경로 환경에 맞게 수정
    service = Service()  # PATH가 잡혀 있으면 비워도 됩니다.
    driver = webdriver.Chrome(service=service, options=chrome_options)
    wait = WebDriverWait(driver, 15)
    return driver, wait


# ========= 유틸 =========
def human_sleep(a=0.6, b=1.4):
    time.sleep(random.uniform(a, b))


def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def extract_price_num(price_str: str) -> Optional[int]:
    """
    '12,000원', '12000 원', '~12,000원', '12,000 ~' 형태에서 숫자만 추출.
    범위/시가/변동가 등은 첫 숫자 기준.
    """
    if not price_str:
        return None
    # 한글 '원' 제거 전 숫자패턴
    m = re.search(r"(\d[\d,]*)", price_str.replace(" ", ""))
    if not m:
        return None
    return int(m.group(1).replace(",", ""))


# ========= 핵심: 메뉴 섹션 진입 및 파싱 =========
def open_place_and_go_menu(driver: webdriver.Chrome, wait: WebDriverWait, place_id: str) -> Dict:
    """
    레스토랑 홈 진입 -> '메뉴' 탭/섹션으로 이동 시도
    반환 dict:
      {
        "loaded": bool,              # 페이지 로딩 성공 여부
        "menu_text_available": bool, # 텍스트 기반 메뉴 섹션 존재 여부(=이미지 메뉴만 있으면 False)
        "image_menu_only": bool,     # '메뉴판 이미지로 보기' 케이스
        "error": Optional[str]
      }
    """
    info = {"loaded": False, "menu_text_available": False, "image_menu_only": False, "error": None}

    # ① 홈 URL (혹시 메뉴 서브 라우팅이 막힌 경우 대비)
    home_url = f"https://pcmap.place.naver.com/restaurant/{place_id}/home"
    driver.get(home_url)
    try:
        wait.until(EC.presence_of_element_located((By.ID, "app-root")))
        info["loaded"] = True
    except Exception as e:
        info["error"] = f"home load fail: {e}"
        return info

    human_sleep()

    # ② '메뉴' 탭/섹션으로 이동
    #    - 탭 버튼: 텍스트에 '메뉴' 포함한 버튼/링크 찾기
    #    - 혹은 스크롤로 '메뉴' 섹션 헤더를 찾아 내려가기
    opened_menu = False

    # (A) 탭/네비게이션 시도
    try:
        # 메뉴로 바로 가는 앵커(내부 라우팅) 혹은 탭(역할=tab/버튼) 탐색
        candidates = driver.find_elements(
            By.XPATH,
            "//a[(contains(., '메뉴') and (@role='tab' or contains(@href, '/menu')))] | "
            "//button[contains(., '메뉴')]"
        )
        if candidates:
            try:
                candidates[0].click()
                opened_menu = True
                human_sleep(0.8, 1.6)
            except Exception:
                pass
    except Exception:
        pass

    # (B) 스크롤 다운 후 섹션 헤더 탐색 (백업 루트)
    if not opened_menu:
        try:
            # 여러 번 천천히 스크롤
            for _ in range(6):
                driver.execute_script("window.scrollBy(0, 800);")
                human_sleep(0.3, 0.6)
                header = driver.find_elements(
                    By.XPATH,
                    "//h2[.//div[contains(normalize-space(.), '메뉴')] or contains(normalize-space(.), '메뉴')]"
                )
                if header:
                    opened_menu = True
                    break
        except Exception:
            pass

    # ③ 메뉴판 이미지 케이스 감지
    try:
        img_menu_btn = driver.find_elements(
            By.XPATH, "//*[contains(., '메뉴판 이미지로 보기')][self::a or self::button or self::span]"
        )
        if img_menu_btn and not opened_menu:
            # '메뉴' 섹션으로 못 갔는데 이미지 보기만 보인다 → 이미지 메뉴 전용일 확률 높음
            info["image_menu_only"] = True
            info["menu_text_available"] = False
            return info
    except Exception:
        pass

    # ④ 텍스트 메뉴 목록 존재 확인
    try:
        # '메뉴' 섹션 헤더 바로 아래의 컨텐츠 영역 찾기
        menu_section = driver.find_elements(
            By.XPATH,
            "//h2[.//div[contains(normalize-space(.), '메뉴')] or contains(normalize-space(.), '메뉴')]/following-sibling::*[1]"
        )
        if menu_section:
            # 보통 ul/li 구조가 있음
            lis = driver.find_elements(By.XPATH, "//div[contains(@class,'place_section_content')]//li")
            if lis:
                info["menu_text_available"] = True
            else:
                # li가 안 잡히면 다른 텍스트 블록 기반일 수 있으니 백업 탐색
                any_texty = driver.find_elements(
                    By.XPATH,
                    "//div[contains(@class,'place_section_content')]//*[self::div or self::span or self::p][contains(., '원')]"
                )
                info["menu_text_available"] = len(any_texty) > 0
        else:
            # 메뉴 섹션 자체가 없고 이미지 버튼만 있으면 이미지 메뉴 케이스로 표시
            if driver.find_elements(
                By.XPATH, "//*[contains(., '메뉴판 이미지로 보기')][self::a or self::button or self::span]"
            ):
                info["image_menu_only"] = True
    except Exception:
        pass

    return info


def parse_menu_items(driver: webdriver.Chrome) -> List[Tuple[str, Optional[str]]]:
    """
    현재 페이지에서 텍스트 기반 메뉴목록을 파싱.
    반환: [(menu_name, price_text or None), ...]
    """
    results = []

    # 1) 일반적인 ul/li 구조
    items = driver.find_elements(
        By.XPATH,
        "//div[contains(@class,'place_section_content')]//li"
    )
    if not items:
        # 2) 백업: 가격(원) 텍스트가 포함된 블록 단위 긁기
        blocks = driver.find_elements(
            By.XPATH,
            "//div[contains(@class,'place_section_content')]//*[self::div or self::li]"
        )
        for b in blocks:
            txt = clean_text(b.text)
            if ("원" in txt) and len(txt) <= 80:
                # 간단 패턴: "김치찌개 8,000원" 형태에서 분리 시도
                # 가격 쪽을 뒤에서부터 찾음
                price_part = None
                m = re.search(r"(\d[\d,]*\s*원)", txt)
                if m:
                    price_part = m.group(1)
                    name_part = clean_text(txt.replace(price_part, ""))
                else:
                    name_part = txt
                if name_part:
                    results.append((name_part, price_part))
        return dedup_menu(results)

    # 1) li 구조 파싱(우선)
    for li in items:
        raw = clean_text(li.text)
        if not raw:
            continue
        # 흔한 라인: "제목", "설명", "8,000원" (여러 줄) → 줄 단위 분해
        lines = [clean_text(x) for x in raw.split("\n") if clean_text(x)]
        if not lines:
            continue

        # 가격 포함 라인 찾기(마지막 줄에 있을 확률↑)
        price_line = None
        for line in reversed(lines):
            if "원" in line and re.search(r"\d", line):
                price_line = line
                break

        if price_line:
            # 메뉴명 후보: 가격 줄 제외한 가장 앞줄
            name_line = None
            for line in lines:
                if line != price_line:
                    name_line = line
                    break
            if not name_line:
                # 하나뿐이면 전부 이름으로 처리
                name_line = price_line
                price_line = None

            name_line = clean_text(name_line)
            price_line = clean_text(price_line) if price_line else None

            # 너무 긴 소개/설명만 잡히면 스킵(유연한 한계선)
            if len(name_line) > 60:
                continue

            # '원'이 있는데 숫자가 없으면 무시
            if price_line and (not re.search(r"\d", price_line)):
                price_line = None

            results.append((name_line, price_line))
        else:
            # 가격이 없는 메뉴(설명만)일 수도 있음 → 이름만 추가
            if len(lines[0]) <= 60:
                results.append((lines[0], None))

    return dedup_menu(results)


def dedup_menu(pairs: List[Tuple[str, Optional[str]]]) -> List[Tuple[str, Optional[str]]]:
    """중복 제거(이름+가격 조합 기준)"""
    seen = set()
    uniq = []
    for name, price in pairs:
        key = (name, price or "")
        if key in seen:
            continue
        seen.add(key)
        uniq.append((name, price))
    return uniq


# ========= 메인: place_id 리스트 받아 메뉴/가격 수집 =========
def crawl_naver_menu(place_ids: List[str], headless: bool = True) -> pd.DataFrame:
    driver, wait = build_driver(headless=headless)
    rows = []
    try:
        for pid in place_ids:
            status = {"place_id": pid, "ok": False, "image_menu_only": False, "error": None}
            try:
                meta = open_place_and_go_menu(driver, wait, pid)
                if not meta.get("loaded"):
                    status["error"] = meta.get("error") or "page-load-failed"
                    rows.append({
                        "place_id": pid, "menu": None, "price": None, "price_num": None,
                        "currency": "KRW", "note": f"ERROR: {status['error']}"
                    })
                    continue

                if meta.get("image_menu_only") and not meta.get("menu_text_available"):
                    status["image_menu_only"] = True
                    rows.append({
                        "place_id": pid, "menu": None, "price": None, "price_num": None,
                        "currency": "KRW", "note": "메뉴판 이미지 전용(텍스트 없음)"
                    })
                    continue

                # 텍스트 메뉴 파싱
                items = parse_menu_items(driver)
                if not items:
                    rows.append({
                        "place_id": pid, "menu": None, "price": None, "price_num": None,
                        "currency": "KRW", "note": "메뉴 섹션은 있으나 텍스트 파싱 실패"
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
                status["ok"] = True

            except Exception as e:
                rows.append({
                    "place_id": pid, "menu": None, "price": None, "price_num": None,
                    "currency": "KRW", "note": f"ERROR: {e}"
                })

            # 로봇 차단 회피를 위한 휴식
            human_sleep(0.8, 1.8)

    finally:
        driver.quit()

    df = pd.DataFrame(rows, columns=["place_id", "menu", "price", "price_num", "currency", "note"])
    return df


# ========= 사용 예시 =========
if __name__ == "__main__":
    # 테스트할 Place ID들을 넣어주세요.
    sample_place_ids = [
        "1024024476",
        "98765432",
        "11727802",
        "1184218781",
        "11839239",
        "1393205104",
        "38229327",
        "1718508266",
        "19867541",
        "37445988",
        "1858307238",
        "1209239188"
    ]
    if sample_place_ids:
        result = crawl_naver_menu(sample_place_ids, headless=True)
        print(result.to_string(index=False))
    else:
        print("sample_place_ids 리스트에 네이버 플레이스 ID를 넣어 실행하세요.")
