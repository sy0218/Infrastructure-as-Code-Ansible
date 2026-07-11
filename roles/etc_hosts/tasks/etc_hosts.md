# 🗂 /etc/hosts 생성 및 관리 (Ansible)
- 서버 초기 세팅 시 **/etc/hosts 파일을 인벤토리 기준으로 자동 생성**
- 기존 `/etc/hosts` 파일을 **전체 덮어쓰기**하여 서버 간 호스트명 통일
---
<br>

## 🧩 main.yml
```yaml
# -----------------------------------------------------
# /etc/hosts 생성 (인벤토리 기반 전체 관리)
# -----------------------------------------------------

# 1. /etc/hosts 생성 (copy: content 자체가 멱등 — 내용이 같으면 changed=0)
- name: "Create /etc/hosts from inventory"
  copy:
    dest: /etc/hosts
    owner: root
    group: root
    mode: '0644'
    content: |
      127.0.0.1   localhost
      ::1         localhost

      {% for host in groups['Ubuntu_Servers'] %}
      {{ hostvars[host]['ansible_host'] }} {{ host }}
      {% endfor %}

# -----------------------------------------------------
# /etc/hosts 설정 검증 (타겟 서버 파일에서 서버별 항목 확인)
# -----------------------------------------------------
- name: "Check /etc/hosts entries"
  command: "grep -F '{{ hostvars[item].ansible_host }} {{ item }}' /etc/hosts"
  loop: "{{ groups['Ubuntu_Servers'] }}"
  register: hosts_check
  changed_when: false
  failed_when: false

- name: "Assert /etc/hosts entries present"
  assert:
    that:
      - item.rc == 0
    success_msg: "Good!.. | /etc/hosts entry present: {{ item.item }}"
    fail_msg: "ERROR!.. | /etc/hosts entry missing: {{ item.item }}"
  loop: "{{ hosts_check.results }}"
```
---
<br>

## 🛠 작업 내용
### 1️⃣ /etc/hosts 파일 생성 (멱등성 핵심)
- `copy: content`로 파일 전체를 선언형 관리 — 내용이 같으면 재실행 시 **changed=0** 보장
- localhost, IPv6 localhost 기본 항목 포함, 소유자 root / 권한 0644
---
### 2️⃣ 인벤토리 기반 호스트 등록
- 인벤토리 그룹 Ubuntu_Servers 기준
- 각 서버의 ansible_host(IP)와 호스트명을 매핑하여 자동 추가
- 모든 서버에서 동일한 /etc/hosts 파일 유지
---
### 3️⃣ /etc/hosts 검증
- 타겟 서버 파일에서 서버별 `IP 호스트명` 항목을 `grep -F`로 확인 후 `assert`
- 누락 항목을 서버별로 식별 가능
---
<br>

## ✅ 실행 결과 예시
```bash
TASK [Assert /etc/hosts entries present]
ok: [192.168.56.60] => (item=...) => {
    "msg": "Good!.. | /etc/hosts entry present: ap"
}
```
---
