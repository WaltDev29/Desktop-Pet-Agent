# MCP Tool 기능 테스트케이스 명세서

- **최종 수정일**: 2026-05-19
- **대상 브랜치**: `test/mcp`
- **대상 파일**: `D:\Desktop-Pet-Agent\agent\agent_server\mcp_client.py`
- **제외 대상**: `desktop-pet-tools`
- **테스트 웹**: `D:\Desktop-Pet-Agent\test\index.html` 또는 터미널 직접 호출
- **테스트 계정**
  - workspace-mcp: `aiswlv1@gmail.com`
  - windows-mcp : `kimheamin0603@gmail.com`
  - email-mcp : `heamin0603@naver.com`
- **테스트 방식**: LangChain `MultiServerMCPClient`로 등록 MCP tool을 직접 호출. 생성, 발송, 삭제, 키보드/마우스 조작처럼 상태를 바꾸는 tool은 테스트 파일/웹 범위에서 실제 실행.

---

## 전체 요약

| 항목 | 값 |
|---|---:|
| 총 tool 수 | 109 |
| PASS | 109 |
| FAIL | 0 |
| BLOCKED | 0 |

---

## 잔여 이슈

없음

## 잔여 상태 변경 리소스

**Gmail**
`MCP_RETEST_20260519_150318_GMAIL_ATTACH` 실제 메일 생성, 라벨 생성/적용/삭제 및 첨부 다운로드 확인.

**email-mcp**
`MCP_RETEST_EMAIL_20260519_162840` 메일을 실제 발송하고 INBOX UID `11878`로 본문 조회/첨부 다운로드를 확인한 뒤 `delete_emails`로 삭제했다. 첨부 다운로드 파일은 `C:\Users\AISW-509-IP\AppData\Local\Temp\MCP_RETEST_EMAIL_20260519_162840_downloaded.txt`에 생성되었다.

**Calendar**
`MCP_SPEC_20260519_140606_CALENDAR` 보조 캘린더가 생성된 상태로 잔여. `create_calendar`에 삭제 tool이 없어 수동 정리.

**Drive / Docs / Sheets**
재테스트 리소스(`MCP_RETEST_20260519_150318*`, `MCP_RETRY_20260519_150801*`)는 `update_drive_file(trashed=true)`로 휴지통 처리 완료.
제공된 스프레드시트 `1AVEmQPWMYFCIKC12Y4PnUxjPRaGtq27UPkzx_0qfzgk`의 structured table `test1`에는 `append_table_rows` 재테스트 행 `codex-retest-20260519_162931`이 실제 추가되었다.

**Notion**
재테스트로 생성한 리소스가 남아 있다.
- page: `365ff20f-f621-81e3-b075-c96742dc0584`
- duplicate page: `365ff20f-f621-81c1-b984-ff8610f2edeb`
- database: `40ad81a5e330465e8f936867fb4be233`
- data source: `1be6d496-0760-491b-a0bf-41288a61119a`
- view: `365ff20f-f621-81b1-9930-000ca032bb29`

---

## v1 — tool 단위 개별 테스트 (완료)

### windows-mcp

**App** — PASS
- **프롬프트**: `App` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `App(mode=launch, name=cmd)`
- **결과**: `Launching Cmd sent, but window not detected yet.`

**PowerShell** — PASS
- **프롬프트**: `PowerShell` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `PowerShell(command="New-Item -ItemType Directory -Force -Path ... | Out-Null; Get-Date -Format o")`
- **결과**: `2026-05-19T13:58:09.8458514+09:00 / Status Code: 0`

**FileSystem** — PASS
- **프롬프트**: `FileSystem` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `FileSystem(mode=write, path=...\\a.txt, content="MCP_SPEC_LINE1\nMCP_SPEC_LINE2")`
- **결과**: `Written to ...\\a.txt (30 bytes)`

**Snapshot** — PASS
- **프롬프트**: `Snapshot` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `Snapshot()`
- **결과**: 커서 위치, 활성 데스크탑, 열린 창 목록 정상 반환

**Screenshot** — PASS
- **프롬프트**: `Screenshot` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `Screenshot()`
- **결과**: 해상도(5760×2160) + PNG base64 이미지 정상 반환

**Click** — PASS
- **프롬프트**: `Click` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `Click(button=left, clicks=1, loc=[180,180])`
- **결과**: `Single left clicked at (180,180).`

**Type** — PASS
- **프롬프트**: `Type` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `Type(loc=[180,180], text="MCP Windows typing test", press_enter=true)`
- **결과**: `Typed MCP Windows typing test at (180,180).`

