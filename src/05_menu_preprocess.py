# ===== 환경 세팅 (Windows 전용) =====
import pandas as pd
import re

# CSV 파일 읽기
df = pd.read_csv('naver_menu_result.csv')

# 메뉴와 가격을 분리하는 함수
def extract_menu_and_price(text):
    """
    텍스트에서 메뉴명과 가격을 분리
    """
    if pd.isna(text):
        return None, None

    text = str(text).strip()

    # 가격 패턴: 숫자+원 또는 숫자+,+숫자+원
    price_patterns = [
        r'([\d,]+원)',  # 기본 가격 패턴
        r'₩([\d,]+)',   # ₩ 기호가 있는 경우
        r'(\d+)원',     # 콤마 없는 가격
    ]

    price = None
    menu = text

    # 가격 추출
    for pattern in price_patterns:
        match = re.search(pattern, text)
        if match:
            price = match.group(0)
            # 메뉴명에서 가격 부분 제거
            menu = re.sub(pattern, '', text).strip()
            break

    # 가격 정리: 숫자만 추출
    if price:
        # 숫자만 추출 (콤마, 원, ₩ 등 모두 제거)
        price = re.sub(r'[^\d]', '', price)

    return menu, price

# 데이터 전처리
processed_data = []

for idx, row in df.iterrows():
    place_id = row.get('place_id', '')
    menu_text = row.get('menu', '')

    menu, price = extract_menu_and_price(menu_text)

    # 메뉴명이 있고, 길이가 500자 이하인 경우만 추가
    if menu and price and len(menu) <= 255:
        processed_data.append({
            'place_id': place_id,
            'menu': menu,
            'price': price
        })

# 새로운 데이터프레임 생성
processed_df = pd.DataFrame(processed_data)

# 결과 저장
output_file = 'naver_menu_processed.csv'
processed_df.to_csv(output_file, index=False, encoding='utf-8-sig')

print(f"전처리 완료! 총 {len(processed_df)}개의 메뉴 항목이 처리되었습니다.")
print(f"(메뉴명 길이 255자 초과 항목은 제외됨)")
print(f"\n결과 파일: {output_file}")
print(f"\n처리 결과 미리보기:")
print(processed_df.head(10))

# 통계 정보
print(f"\n=== 통계 정보 ===")
print(f"총 레스토랑 수: {processed_df['place_id'].nunique()}")
print(f"총 메뉴 수: {len(processed_df)}")