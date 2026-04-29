# config.json 작성 가이드

`config.default.json`을 복제해서 `config.json`으로 저장한 뒤 아래 가이드를 참고해 값을 채우세요.
`config.json`은 `.gitignore`에 추가되어 있으므로 git에 커밋되지 않습니다.

> **슬래시 방향 주의** — JSON에서 경로는 `/` 또는 `\\` 사용. `\` 단독 사용 시 파싱 에러 발생.
> 예: `C:\\Users\\...` 또는 `C:/Users/...`

---

## 1. `windows_mcp.python_path`

mcp 환경의 Python 인터프리터 경로입니다.

```bash
# 터미널에서
conda activate mcp
where python
```

```
출력 예시: C:\Users\본인계정\anaconda3\envs\mcp\python.exe
```

```json
"python_path": "C:/Users/본인계정/anaconda3/envs/mcp/python.exe"
```

---

## 2. `workspace_mcp.exe_path`

workspace-mcp 실행 파일 경로입니다.

```bash
conda activate mcp
pip install workspace-mcp   # 미설치 시
where workspace-mcp
```

```
출력 예시: C:\Users\본인계정\anaconda3\envs\mcp\Scripts\workspace-mcp.exe
```

```json
"exe_path": "C:/Users/본인계정/anaconda3/envs/mcp/Scripts/workspace-mcp.exe"
```

### `workspace_mcp.tools` — 사용할 서비스 선택

필요한 것만 골라서 넣으세요. 많을수록 LLM 컨텍스트 부담이 커집니다.

| 값           | 서비스             |
| ------------ | ------------------ |
| `gmail`    | Gmail              |
| `calendar` | Google Calendar    |
| `drive`    | Google Drive       |
| `docs`     | Google Docs        |
| `sheets`   | Google Sheets      |
| `tasks`    | Google Tasks       |
| `chat`     | Google Chat        |
| `contacts` | Google Contacts    |
| `slides`   | Google Slides      |
| `forms`    | Google Forms       |
| `script`   | Google Apps Script |
| `search`   | Google Search      |

```json
"tools": ["gmail", "calendar", "drive"]
```

### OAuth 설정 (`.env`에 입력)

```bash
# .env
GOOGLE_OAUTH_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your_client_secret
```

> 발급 하여 공유 드린 내용이니 확인후 ID와 Secret을 입력하세요.
> 각자 첫 실행 시 브라우저에서 본인 Google 계정으로 로그인 1회 필요.
> 개인 토큰은 `~/.workspace-mcp/cli-tokens/`에 자동 저장됩니다. (PC별 분리)

---

## 3. `email_mcp.exe_path`

mcp-email-server 실행 파일 경로입니다.

```bash
conda activate mcp
pip install mcp-email-server   # 미설치 시
where mcp-email-server
```

```
출력 예시: C:\Users\본인계정\anaconda3\envs\mcp\Scripts\mcp-email-server.exe
```

```json
"exe_path": "C:/Users/본인계정/anaconda3/envs/mcp/Scripts/mcp-email-server.exe"
```

### 계정 정보 입력

| 필드              | 설명                                            |
| ----------------- | ----------------------------------------------- |
| `full_name`     | 발신자 이름 — 수신자에게 보이는 이름           |
| `email_address` | 실제 이메일 주소                                |
| `password`      | **앱 비밀번호** (실제 로그인 비밀번호 ❌) |
|`imap_host`,`smtp_port`| 도메인에 naver 혹은 gamil 등 사용 도메인 기입 |

### 앱 비밀번호 발급 방법

**Gmail**

1. Google 계정 → 보안
2. 2단계 인증 활성화 (미설정 시 먼저 설정)
3. 검색창에 "앱 비밀번호" 검색
4. 앱 이름 입력 후 만들기 → 16자리 코드 발급
5. 띄어쓰기 제거 후 입력: `"password": "abcdefghijklmnop"`

**Naver**

1. 네이버 메일 → 환경설정 → POP3/IMAP 설정 → 사용함
2. 보안설정 → 2단계 인증 → 앱 비밀번호 발급

### 주요 메일 서비스 서버 정보

| 서비스   | SMTP 호스트    | SMTP 포트 | IMAP 호스트    | IMAP 포트 |
| -------- | -------------- | --------- | -------------- | --------- |
| Gmail    | smtp.gmail.com | 465       | imap.gmail.com | 993       |
| Naver    | smtp.naver.com | 465       | imap.naver.com | 993       |
| Daum     | smtp.daum.net  | 465       | imap.daum.net  | 993       |
| Exchange | 사내 서버 주소 | 587       | 사내 서버 주소 | 993       |

---

## 4. `notion_mcp`

별도 설치 및 경로 설정이 필요 없습니다. `enabled: true`만 하면 됩니다.

```json
"notion_mcp": {
    "enabled": true
}
```

- 최초 실행 시 브라우저가 열리고 Notion 계정으로 로그인 1회 필요
- 이후 OAuth 토큰은 Notion이 자동 관리 (`config.json`에 저장되지 않음)