**Scroll** — PASS
- **프롬프트**: `Scroll` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `Scroll(direction=down, loc=[300,250], wheel_times=1)`
- **결과**: `Scrolled vertical down by 1 wheel times at (300,250).`

**Move** — PASS
- **프롬프트**: `Move` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `Move(loc=[350,260])`
- **결과**: `Moved the mouse pointer to (350,260).`

**Shortcut** — PASS
- **프롬프트**: `Shortcut` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `Shortcut(shortcut=ctrl+v)`
- **결과**: `Pressed ctrl+v.`

**Wait** — PASS
- **프롬프트**: `Wait` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `Wait(duration=1)`
- **결과**: `Waited for 1 seconds.`

**Scrape** — PASS
- **프롬프트**: `Scrape` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `Scrape(url=https://example.com, query="page title", use_sampling=false)`
- **결과**: `Example Domain` 페이지 콘텐츠 정상 반환

**MultiSelect** — PASS
- **프롬프트**: `MultiSelect` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `MultiSelect(locs=[[180,180],[220,180]], press_ctrl=false)`
- **결과**: `Multi-selected elements at: (180,180) (220,180)`

**MultiEdit** — PASS
- **프롬프트**: `MultiEdit` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `MultiEdit(locs=[[180,180,"multi edit 1"],[180,220,"multi edit 2"]])`
- **결과**: 두 좌표에 각각 텍스트 입력 성공

**Clipboard** — PASS
- **프롬프트**: `Clipboard` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `Clipboard(mode=set, text="MCP_CLIPBOARD_TEST")`
- **결과**: `Clipboard set to: MCP_CLIPBOARD_TEST`

**Process** — PASS
- **프롬프트**: `Process` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `Process(mode=list, name=notepad, limit=5)`
- **결과**: `No processes found matching notepad.`

**Notification** — PASS
- **프롬프트**: `Notification` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `Notification(title="MCP Spec Test", message="windows-mcp notification retry", app_id="Windows PowerShell")`
- **결과**: `Notification sent: "MCP Spec Test" - windows-mcp notification retry`

**Registry** — PASS
- **프롬프트**: `Registry` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `Registry(mode=set, path=HKCU:\\Software\\MCP_SPEC_TEST_20260519_135802, name=Sample, type=String, value=Value1)`
- **결과**: `Registry value [...] "Sample" set to "Value1" (type: String).`

---

### workspace-mcp

**start_google_auth** — PASS
- **프롬프트**: `start_google_auth` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `start_google_auth(service_name=gmail, user_google_email=aiswlv1@gmail.com)`
- **결과**: Google OAuth 인증 URL 정상 반환

**search_gmail_messages** — PASS
- **프롬프트**: `search_gmail_messages` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `search_gmail_messages(query=subject:MCP_RETEST_20260519_150318_GMAIL_ATTACH, page_size=5)`
- **결과**: 메시지 ID `19e3ed4ff169c2c0` 포함 1건 반환

**get_gmail_message_content** — PASS
- **프롬프트**: `get_gmail_message_content` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `get_gmail_message_content(message_id=19e3ea0e9042f3f0)`
- **결과**: 제목, 발신자, 본문, 첨부 목록 정상 반환

**get_gmail_messages_content_batch** — PASS
- **프롬프트**: `get_gmail_messages_content_batch` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `get_gmail_messages_content_batch(message_ids=["19e3ea0e9042f3f0"])`
- **결과**: 1건 배치 조회 정상 반환

**get_gmail_attachment_content** — PASS
- **프롬프트**: `get_gmail_attachment_content` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `get_gmail_attachment_content(message_id=19e3ed4ff169c2c0, attachment_id=..., return_base64=false)`
- **결과**: `retest_attach.txt` (17 bytes) 로컬 저장 성공

**send_gmail_message** — PASS
- **프롬프트**: `send_gmail_message` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `send_gmail_message(to=aiswlv1@gmail.com, subject=MCP_SPEC_20260519_140606_GMAIL_SEND, body=..., attachments=[{filename=mcp_spec_attachment.txt, mime_type=text/plain}])`
- **결과**: `Email sent with 1 attachment(s)! Message ID: 19e3ea0e9042f3f0`

**draft_gmail_message** — PASS
- **프롬프트**: `draft_gmail_message` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `draft_gmail_message(to=aiswlv1@gmail.com, subject=MCP_SPEC_20260519_140606_GMAIL_DRAFT, body="workspace-mcp draft test")`
- **결과**: `Draft created! Draft ID: r-8317581307406074482`

