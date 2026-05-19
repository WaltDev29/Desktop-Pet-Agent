# config.json 작성 가이드

최신 develop 기준 MCP 설정은 `agent/agent_server/config.json`의 `mcpServers`만 사용합니다.
`config.default.json`을 복사해 `config.json`으로 만들고, 사용할 MCP 서버를 `mcpServers` 아래에 추가하세요.

`config.json`은 개인 계정, 앱 비밀번호, OAuth client secret 등을 포함하므로 git에 커밋하지 않습니다.

## 기본 구조

```json
{
  "mcpServers": {
    "server-name": {
      "command": "uvx",
      "args": ["package-name", "stdio"],
      "transport": "stdio",
      "env": {}
    }
  }
}
```

`command`가 `"python"`이면 에이전트가 실행 중인 Python 인터프리터로 자동 보정됩니다. 그 외에는 `uvx`, 실행 파일 경로, 또는 설치된 명령 이름을 그대로 사용합니다.

## windows-mcp

```json
{
  "mcpServers": {
    "windows-mcp": {
      "command": "uvx",
      "args": ["windows-mcp"],
      "transport": "stdio",
      "env": {
        "WINDOWS_MCP_SCREENSHOT_SCALE": "0.5",
        "WINDOWS_MCP_SCREENSHOT_BACKEND": "auto",
        "WINDOWS_MCP_PROFILE_SNAPSHOT": "false",
        "ANONYMIZED_TELEMETRY": "true",
        "WINDOWS_MCP_DEBUG": "false"
      }
    }
  }
}
```

## workspace-mcp

```json
{
  "mcpServers": {
    "workspace-mcp": {
      "command": "uvx",
      "args": [
        "workspace-mcp",
        "--tools",
        "gmail",
        "calendar",
        "drive",
        "docs",
        "sheets"
      ],
      "transport": "stdio",
      "env": {
        "GOOGLE_OAUTH_CLIENT_ID": "google-oauth-client-id",
        "GOOGLE_OAUTH_CLIENT_SECRET": "google-oauth-client-secret",
        "USER_GOOGLE_EMAIL": "your-email@gmail.com",
        "OAUTHLIB_INSECURE_TRANSPORT": "1",
        "PORT": "8003",
        "WORKSPACE_MCP_PORT": "8003",
        "GOOGLE_OAUTH_REDIRECT_URI": "http://localhost:8003/oauth2callback"
      }
    }
  }
}
```

테스트할 Google 계정은 Google Cloud Console의 OAuth 동의 화면 대상 탭에 테스트 사용자로 등록되어 있어야 합니다.

## email-mcp

일반 SSL 465 예시:

```json
{
  "mcpServers": {
    "zerolib-email": {
      "command": "uvx",
      "args": ["mcp-email-server@latest", "stdio"],
      "transport": "stdio",
      "env": {
        "MCP_EMAIL_SERVER_ACCOUNT_NAME": "account-name",
        "MCP_EMAIL_SERVER_FULL_NAME": "full-name",
        "MCP_EMAIL_SERVER_EMAIL_ADDRESS": "your-email@example.com",
        "MCP_EMAIL_SERVER_USER_NAME": "your-email@example.com",
        "MCP_EMAIL_SERVER_PASSWORD": "app-password",
        "MCP_EMAIL_SERVER_IMAP_HOST": "imap.domain.com",
        "MCP_EMAIL_SERVER_IMAP_PORT": "993",
        "MCP_EMAIL_SERVER_SMTP_HOST": "smtp.domain.com",
        "MCP_EMAIL_SERVER_SMTP_PORT": "465",
        "MCP_EMAIL_SERVER_SMTP_SSL": "true",
        "MCP_EMAIL_SERVER_SMTP_START_SSL": "false",
        "MCP_EMAIL_SERVER_ENABLE_ATTACHMENT_DOWNLOAD": "false"
      }
    }
  }
}
```

Naver STARTTLS 587 예시:

```json
{
  "mcpServers": {
    "zerolib-email-naver": {
      "command": "uvx",
      "args": ["mcp-email-server@latest", "stdio"],
      "transport": "stdio",
      "env": {
        "MCP_EMAIL_SERVER_ACCOUNT_NAME": "your-id@naver.com",
        "MCP_EMAIL_SERVER_FULL_NAME": "full-name",
        "MCP_EMAIL_SERVER_EMAIL_ADDRESS": "your-id@naver.com",
        "MCP_EMAIL_SERVER_USER_NAME": "your-id@naver.com",
        "MCP_EMAIL_SERVER_PASSWORD": "naver-app-password",
        "MCP_EMAIL_SERVER_IMAP_HOST": "imap.naver.com",
        "MCP_EMAIL_SERVER_IMAP_PORT": "993",
        "MCP_EMAIL_SERVER_SMTP_HOST": "smtp.naver.com",
        "MCP_EMAIL_SERVER_SMTP_PORT": "587",
        "MCP_EMAIL_SERVER_SMTP_SSL": "false",
        "MCP_EMAIL_SERVER_SMTP_START_SSL": "true",
        "MCP_EMAIL_SERVER_ENABLE_ATTACHMENT_DOWNLOAD": "true"
      }
    }
  }
}
```

## Notion 등 기타 MCP

최신 구조에서는 Notion도 별도 코드 경로가 아니라 `mcpServers`에 서버 실행 방식과 인증 환경값을 직접 넣어 추가합니다. 서버 패키지가 요구하는 `command`, `args`, `env`를 그대로 작성하면 통합 `general_mcp_worker`가 다른 MCP와 함께 관리합니다.
