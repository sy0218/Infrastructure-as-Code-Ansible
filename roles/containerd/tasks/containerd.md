# 📦 containerd 설치 및 설정 (Ansible)
- K8s 컨테이너 런타임인 containerd를 **인벤토리 `containerd_version`으로 버전 고정** 설치하고
`SystemdCgroup = true`를 적용한다.
- cgroup v2 환경에서 kubelet(systemd 드라이버)과 cgroup 관리 주체를 일치시키기 위함
— 불일치 시 파드 재시작 반복 등 불안정 발생.
- **인벤토리 `containerd_insecure_registries`** 목록의 HTTP 사설 레지스트리(Harbor 등)에
`certs.d/hosts.toml`로 HTTP 접속을 허용한다.
- 설치 후 hold로 고정하며, 설정(config.toml/hosts.toml)이 실제로 변경된 경우에만 containerd를 재시작한다.
---
<br>

## 🧩 main.yml
```yaml
# -----------------------------------------------------
# containerd 설치 및 설정 (K8s 컨테이너 런타임)
# -----------------------------------------------------
# SystemdCgroup = true 필수 — cgroup v2 환경에서 kubelet(systemd 드라이버)과
# cgroup 관리 주체를 일치시킴 (불일치 시 파드 재시작 반복 등 불안정)
# -----------------------------------------------------

# 1. containerd 설치 — 인벤토리 containerd_version으로 버전 고정
#    (버전 변경 시 hold 상태여도 해당 버전으로 수렴)
- name: "Install containerd"
  apt:
    name: "containerd={{ containerd_version }}"
    state: present # 없으면 설치
    update_cache: yes # apt update 먼저 실행
    cache_valid_time: 3600 # 캐시가 1시간 이내면 update 생략 (매 실행 시간 절약)
    allow_change_held_packages: true # hold 상태에서도 버전 변경 허용
    allow_downgrade: true # 하위 버전으로 고정 시 다운그레이드 허용

# 2. 버전 고정 — 의도치 않은 업그레이드 방지
#    (dpkg_selections 자체가 멱등 — command apt-mark hold는 매번 changed)
- name: "Hold containerd package"
  dpkg_selections:
    name: containerd
    selection: hold

# 3. 설정 디렉토리 생성 (file 모듈 자체가 멱등)
- name: "Create containerd config directory"
  file:
    path: /etc/containerd
    state: directory
    owner: root
    group: root
    mode: "0755"

# 4. 기본 설정 생성 (조회 전용 → 상태 변경 없음)
- name: "Get containerd default config"
  command: containerd config default
  register: containerd_default
  changed_when: false

# 5. SystemdCgroup 활성화 + certs.d 경로 지정해서 설정 파일 배포
#    - config_path 기본값은 빈 문자열 → 지정 없이는 certs.d의 hosts.toml을 읽지 않음
#    (파이프+sed는 비멱등이라 금지 — copy는 내용이 같으면 changed=0 보장)
- name: "Apply containerd config"
  copy:
    content: "{{ containerd_default.stdout | replace('SystemdCgroup = false', 'SystemdCgroup = true') | replace('config_path = \"\"', 'config_path = \"/etc/containerd/certs.d\"') }}\n"
    dest: /etc/containerd/config.toml
    owner: root
    group: root
    mode: "0644"
  register: containerd_config

# 6. 서비스 기동 + 부팅 자동시작 (systemd 모듈 자체가 멱등)
- name: "Enable and start containerd"
  systemd:
    name: containerd
    enabled: true
    state: started

# 7. 레지스트리별 접속 규칙 디렉토리 — 디렉토리 이름이 곧 레지스트리 주소(host:port)
- name: "Create certs.d registry directories"
  file:
    path: "/etc/containerd/certs.d/{{ item }}"
    state: directory
    owner: root
    group: root
    mode: "0755"
  loop: "{{ containerd_insecure_registries }}"

# 8. hosts.toml 배포 — 스킴을 http로 선언해 HTTPS 시도 자체를 차단
#    (TLS 없는 사설 레지스트리 pull 시 "server gave HTTP response to HTTPS client" 방지)
- name: "Apply insecure registry hosts.toml"
  copy:
    content: |
      server = "http://{{ item }}"

      [host."http://{{ item }}"]
        capabilities = ["pull", "resolve"]
    dest: "/etc/containerd/certs.d/{{ item }}/hosts.toml"
    owner: root
    group: root
    mode: "0644"
  loop: "{{ containerd_insecure_registries }}"
  register: registry_hosts

# 9. 설정이 변경된 경우만 재시작 (매 실행 재시작 방지 — config.toml/hosts.toml 반영에는 재시작 필수)
- name: "Restart containerd on config change"
  systemd:
    name: containerd
    state: restarted
  when: containerd_config.changed or registry_hosts.changed

# -----------------------------------------------------
# 검증
# -----------------------------------------------------
- name: "Check containerd status"
  command: systemctl is-active containerd
  register: containerd_status
  failed_when: false
  changed_when: false

# 설치된 버전 확인
- name: "Check installed containerd version"
  command: dpkg-query -W --showformat=${Version} containerd
  register: containerd_pkg_version
  changed_when: false

# hold 상태 확인
- name: "Check held packages"
  command: apt-mark showhold
  register: held_containerd
  changed_when: false

# 설정 파일에 SystemdCgroup = true 반영 확인 (grep 미일치 시 rc=1 → 실패 처리 안 함)
- name: "Check SystemdCgroup in config"
  command: grep -c "SystemdCgroup = true" /etc/containerd/config.toml
  register: systemd_cgroup_check
  failed_when: false
  changed_when: false

# 설정 파일에 certs.d 경로 반영 확인
- name: "Check certs.d config_path in config"
  command: grep -c 'config_path = "/etc/containerd/certs.d"' /etc/containerd/config.toml
  register: config_path_check
  failed_when: false
  changed_when: false

# 레지스트리별 hosts.toml에 http 스킴 선언 확인
- name: "Check insecure registry hosts.toml"
  command: grep -c 'server = "http://{{ item }}"' /etc/containerd/certs.d/{{ item }}/hosts.toml
  register: registry_hosts_check
  failed_when: false
  changed_when: false
  loop: "{{ containerd_insecure_registries }}"

- name: "Assert containerd active, version pinned and held"
  assert:
    that:
      - containerd_status.stdout == "active"
      - containerd_pkg_version.stdout == containerd_version # 고정 버전 일치 (조건문 안에서는 {{ }} 금지)
      - '"containerd" in held_containerd.stdout_lines'
      - systemd_cgroup_check.stdout | int >= 1
      - config_path_check.stdout | int >= 1
    success_msg: "Good!.. | containerd {{ containerd_pkg_version.stdout }} active & held (SystemdCgroup = true, certs.d enabled)"
    fail_msg: "ERROR!.. | containerd inactive, version mismatch or NOT held"

- name: "Assert insecure registry hosts.toml applied"
  assert:
    that:
      - item.stdout | int >= 1
    success_msg: "Good!.. | insecure registry applied: {{ item.item }}"
    fail_msg: "ERROR!.. | insecure registry NOT applied: {{ item.item }}"
  loop: "{{ registry_hosts_check.results }}"
  loop_control:
    label: "{{ item.item }}"
```
---
<br>