**get_gmail_thread_content** — PASS
- **프롬프트**: `get_gmail_thread_content` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `get_gmail_thread_content(thread_id=19e3ea0e9042f3f0)`
- **결과**: 스레드 내 메시지 1건 + 첨부 목록 정상 반환

**get_gmail_threads_content_batch** — PASS
- **프롬프트**: `get_gmail_threads_content_batch` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `get_gmail_threads_content_batch(thread_ids=["19e3ea0e9042f3f0"])`
- **결과**: 1건 배치 조회 정상 반환

**list_gmail_labels** — PASS
- **프롬프트**: `list_gmail_labels` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `list_gmail_labels(user_google_email=aiswlv1@gmail.com)`
- **결과**: 시스템 라벨 14건 반환

**manage_gmail_label** — PASS
- **프롬프트**: `manage_gmail_label` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `manage_gmail_label(action=create, name=MCP_SPEC_20260519_140606_LABEL, label_list_visibility=labelShow, message_list_visibility=show)`
- **결과**: `Label created successfully! ID: Label_1`

**list_gmail_filters** — PASS
- **프롬프트**: `list_gmail_filters` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `list_gmail_filters(user_google_email=aiswlv1@gmail.com)`
- **결과**: `No filters found.`

**manage_gmail_filter** — PASS
- **프롬프트**: `manage_gmail_filter` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `manage_gmail_filter(action=create, criteria={from=aiswlv1@gmail.com, subject=MCP_SPEC_20260519_140606}, filter_action={addLabelIds=[STARRED]})`
- **결과**: `Filter created successfully! Filter ID: ANe1Bmie8FE6dNZGA2S7SQxWSeHjnMcIH1sqVQ`

**modify_gmail_message_labels** — PASS
- **프롬프트**: `modify_gmail_message_labels` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `modify_gmail_message_labels(message_id=19e3ea0e9042f3f0, add_label_ids=[STARRED], remove_label_ids=[])`
- **결과**: `Message labels updated successfully!`

**batch_modify_gmail_message_labels** — PASS
- **프롬프트**: `batch_modify_gmail_message_labels` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `batch_modify_gmail_message_labels(message_ids=["19e3ed4ff169c2c0"], add_label_ids=[Label_2], remove_label_ids=[])`
- **결과**: `Labels updated for 1 messages: Added labels: Label_2`

**list_calendars** — PASS
- **프롬프트**: `list_calendars` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `list_calendars(user_google_email=aiswlv1@gmail.com)`
- **결과**: 기본 캘린더 `aiswlv1@gmail.com` 1건 반환

**get_events** — PASS
- **프롬프트**: `get_events` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `get_events(calendar_id=primary, time_min=2026-05-20T00:00:00+09:00, time_max=2026-05-21T00:00:00+09:00, max_results=10)`
- **결과**: `MCP_SPEC_20260519_140606_EVENT` 1건 반환

**manage_event** — PASS
- **프롬프트**: `manage_event` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `manage_event(action=create, summary=MCP_SPEC_20260519_140606_EVENT, start_time=2026-05-20T09:00:00+09:00, end_time=2026-05-20T09:30:00+09:00, timezone=Asia/Seoul, description="mcp spec event")`
- **결과**: 이벤트 생성 성공 + 링크 반환

**manage_out_of_office** — PASS
- **프롬프트**: `manage_out_of_office` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `manage_out_of_office(action=list, time_min=2026-05-20T00:00:00+09:00, time_max=2026-05-21T00:00:00+09:00, max_results=5)`
- **결과**: `No out-of-office events found.`

**manage_focus_time** — PASS
- **프롬프트**: `manage_focus_time` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `manage_focus_time(action=list, time_min=2026-05-20T00:00:00+09:00, time_max=2026-05-21T00:00:00+09:00, max_results=5)`
- **결과**: `No Focus Time events found.`

**query_freebusy** — PASS
- **프롬프트**: `query_freebusy` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `query_freebusy(calendar_ids=[primary], time_min=2026-05-20T00:00:00+09:00, time_max=2026-05-21T00:00:00+09:00)`
- **결과**: 바쁜 시간대 1건(00:00~00:30 UTC) 반환

**create_calendar** — PASS
- **프롬프트**: `create_calendar` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `create_calendar(summary=MCP_SPEC_20260519_140606_CALENDAR, description="mcp spec temp calendar", timezone=Asia/Seoul)`
- **결과**: 캘린더 생성 성공 (ID: `75e4c836...@group.calendar.google.com`)

