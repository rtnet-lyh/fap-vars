import requests
import json
import sys
import re
from pathlib import Path

# 호스트 URL (실제 환경에 맞게 수정하세요)
DEFAULT_HOST = "http://192.168.1.233:8080"  # 예: https://api.example.com
SESSION_PATH = Path(__file__).resolve().parents[1] / "session.md"


def read_session_md(path=SESSION_PATH):
    """api_data/session.md의 ## heading 값을 읽는다."""
    text = Path(path).read_text(encoding="utf-8")
    values = {}
    current_key = None
    current_lines = []

    def flush():
        if current_key:
            values[current_key] = "\n".join(current_lines).strip()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            flush()
            current_key = match.group(1).strip()
            current_lines = []
            continue
        if current_key and line:
            current_lines.append(line)

    flush()
    return values


def require_session_value(session, key):
    value = str(session.get(key) or "").strip()
    if not value:
        raise ValueError(f"{SESSION_PATH}에 {key} 값이 없습니다.")
    return value


def normalize_jsessionid(value):
    text = str(value or "").strip().strip('",')
    match = re.search(r"JSESSIONID=([^;\s,\"]+)", text)
    if match:
        return match.group(1)
    return text


def load_session_config():
    session = read_session_md()
    host = str(session.get("URL") or DEFAULT_HOST).strip().rstrip("/")
    language = str(session.get("language") or "ko-KR").strip()
    jsessionid = normalize_jsessionid(
        session.get("JSESSIONID") or session.get("SESSION_ID")
    )
    if not jsessionid:
        raise ValueError(f"{SESSION_PATH}에 SESSION_ID 또는 JSESSIONID 값이 없습니다.")

    return {
        "host": host,
        "language": language,
        "jsessionid": jsessionid,
        "application_name": require_session_value(session, "application_name"),
        "type_name": require_session_value(session, "type_name"),
    }


SESSION = load_session_config()
HOST = SESSION["host"]

# 인증 헤더 (필요 시 추가, 예: Bearer 토큰)
HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": f"{SESSION['language']},ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
    "Cookie": f"Language={SESSION['language']}; JSESSIONID={SESSION['jsessionid']}",
    "Referer": f"{HOST}/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest"
}

def get_inspection_items():
    """목록 API로 조건에 맞는 HP-UX + 일상점검(상태점검) 항목 검색"""
    url = f"{HOST}/data/inspection/items"
    params = {
        "filterData": json.dumps([
            {"column": "type_name", "values": [SESSION["type_name"]]},
            {"column": "application_name", "values": [SESSION["application_name"]]}
        ]),
        "selectStartRowNum": 0,
        "selectEndRowNum": 1000  # 결과 수 제한, 필요에 따라 조정
    }
    response = requests.get(url, params=params, headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    print("목록 API 응답 디버깅:", json.dumps(data, indent=2, ensure_ascii=False)[:1000])  # 디버깅용 출력 (첫 1000자)
    return data

def get_item_detail(item_id, mapping_id):
    """상세 API로 item_id 기반 정보 조회 및 mapping_id로 HP-UX 매핑 추출"""
    url = f"{HOST}/data/inspection/items/{item_id}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    data = response.json()["data"]
    
    # item 기본 정보
    item_info = data["item"]
    
    # mappings에서 HP-UX 매핑 찾기 (mapping_id로 필터)
    hpux_mapping = next((m for m in data["mappings"] if m["id"] == mapping_id), None)
    
    return {
        "item_id": item_id,
        "mapping_id": mapping_id,
        # 기본 점검항목 정보 (모달 상세)
        "type_name": item_info.get("type_name"),
        "category_name": item_info.get("category_name"),
        "area_name": item_info.get("area_name"),
        "code": item_info.get("code"),
        "inspection_code": item_info.get("inspection_code"),
        "inspection_name": item_info.get("inspection_name"),
        "inspection_content": item_info.get("inspection_content"),
        # HP-UX 매핑 정보 (모달 상세)
        "application_name": hpux_mapping.get("application_name") if hpux_mapping else None,
        "application_version_name": hpux_mapping.get("application_version_name") if hpux_mapping else None,
        "inspection_command": hpux_mapping.get("inspection_command") if hpux_mapping else None,
        "inspection_output": hpux_mapping.get("inspection_output") if hpux_mapping else None,
        "description": hpux_mapping.get("description") if hpux_mapping else None,
        "inspection_script": hpux_mapping.get("inspection_script") if hpux_mapping else None
    }

def get_item_thresholds(item_id):
    """thresholds API로 기준치 정보 조회 (선택적)"""
    url = f"{HOST}/data/inspection/items/{item_id}/thresholds"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()["data"]["thresholds"]

def main():
    """메인 실행 함수"""
    try:
        # 1. 목록 조회
        print("목록 API 호출 중...")
        list_response = get_inspection_items()
        items = list_response["data"]["items"]
        print(f"총 {len(items)}개의 항목을 찾았습니다.")
        
        results = []
        for i, row in enumerate(items):
            item_id = row["item_id"]
            mapping_id = row["mapping_id"]
            print(f"항목 {i+1}/{len(items)} 처리 중: item_id={item_id}, mapping_id={mapping_id}")
            
            # 2. 상세 조회
            detail = get_item_detail(item_id, mapping_id)
            
            # 3. thresholds 추가 (필요 시 주석 해제)
            # thresholds = get_item_thresholds(item_id)
            # detail["thresholds"] = thresholds
            
            results.append(detail)
        
        # 4. 결과 출력 (JSON 형식)
        output_file = "hpux_inspection_details.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"결과가 {output_file}에 저장되었습니다.")
        
        # 콘솔에도 간단 출력
        for res in results[:5]:  # 처음 5개만 예시로 출력
            print(json.dumps(res, indent=2, ensure_ascii=False))
            print("---")
        
    except requests.exceptions.RequestException as e:
        print(f"API 호출 오류: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"기타 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
