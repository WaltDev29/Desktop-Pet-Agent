# config.json 작성 가이드

`config.default.json`을 복제해서 `config.json`으로 저장한 뒤 아래 가이드를 참고해 값을 채우세요.
`config.json`은 개인 환경값과 OAuth 토큰을 포함하므로 git에 커밋하지 않습니다.

> **슬래시 방향 주의**: JSON에서 Windows 경로는 `/` 또는 `\\`를 사용하세요. `\`를 단독으로 쓰면 JSON 파싱 오류가 발생합니다.
> 예: `C:\\Users\\...` 또는 `C:/Users/...`

---

## 1. `windows_mcp.python_path`

`windows-mcp`를 실행할 Python 인터프리터 경로입니다.

```bash
conda activate mcp
where python
```

출력 예시:

```text
C:\Users\본인계정\anaconda3\envs\mcp\python.exe
```

설정 예시:

```json
"python_path": "C:/Users/본인계정/anaconda3/envs/mcp/python.exe"
```

---

## 2. `workspace_mcp`

### `workspace_mcp.exe_path`

`workspace-mcp` 실행 파일 경로입니다.

```bash
conda activate mcp
pip install workspace-mcp
where workspace-mcp
```

출력 예시:

```text
C:\Users\본인계정\anaconda3\envs\mcp\Scripts\workspace-mcp.exe
```

설정 예시:

```json
"exe_path": "C:/Users/본인계정/anaconda3/envs/mcp/Scripts/workspace-mcp.exe"
```

### `workspace_mcp.tools`

필요한 서비스만 선택하세요. 많이 켤수록 tool 수와 LLM 컨텍스트 부담이 커집니다.
만약 실행이 되지 않는다면 aisw 계정 Google Cloud Console에서 해당 도구 API 사용 켜주시기 바랍니다. gamil, calender, drive, docs, sheets 는 허용된 상태입니다. 

| 값 | 서비스 |
|---|---|
| `gmail` | Gmail |
| `calendar` | Google Calendar |
| `drive` | Google Drive |
| `docs` | Google Docs |
| `sheets` | Google Sheets |
| `tasks` | Google Tasks |
| `chat` | Google Chat |
| `contacts` | Google Contacts |
| `slides` | Google Slides |
| `forms` | Google Forms |
| `script` | Google Apps Script |
| `search` | Google Search |

```json
"tools": ["gmail", "calendar", "drive"]
```

### Google OAuth 설정

Google OAuth client id와 secret은 `agent/.env`에 입력합니다. 팀 공통 키이니 확인 후 정확하게 기재 바랍니다.

```bash
GOOGLE_OAUTH_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your_client_secret
```

- 최초 실행 시 브라우저에서 테스트할 Google 계정으로 로그인해야 합니다.
- aisw 계정의 Google Cloud Console의 OAuth 테스트 사용자에 테스트할 계정이 등록되어 있어야 합니다. (그렇게 할 수 없다면 email: aiswlv1@gmail.com / password: @Polytech 계정 사용 바랍니다.)
- 개인 credential은 기본적으로 `C:\Users\<계정>\.google_workspace_mcp\credentials` 아래에 저장됩니다.

---

## 3. `email_mcp`

### `email_mcp.exe_path`

`mcp-email-server` 실행 파일 경로입니다.

```bash
conda activate mcp
pip install mcp-email-server
where mcp-email-server
```

출력 예시:

```text
C:\Users\본인계정\anaconda3\envs\mcp\Scripts\mcp-email-server.exe
```

설정 예시:

```json
"exe_path": "C:/Users/본인계정/anaconda3/envs/mcp/Scripts/mcp-email-server.exe"
```

### 계정 정보

| 필드 | 설명 |
|---|---|
| `account_name` | MCP tool 호출 시 사용하는 계정명입니다. `send_email` 등에서 `account_name`으로 전달합니다. |
| `full_name` | 발신자 이름입니다. 인코딩 문제를 피하려면 ASCII 이름을 권장합니다. |
| `email_address` | 실제 이메일 주소입니다. |
| `password` | 앱 비밀번호입니다. 실제 로그인 비밀번호를 넣지 마세요. |
| `imap_host` | IMAP 서버 호스트입니다. |
| `imap_port` | IMAP 서버 포트입니다. 보통 SSL 993을 사용합니다. |
| `smtp_host` | SMTP 서버 호스트입니다. |
| `smtp_port` | SMTP 서버 포트입니다. SSL 465 또는 STARTTLS 587을 사용합니다. |
| `enable_attachment_download` | 첨부 다운로드 tool 사용 여부입니다. `"true"` 또는 `"false"`로 설정합니다. |

Naver 예시:

```json
"email_mcp": {
  "enabled": true,
  "exe_path": "C:/Users/본인계정/anaconda3/envs/mcp/Scripts/mcp-email-server.exe",
  "account_name": "heamin0603@naver.com",
  "full_name": "kim heamin",
  "email_address": "heamin0603@naver.com",
  "password": "앱_비밀번호",
  "imap_host": "imap.naver.com",
  "imap_port": "993",
  "smtp_host": "smtp.naver.com",
  "smtp_port": "587",
  "enable_attachment_download": "true"
}
```

> `account_name`은 이메일 주소와 같게 맞추는 것을 권장합니다. 그렇지 않으면 tool 호출 시 실제 이메일 주소가 아니라 설정된 계정명을 전달해야 합니다.

### 앱 비밀번호 발급

**Gmail**

1. Google 계정 > 보안으로 이동합니다.
2. 2단계 인증을 활성화합니다.
3. "앱 비밀번호"를 검색합니다.
4. 앱 이름을 입력하고 16자리 앱 비밀번호를 발급합니다.
5. 공백을 제거하고 `password`에 입력합니다.

**Naver**

1. 네이버 메일 > 환경설정 > POP3/IMAP 설정에서 IMAP 사용을 켭니다.
2. 보안설정 > 2단계 인증 > 앱 비밀번호에서 앱 비밀번호를 발급합니다.

### 주요 메일 서비스 서버 정보

| 서비스 | SMTP 호스트 | SMTP 포트 | IMAP 호스트 | IMAP 포트 |
|---|---|---:|---|---:|
| Gmail | smtp.gmail.com | 465 | imap.gmail.com | 993 |
| Naver | smtp.naver.com | 465 또는 587 | imap.naver.com | 993 |
| Daum | smtp.daum.net | 465 | imap.daum.net | 993 |
| Exchange | 조직 서버 주소 | 587 | 조직 서버 주소 | 993 |

---

## 4. `notion_mcp`

Notion MCP는 별도 실행 파일 경로가 필요 없습니다. 아래처럼 활성화만 하면 됩니다.

```json
"notion_mcp": {
  "enabled": true
}
```

- 최초 실행 시 브라우저가 열리고 Notion 계정으로 로그인해야 합니다.
- OAuth access token, refresh token, client id, metadata는 `config.json`의 `notion_oauth` 섹션에 저장됩니다.
- Notion MCP access token은 만료 시간이 짧으므로, 서버 연결 전에 저장된 토큰의 남은 시간이 부족하면 자동 refresh합니다.
- 401 Unauthorized가 발생하면 저장된 access token을 무효화하고 refresh token으로 재발급한 뒤 MCP client/session을 새로 만들어 재시도해야 합니다.
