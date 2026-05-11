---
name: Git push skill vbhc — auto, không hỏi confirm
description: Khi user nói "đưa lên git" / "push lên git" / "commit và push" cho skill soan-thao-vbhc, tự động làm toàn bộ; không hỏi confirm về repo state, auth, scope
type: feedback
originSessionId: d2678777-08f3-4e95-9a55-7c3501505901
---
**Rule:** Khi user yêu cầu "đưa lên git" (hoặc đồng nghĩa) về project skill `soan-thao-vbhc`, tự động chạy: `git add .` → `git commit -m "..."` → `git push`. KHÔNG hỏi confirm về repo state / auth method / scope như lần đầu.

**Why:** User đã setup xong local repo + remote + Git Credential Manager với account `biencuong` ở session 2026-05-10. Hỏi lại các câu confirm là noise — user chốt rằng bước này phải tối giản để dễ update sau này.

**How to apply:**

- **Working dir**: `D:\SKILL_AI\skills\soan-thao-vbhc\`
- **Remote**: `https://github.com/biencuong/vbhc.git` (origin)
- **Branch**: `main`
- **Auth**: Git Credential Manager browser-based (đã authorize lần đầu, cache token)
- **Identity đã set**: `biencuong` / `thpt.hg@gmail.com`

**Quy trình tự động (3 bước, không hỏi):**

```bash
cd /d/SKILL_AI/skills/soan-thao-vbhc
git add .
git commit -m "<commit message tự generate dựa trên thay đổi trong session>"
git push
```

**Commit message style:**
- 1 dòng tiêu đề ngắn (≤ 70 ký tự, imperative form, tiếng Việt OK)
- Optional: blank line + bullet list các thay đổi cụ thể
- Vd: `Fix nginx reload command for aaPanel + add INSTALL-AAPANEL.md`

**Nếu `git push` fail do auth chưa cache (rare, hệ thống mới):**
- Print lệnh ngắn cho user copy chạy tay (1 dòng `git push` đủ — GCM popup browser tự xử lý)
- KHÔNG hỏi PAT / SSH key

**Trước khi commit, vẫn cần verify nhanh:**
- `git status` để biết những gì sẽ commit (in ra cho user thấy)
- Check không có file nhạy cảm: `htpasswd*`, `.env`, `*.pem`, `*.key`, `cong-viec/` (đã có trong `.gitignore`, nhưng kiểm tra `git status` lại)
- Nếu thấy file đáng ngờ → DỪNG, hỏi user

**KHÔNG áp dụng rule này cho repo khác** (chỉ cho `biencuong/vbhc` của skill `soan-thao-vbhc`). Repo khác user chưa cho phép tự động.
