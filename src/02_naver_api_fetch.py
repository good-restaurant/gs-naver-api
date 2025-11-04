import requests
import pandas as pd
import re
import time

# 네이버 API 인증키
client_id = NAVER_CLIENT_ID
client_secret = NAVER_CLIENT_SECRET

# ✅ 주소 정제 함수 (도로명주소만 추출, 건물명/층수 제거)
def clean_address(addr):
    addr = str(addr)
    addr = re.sub(r"\(.*?\)", "", addr)   # 괄호 제거
    addr = addr.split(",")[0]             # 쉼표 이후 제거
    addr = " ".join(addr.split())         # 공백 정리
    return addr.strip()


# ✅ 네이버 Local API 호출
def get_store_info(query):
    url = "https://openapi.naver.com/v1/search/local.json"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret
    }
    params = {"query": query, "display": 1}
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        if data.get("items"):
            return data["items"][0]
    return None

# ✅ 엑셀 불러오기 (엑셀에 반드시 "상호명","도로명주소" 컬럼 있어야 함)
df = pd.read_excel("input.xlsx")

# ✅ 결과 컬럼 추가
new_cols = [
    "cleaned_address", "api_title", "api_link", "api_category", "api_description",
    "api_telephone", "api_address", "api_roadAddress", "api_mapx", "api_mapy"
]
for col in new_cols:
    if col not in df.columns:
        df[col] = ""

# ✅ 각 행 처리
for idx, row in df.iterrows():
    clean_addr = clean_address(row["address"])
    query = f"{row['restaurant_name']} {clean_addr}"

    result = get_store_info(query)
    if result:
        df.at[idx, "cleaned_address"] = clean_addr
        df.at[idx, "api_title"] = result.get("title", "")
        df.at[idx, "api_link"] = result.get("link", "")

        # ✅ 카테고리 분리
        raw_category = result.get("category", "")
        if ">" in raw_category:
            parts = [p.strip() for p in raw_category.split(">")]
            df.at[idx, "category"] = parts[0]  # 대분류
            df.at[idx, "menu"] = parts[-1]     # 소분류
        else:
            df.at[idx, "category"] = raw_category
            df.at[idx, "menu"] = ""

        df.at[idx, "api_description"] = result.get("description", "")
        df.at[idx, "api_telephone"] = result.get("telephone", "")
        df.at[idx, "api_address"] = result.get("address", "")
        df.at[idx, "api_roadAddress"] = result.get("roadAddress", "")
        df.at[idx, "api_mapx"] = result.get("mapx", "")
        df.at[idx, "api_mapy"] = result.get("mapy", "")

    time.sleep(0.2)  # rate-limit 고려

# ✅ 결과 엑셀 저장
df.to_excel("output.xlsx", index=False, engine="openpyxl")
print("✅ 결과 저장 완료: output.xlsx")