**search_drive_files** — PASS
- **프롬프트**: `search_drive_files` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `search_drive_files(query=MCP_SPEC_20260519_140606, page_size=10)`
- **결과**: 파일 1건 + 폴더 1건 반환

**get_drive_file_content** — PASS
- **프롬프트**: `get_drive_file_content` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `get_drive_file_content(file_id=1Yp88-me_NU0z_f9kYcpRAPcoJR33qOJE)`
- **결과**: `drive file content` 본문 정상 반환

**get_drive_file_download_url** — PASS
- **프롬프트**: `get_drive_file_download_url` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `get_drive_file_download_url(file_id=1Yp88-me_NU0z_f9kYcpRAPcoJR33qOJE)`
- **결과**: 로컬 경로에 18 bytes 파일 저장 성공

**list_drive_items** — PASS
- **프롬프트**: `list_drive_items` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `list_drive_items(folder_id=root, page_size=10)`
- **결과**: `No items found in folder 'root'.`

**create_drive_folder** — PASS
- **프롬프트**: `create_drive_folder` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `create_drive_folder(folder_name=MCP_SPEC_20260519_140606_FOLDER)`
- **결과**: 폴더 생성 성공 (ID: `1wIrUcUsGic_4iFXl3yw8jUDXjZYY6Y9q`)

**create_drive_file** — PASS
- **프롬프트**: `create_drive_file` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `create_drive_file(file_name=MCP_SPEC_20260519_140606_FILE.txt, content="drive file content", folder_id=1wIrUcUsGic_4iFXl3yw8jUDXjZYY6Y9q, mime_type=text/plain)`
- **결과**: 파일 생성 성공 (ID: `1Yp88-me_NU0z_f9kYcpRAPcoJR33qOJE`)

**import_to_google_doc** — PASS
- **프롬프트**: `import_to_google_doc` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `import_to_google_doc(file_name=MCP_RETEST_20260519_150318_IMPORT.md, content="# Retest Import\nImported markdown body", source_format=md, folder_id=...)`
- **결과**: Google Doc 생성 성공 (ID: `1PudBSp4VMht57zMsk0-iFOXsAKs3fU3jMb0u3yWgnhI`)

**get_drive_file_permissions** — PASS
- **프롬프트**: `get_drive_file_permissions` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `get_drive_file_permissions(file_id=1Yp88-me_NU0z_f9kYcpRAPcoJR33qOJE)`
- **결과**: 소유자 1명(`aiswlv1@gmail.com`), 비공개 상태 반환

**check_drive_file_public_access** — PASS
- **프롬프트**: `check_drive_file_public_access` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `check_drive_file_public_access(file_name=MCP_RETEST_20260519_150318_PUBLIC.txt)`
- **결과**: `NO PUBLIC ACCESS` 상태 정상 반환

**update_drive_file** — PASS
- **프롬프트**: `update_drive_file` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `update_drive_file(file_id=1Yp88-me_NU0z_f9kYcpRAPcoJR33qOJE, name=MCP_SPEC_20260519_140606_FILE_UPDATED.txt, description="updated by mcp spec", starred=false)`
- **결과**: 파일명 및 설명 변경 성공

**get_drive_shareable_link** — PASS
- **프롬프트**: `get_drive_shareable_link` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `get_drive_shareable_link(file_id=1Yp88-me_NU0z_f9kYcpRAPcoJR33qOJE)`
- **결과**: View / Download 링크 반환

**manage_drive_access** — PASS
- **프롬프트**: `manage_drive_access` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `manage_drive_access(action=grant, file_id=..., role=reader, share_type=user, share_with=aiswlv1@gmail.com, send_notification=false)`
- **결과**: 공유 권한 부여 성공

**copy_drive_file** — PASS
- **프롬프트**: `copy_drive_file` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `copy_drive_file(file_id=1Yp88-me_NU0z_f9kYcpRAPcoJR33qOJE, new_name=MCP_SPEC_20260519_140606_COPY.txt, parent_folder_id=1wIrUcUsGic_4iFXl3yw8jUDXjZYY6Y9q)`
- **결과**: 복사 성공 (새 ID: `1jHbH6fjIR1p3YRf6TA2Jd6K56uUopmjp`)

**set_drive_file_permissions** — PASS
- **프롬프트**: `set_drive_file_permissions` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `set_drive_file_permissions(file_id=1Yp88-me_NU0z_f9kYcpRAPcoJR33qOJE, link_sharing=reader, writers_can_share=false)`
- **결과**: 링크 공유 활성화, 편집자 공유 제한 적용 성공