## 🛠 작업 내용
### 1️⃣ containerd 설치 — 버전 고정 (멱등성 핵심)
- `containerd={{ containerd_version }}` 형식으로 인벤토리에 명시한 버전만 설치
- `allow_change_held_packages` + `allow_downgrade` → 버전 변수 변경 시 hold 상태여도 해당 버전으로 수렴
- 설치 후 `dpkg_selections`로 hold — 의도치 않은 업그레이드 방지
---
### 2️⃣ 설정 파일 생성 — SystemdCgroup 활성화 + certs.d 경로 지정
- `containerd config default` 출력을 `register`로 받아(`changed_when: false`)
`replace` 필터로 `SystemdCgroup = true` 치환 후 `copy`로 배포
- `config_path = "/etc/containerd/certs.d"`도 함께 치환 — 지정 없이는 hosts.toml을 읽지 않음
- 파이프+sed 방식은 비멱등이라 금지 — copy는 내용 동일 시 **changed=0** 보장
---
### 3️⃣ HTTP 사설 레지스트리 허용 — certs.d/hosts.toml
- 인벤토리 `containerd_insecure_registries` 목록으로 레지스트리별
`/etc/containerd/certs.d/<host:port>/hosts.toml` 배포
- `server = "http://..."`로 스킴을 박아 HTTPS 시도 자체를 차단
— TLS 없는 레지스트리 pull 시 `server gave HTTP response to HTTPS client` 방지
---
### 4️⃣ 서비스 기동 + 조건부 재시작
- `systemd` 모듈로 기동/자동시작 등록, 설정(config.toml/hosts.toml)이 **변경된 경우에만** 재시작
---
### 5️⃣ 검증
- 서비스 active + **설치 버전 = 고정 버전** + hold 상태 + `SystemdCgroup = true`
+ certs.d `config_path` + 레지스트리별 hosts.toml 존재를 `assert`로 검증
---
<br>

## ✅ 실행 결과 예시
```bash
TASK [Assert containerd active, version pinned and held]
ok: [ap] => {
    "msg": "Good!.. | containerd 1.7.12-0ubuntu4 active & held (SystemdCgroup = true, certs.d enabled)"
}

TASK [Assert insecure registry hosts.toml applied]
ok: [ap] => (item=192.168.56.200:30002) => {
    "msg": "Good!.. | insecure registry applied: 192.168.56.200:30002"
}
```
---
