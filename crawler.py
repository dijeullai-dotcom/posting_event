import requests
from bs4 import BeautifulSoup
import re
import os
import json
import time
from datetime import datetime

# 닉네임 클릭 스크립트에서 고유 ID 추출하는 함수
def extract_user_id(onclick_text):
    if not onclick_text: return None
    match = re.search(r"show_nick_dropdown\([^,]+,\s*'[^']+',\s*'([^']+)'", onclick_text)
    return match.group(1) if match else None

def run_event_crawler():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_dir, 'data.json')
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🚀 실시간 이벤트 데이터 스캔 시작...")
    
    user_post_counts = {}
    page = 1
    stop_scraping = False
    
    while not stop_scraping:
        list_url = f"https://ygosu.com/board/pan_ahrisong/?page={page}"
        try:
            response = requests.get(list_url, headers=headers, timeout=10)
        except Exception as e:
            print(f"네트워크 오류: {e}")
            break
            
        soup = BeautifulSoup(response.text, 'html.parser')
        # 테이블의 행들 추출
        posts = soup.select("table.bd_list tbody tr")
        
        has_normal_post = False
        
        for post in posts:
            # 공지사항은 매 페이지마다 뜨므로 무시
            if 'notice' in post.get('class', []): 
                continue 
            
            has_normal_post = True
            
            date_tag = post.select_one("td.date")
            if not date_tag: continue
            date_text = date_tag.text.strip()
            
            # 시간 형식(예: 06:55)이면 당일 글, 날짜 형식(예: 26.07.14)이면 지난 글
            if ":" in date_text:
                author_tag = post.select_one("td.name a")
                if not author_tag: continue
                
                author_nick = author_tag.text.strip()
                author_id = extract_user_id(author_tag.get('onclick', ''))
                
                if author_id:
                    if author_id not in user_post_counts:
                        user_post_counts[author_id] = {"nick": author_nick, "id": author_id, "count": 0}
                    user_post_counts[author_id]["count"] += 1
            else:
                # ':'가 없는 행이 나왔다는 것은 전날 글로 넘어갔다는 의미
                # 이후 리스트는 볼 필요가 없으므로 루프 완전 탈출
                stop_scraping = True
                break
                
        # 한 페이지 전체가 공지사항이거나 글이 아예 없을 경우 대비
        if not has_normal_post:
            break
            
        # 다음 페이지로
        if not stop_scraping:
            page += 1
            # 서버 부하 방지를 위해 페이지 간 짧은 대기
            time.sleep(0.5) 
            
    # 스캔 종료 후 집계 (작성글 수 기준 내림차순 정렬)
    sorted_users = sorted(user_post_counts.values(), key=lambda x: x["count"], reverse=True)
    
    # JSON 파일 포맷 조립
    dashboard_data = {
        "updated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "rankings": {
            "posts": sorted_users,
            "given_good": [] # 이벤트용에서는 사용 안함
        }
    }
    
    # data.json 덮어쓰기
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(dashboard_data, f, ensure_ascii=False, indent=2)
        
    top_score = sorted_users[0]['count'] if sorted_users else 0
    print(f"✅ 스캔 완료: 총 {len(sorted_users)}명의 유저가 오늘 글을 작성했습니다. (최고 달성: {top_score}개)\n" + "-"*50)

if __name__ == "__main__":
    # GitHub Actions 환경인지 확인
    if os.environ.get("GITHUB_ACTIONS"):
        print("☁️ GitHub Actions 환경 감지: 1회 스캔을 진행하고 종료합니다.")
        run_event_crawler()
    else:
        print("💻 로컬 환경 감지: 15초 주기로 무한 루프 스캔을 시작합니다...")
        while True:
            run_event_crawler()
            time.sleep(15)