**search_docs** — PASS
- **프롬프트**: `search_docs` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `search_docs(query=MCP_SPEC_20260519_140606, page_size=10)`
- **결과**: `No Google Docs found matching '...'`

**get_doc_content** — PASS
- **프롬프트**: `get_doc_content` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `get_doc_content(document_id=1FOpZifEJXaXXgBYxp8g_tTVWodUFKmuXagZdr4WpDXA)`
- **결과**: Tab 1 내 본문(`Alpha line`, `Beta line`) 정상 반환

**list_docs_in_folder** — PASS
- **프롬프트**: `list_docs_in_folder` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `list_docs_in_folder(folder_id=root, page_size=10)`
- **결과**: `No Google Docs found in folder 'root'.`

**create_doc** — PASS
- **프롬프트**: `create_doc` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `create_doc(title=MCP_RETEST_20260519_150318_DOC, content="Alpha line\nBeta line\n")`
- **결과**: Doc 생성 성공 (ID: `1FOpZifEJXaXXgBYxp8g_tTVWodUFKmuXagZdr4WpDXA`)

**modify_doc_text** — PASS
- **프롬프트**: `modify_doc_text` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `modify_doc_text(document_id=..., start_index=0, text="Inserted text\n")`
- **결과**: index 0에 14자 삽입 성공

**find_and_replace_doc** — PASS
- **프롬프트**: `find_and_replace_doc` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `find_and_replace_doc(document_id=..., find_text=Alpha, replace_text=Gamma)`
- **결과**: 1건 교체 성공

**insert_doc_elements** — PASS
- **프롬프트**: `insert_doc_elements` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `insert_doc_elements(document_id=..., element_type=list, list_type=UNORDERED, text="item one\nitem two", index=1)`
- **결과**: 비순서 목록 삽입 성공

**insert_doc_image** — PASS
- **프롬프트**: `insert_doc_image` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `insert_doc_image(document_id=..., image_source=https://www.gstatic.com/images/branding/product/1x/docs_2020q4_48dp.png, width=48, height=48, index=1)`
- **결과**: 48×48 URL 이미지 삽입 성공

**update_doc_headers_footers** — PASS
- **프롬프트**: `update_doc_headers_footers` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `update_doc_headers_footers(document_id=..., section_type=header, content="Retest Header")`
- **결과**: 헤더 업데이트 성공

**batch_update_doc** — PASS
- **프롬프트**: `batch_update_doc` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `batch_update_doc(document_id=..., operations=[{type=insert_text, text="Batch append\n", end_of_segment=true}])`
- **결과**: 1개 operation 실행, 문서 길이 50자 확인

**inspect_doc_structure** — PASS
- **프롬프트**: `inspect_doc_structure` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `inspect_doc_structure(document_id=...)`
- **결과**: 구조 정보 JSON 반환 (Tab 1 확인)

**debug_docs_runtime_info** — PASS
- **프롬프트**: `debug_docs_runtime_info` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `debug_docs_runtime_info(user_google_email=aiswlv1@gmail.com)`
- **결과**: runtime canary, 설치 파일 경로 정보 반환

**create_table_with_data** — PASS (응답 문구 개선 권장)
- **프롬프트**: `create_table_with_data` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `create_table_with_data(document_id=..., table_data=[["H1","H2"],["A","B"]], bold_headers=true, index=1)`
- **결과**: 응답에 `ERROR: Could not find table after creation` 문구 포함됐으나 후속 `debug_table_structure`에서 2×2 표 생성 확인됨. 기능은 정상 동작하나 응답 문구 정합성은 별도 개선 권장.

**debug_table_structure** — PASS
- **프롬프트**: `debug_table_structure` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `debug_table_structure(document_id=..., table_index=0)`
- **결과**: 2×2 테이블 구조(범위, 셀 삽입 인덱스 등) 정상 반환

**export_doc_to_pdf** — PASS
- **프롬프트**: `export_doc_to_pdf` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `export_doc_to_pdf(document_id=..., folder_id=1cam39nFcAwOTuP399DbOA9gJZmOrJfKe, pdf_filename=MCP_RETEST_20260519_150318_DOC.pdf)`
- **결과**: 26,542 bytes PDF Drive 저장 성공

**update_paragraph_style** — PASS
- **프롬프트**: `update_paragraph_style` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `update_paragraph_style(document_id=..., start_index=1, end_index=5, alignment=CENTER)`
- **결과**: 단락 정렬 적용 성공

