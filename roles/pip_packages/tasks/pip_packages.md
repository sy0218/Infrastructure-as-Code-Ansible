# 🐍 Python 패키지 설치 (Ansible)
- `pip_packages` 변수 기반 Python 패키지 **pip3 설치**
- `pip` 모듈 자체 멱등성 + **사후 검증(assert)** 흐름
---
<br>

## 🧩 main.yml
```yaml
# -----------------------------------------------------
# Python Packages 설치
# -----------------------------------------------------

# 1. Python 패키지 설치 (pip 모듈 자체가 멱등 — 사전 체크 불필요)
- name: "Install Python packages"
  pip:
    name: "{{ pip_packages }}"
    state: present
    executable: pip3
    extra_args: "--break-system-packages" # PEP 668(외부 관리 환경) 차단 우회 — 시스템 전역 설치 허용

# 2. 패키지 설치 검증 (버전 지정자(==) 제거 후 조회)
- name: "Check installed Python packages"
  command: "pip3 show {{ item.split('==')[0] }}"
  loop: "{{ pip_packages }}"
  register: pip_check
  changed_when: false
  failed_when: false

- name: "Assert Python packages installed"
  assert:
    that:
      - item.rc == 0
    fail_msg: "[FAIL] Some Python packages are missing"
    success_msg: "Good!.. | Python packages installed successfully"
  loop: "{{ pip_check.results }}"
```
---
<br>

## 🛠 작업 내용
### 1️⃣ 패키지 설치
- `pip_packages`에 정의된 패키지 설치 (`docker==7.1.0`처럼 버전 고정 가능)
- `pip: state=present`는 모듈 자체가 멱등 → 사전 체크 없이 재실행해도 **changed=0** 보장
- `--break-system-packages`: Ubuntu 24.04+의 PEP 668 정책이 시스템 pip 설치를 차단하므로 우회 필요

예시:
```yaml
# host.yml
pip_packages:
  - docker==7.1.0
```
---
### 2️⃣ 설치 검증
- `pip3 show <package>`로 설치 여부 확인 (버전 지정자 `==`는 제거 후 조회)
- `rc == 0`이면 정상 설치, `assert`를 항목별 loop로 수행해 **누락 패키지 식별 가능**
---
<br>

## ✅ 실행 결과 예시
```bash
TASK [Assert Python packages installed]
ok: [apserver] => (item={...'rc': 0, 'item': 'docker==7.1.0'...}) => {
    "msg": "Good!.. | Python packages installed successfully"
}
```
---