**get_doc_as_markdown** — PASS
- **프롬프트**: `get_doc_as_markdown` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `get_doc_as_markdown(document_id=...)`
- **결과**: 이미지, 표, 목록, 본문 포함 Markdown 반환

**manage_doc_tab** — PASS
- **프롬프트**: `manage_doc_tab` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `manage_doc_tab(action=create, document_id=..., title="Retest Tab", index=1)`
- **결과**: Tab ID `t.skv3l6jqds6a` 생성 성공

**list_document_comments** — PASS
- **프롬프트**: `list_document_comments` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `list_document_comments(document_id=...)`
- **결과**: `No comments found.`

**manage_document_comment** — PASS
- **프롬프트**: `manage_document_comment` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `manage_document_comment(action=create, document_id=..., comment_content="Retest doc comment")`
- **결과**: Comment ID `AAAB5jJohRM` 생성 성공

**list_spreadsheets** — PASS
- **프롬프트**: `list_spreadsheets` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `list_spreadsheets(max_results=10)`
- **결과**: `No spreadsheets found.`

**get_spreadsheet_info** — PASS
- **프롬프트**: `get_spreadsheet_info` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `get_spreadsheet_info(spreadsheet_id=1RYL2H71e3rYio-Sp6QGaDfS5LMSh0PB-bb50cEsDLTk)`
- **결과**: 시트 1개(`Data`), 1000×26, 조건부 포맷 0건 반환

**read_sheet_values** — PASS
- **프롬프트**: `read_sheet_values` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `read_sheet_values(spreadsheet_id=1RYL2H71e3rYio-Sp6QGaDfS5LMSh0PB-bb50cEsDLTk, range_name=Data!A1:C3)`
- **결과**: 3행(헤더 + 2행 데이터) 정상 반환

**modify_sheet_values** — PASS
- **프롬프트**: `modify_sheet_values` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `modify_sheet_values(spreadsheet_id=1yPnf_sVAiznTn-bdZavJ3HhXVVDvkc8_ioFKl8kkx2o, range_name=Data!A1:B2, values=[["Name","Value"],["alpha","1"]])`
- **결과**: 4셀 업데이트 성공

**format_sheet_range** — PASS
- **프롬프트**: `format_sheet_range` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `format_sheet_range(spreadsheet_id=..., range_name=Data!A1:C1, background_color=#ddeeff, bold=true)`
- **결과**: 배경색 및 볼드 적용 성공

**manage_conditional_formatting** — PASS
- **프롬프트**: `manage_conditional_formatting` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `manage_conditional_formatting(action=add, spreadsheet_id=..., sheet_name=Data, range_name=Data!B2:B3, condition_type=NUMBER_GREATER, condition_values=["1"], background_color=#ffeeaa)`
- **결과**: 조건부 포맷 1건 추가 성공

**create_spreadsheet** — PASS
- **프롬프트**: `create_spreadsheet` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `create_spreadsheet(title=MCP_RETRY_20260519_150801_SHEET, sheet_names=[Data])`
- **결과**: 스프레드시트 생성 성공 (ID: `1yPnf_sVAiznTn-bdZavJ3HhXVVDvkc8_ioFKl8kkx2o`)

**create_sheet** — PASS
- **프롬프트**: `create_sheet` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `create_sheet(spreadsheet_id=1RYL2H71e3rYio-Sp6QGaDfS5LMSh0PB-bb50cEsDLTk, sheet_name=Extra)`
- **결과**: 시트 `Extra` (ID: 675080046) 생성 성공

**list_sheet_tables** — PASS
- **프롬프트**: `list_sheet_tables` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `list_sheet_tables(spreadsheet_id=1RYL2H71e3rYio-Sp6QGaDfS5LMSh0PB-bb50cEsDLTk)`
- **결과**: `No structured tables found.`

**append_table_rows** — PASS
- **프롬프트**: `append_table_rows` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `list_sheet_tables(user_google_email=aiswlv1@gmail.com, spreadsheet_id=1AVEmQPWMYFCIKC12Y4PnUxjPRaGtq27UPkzx_0qfzgk)` → `append_table_rows(user_google_email=aiswlv1@gmail.com, spreadsheet_id=1AVEmQPWMYFCIKC12Y4PnUxjPRaGtq27UPkzx_0qfzgk, table_id=2069954450, values=[[codex-retest-20260519_162931, PASS, append_table_rows, actual state change]])`
- **결과**: `list_sheet_tables`에서 structured table 1개(`Name: tset1`, `Table ID: 2069954450`, Sheet: `시트1`) 확인. `append_table_rows`가 `Successfully appended 1 row(s) to table '2069954450'` 응답을 반환했고 실제 상태 변경을 수행했다.

**resize_sheet_dimensions** — PASS
- **프롬프트**: `resize_sheet_dimensions` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `resize_sheet_dimensions(spreadsheet_id=1yPnf_sVAiznTn-bdZavJ3HhXVVDvkc8_ioFKl8kkx2o, sheet_name=Data, auto_resize_columns=[A,B], frozen_row_count=1)`
- **결과**: 열 자동 조정 및 1행 고정 적용 성공

**move_sheet_rows** — PASS
- **프롬프트**: `move_sheet_rows` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `move_sheet_rows(spreadsheet_id=..., source_sheet=Data, destination_sheet=Extra, start_row=2, end_row=3)`
- **결과**: 2행 이동 성공

**list_spreadsheet_comments** — PASS
- **프롬프트**: `list_spreadsheet_comments` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `list_spreadsheet_comments(spreadsheet_id=1RYL2H71e3rYio-Sp6QGaDfS5LMSh0PB-bb50cEsDLTk)`
- **결과**: `No comments found.`

**manage_spreadsheet_comment** — PASS
- **프롬프트**: `manage_spreadsheet_comment` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `manage_spreadsheet_comment(action=create, spreadsheet_id=..., comment_content="Retest sheet comment")`
- **결과**: Comment ID `AAAB6m4k_Mc` 생성 성공

---

### email-mcp

**list_available_accounts** — PASS
- **프롬프트**: `list_available_accounts` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `list_available_accounts()`
- **결과**: 
```
account_name : default
full_name    : 김해민
incoming     : imap.naver.com:993 (SSL)
outgoing     : smtp.naver.com:587
```
`heamin0603@naver.com` 계정 정보 정상 반환

**add_email_account** — PASS
- **프롬프트**: `add_email_account` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `add_email_account({account_name=MCP_SPEC_20260519_141121_INVALID, email_address=invalid@example.com, full_name="MCP Invalid", incoming={host=imap.invalid.local, port=993, use_ssl=true}, outgoing={host=smtp.invalid.local, port=465, use_ssl=true}})`
- **결과**: `Successfully added email account 'MCP_SPEC_20260519_141121_INVALID'`

**list_emails_metadata** — PASS
- **프롬프트**: `list_emails_metadata` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `list_emails_metadata(account_name=heamin0603@naver.com, mailbox=INBOX, page=1, page_size=10, subject=MCP_RETEST_20260519_150906)`
- **결과**: 검색 결과 0건 (발송된 메일 없어 정상)

**get_emails_content** — PASS
- **프롬프트**: `get_emails_content` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `get_emails_content(account_name=heamin0603@naver.com, email_ids=["11878"], mailbox=INBOX)`
- **결과**: Subject `MCP_RETEST_EMAIL_20260519_162840`, sender/recipient `heamin0603@naver.com`, body `email-mcp retest body 20260519_162840`, attachment `MCP_RETEST_EMAIL_20260519_162840_attach.txt` 조회 성공.

**send_email** — PASS
- **프롬프트**: `send_email` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `send_email(account_name=heamin0603@naver.com, recipients=[heamin0603@naver.com], subject=MCP_RETEST_EMAIL_20260519_162840, body="email-mcp retest body 20260519_162840", attachments=[C:\Users\AISW-509-IP\AppData\Local\Temp\MCP_RETEST_EMAIL_20260519_162840_attach.txt], html=false)`
- **결과**: `Email sent successfully to heamin0603@naver.com with 1 attachment(s)`. `list_available_accounts`에서 outgoing 설정 `port=587`, `use_ssl=false`, `start_ssl=true` 확인.

**delete_emails** — PASS
- **프롬프트**: `delete_emails` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `delete_emails(account_name=heamin0603@naver.com, email_ids=["11878"], mailbox=INBOX)`
- **결과**: `Successfully deleted 1 email(s)`. 실제 수신 테스트 메일을 삭제했다.

**download_attachment** — PASS
- **프롬프트**: `download_attachment` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `download_attachment(account_name=heamin0603@naver.com, email_id="11878", mailbox=INBOX, attachment_name=MCP_RETEST_EMAIL_20260519_162840_attach.txt, save_path=C:\Users\AISW-509-IP\AppData\Local\Temp\MCP_RETEST_EMAIL_20260519_162840_downloaded.txt)`
- **결과**: 첨부 파일 저장 성공. `mime_type=application/plain`, `size=49`, 저장 경로 `C:\Users\AISW-509-IP\AppData\Local\Temp\MCP_RETEST_EMAIL_20260519_162840_downloaded.txt`.

---

### notion-mcp

**notion-search** — PASS
- **프롬프트**: `notion-search` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `notion-search(query=MCP_SPEC, query_type=internal, page_size=5, filters={})`
- **결과**: 관련 페이지 3건 반환

**notion-fetch** — PASS
- **프롬프트**: `notion-fetch` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `notion-fetch(id=1be6d496-0760-491b-a0bf-41288a61119a)`
- **결과**: `MCP_RETEST_20260519_151031_DB` 데이터소스 스키마 정상 반환

**notion-create-pages** — PASS
- **프롬프트**: `notion-create-pages` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `notion-create-pages(pages=[{properties={title=MCP_RETEST_20260519_151031_PAGE}, content="# Retest Page\nInitial content"}])`
- **결과**: 페이지 생성 성공 (ID: `365ff20f-f621-81e3-b075-c96742dc0584`)

**notion-update-page** — PASS
- **프롬프트**: `notion-update-page` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `notion-update-page(page_id=365ff20f-f621-81e3-b075-c96742dc0584, command=insert_content, content="\nInserted by retest", position={type:end}, properties={}, content_updates=[])`
- **결과**: 페이지 하단에 내용 삽입 성공

**notion-move-pages** — PASS
- **프롬프트**: `notion-move-pages` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `notion-move-pages(page_or_database_ids=[365ff20f-f621-81c1-b984-ff8610f2edeb], new_parent={type:workspace})`
- **결과**: `1 item was already in the target location` (이미 workspace에 위치, 정상)

**notion-duplicate-page** — PASS
- **프롬프트**: `notion-duplicate-page` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `notion-duplicate-page(page_id=365ff20f-f621-81e3-b075-c96742dc0584)`
- **결과**: 복제 성공 (새 ID: `365ff20f-f621-81c1-b984-ff8610f2edeb`)

**notion-create-database** — PASS
- **프롬프트**: `notion-create-database` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `notion-create-database(parent={type=page_id, page_id=365ff20f-f621-81e3-b075-c96742dc0584}, title=MCP_RETEST_20260519_151031_DB, schema="CREATE TABLE Tasks (Name TITLE, Status SELECT, Score NUMBER);")`
- **결과**: DB 생성 성공 (ID: `40ad81a5e330465e8f936867fb4be233`)

**notion-update-data-source** — PASS
- **프롬프트**: `notion-update-data-source` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `notion-update-data-source(data_source_id=1be6d496-0760-491b-a0bf-41288a61119a, description="Retest data source description")`
- **결과**: 데이터소스 설명 업데이트 성공

**notion-create-comment** — PASS
- **프롬프트**: `notion-create-comment` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `notion-create-comment(page_id=365ff20f-f621-81e3-b075-c96742dc0584, rich_text=[{type=text, text={content="Retest comment"}}])`
- **결과**: 댓글 생성 성공 (ID: `365ff20f-f621-81f6-a50c-001ddcc8c2bf`)

**notion-get-comments** — PASS
- **프롬프트**: `notion-get-comments` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `notion-get-comments(page_id=365ff20f-f621-81e3-b075-c96742dc0584, include_all_blocks=true)`
- **결과**: 댓글 1건 포함 discussion 정상 반환

**notion-get-teams** — PASS
- **프롬프트**: `notion-get-teams` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `notion-get-teams()`
- **결과**: `김해민님의 워크스페이스 HQ` (owner 역할) 반환

**notion-get-users** — PASS
- **프롬프트**: `notion-get-users` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `notion-get-users()`
- **결과**: bot 1건 + person 1건(`kimheamin0603@gmail.com`) 반환

**notion-create-view** — PASS
- **프롬프트**: `notion-create-view` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `notion-create-view(database_id=40ad81a5e330465e8f936867fb4be233, data_source_id=1be6d496-0760-491b-a0bf-41288a61119a, name=MCP_RETRY_VIEW_20260519_151142, type=table)`
- **결과**: 뷰 생성 성공 (ID: `365ff20f-f621-81b1-9930-000ca032bb29`)

**notion-update-view** — PASS
- **프롬프트**: `notion-update-view` 도구를 실제 MCP 호출로 실행하고 응답 또는 오류를 확인한다.
- **호출**: `notion-update-view(view_id=365ff20f-f621-81b1-9930-000ca032bb29, name=MCP_RETRY_VIEW_20260519_151142_UPDATED)`
- **결과**: 뷰 이름 변경 성공

---

