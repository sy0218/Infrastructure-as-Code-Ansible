# ☸️ K8s 패키지 설치 — kubeadm / kubelet / kubectl (Ansible)
- pkgs.k8s.io 공식 저장소를 등록하고 kubeadm / kubelet / kubectl을
**인벤토리 `kubernetes_package_version`으로 버전 고정** 설치한다.
- 설치 후 hold로 고정해 의도치 않은 업그레이드로 클러스터가 깨지는 것을 방지한다.
- kubelet `--node-ip`를 인벤토리 `ansible_host`(host-only IP)로 고정해
VirtualBox NAT IP(10.0.2.15) 오인 사고를 방지한다.
- 저장소 마이너 버전은 `kubernetes_version`, 패키지 버전은 `kubernetes_package_version`으로 관리한다.
---
<br>

## 🧩 main.yml
```yaml
# -----------------------------------------------------
# K8s 패키지 설치 — kubeadm / kubelet / kubectl
# -----------------------------------------------------
# pkgs.k8s.io 저장소 등록 → 설치 → 버전 고정(hold)
# node-ip 고정: VirtualBox NAT IP(10.0.2.15)를 노드 IP로 오인하는 사고 방지
# -----------------------------------------------------

# 1. deb822_repository 모듈 의존성 설치 (apt 모듈 자체가 멱등)
#    (다른 플레이북에 기대지 않고 롤이 자기 의존성을 직접 보장)
- name: "Install python3-debian"
  apt:
    name: python3-debian
    state: present
    update_cache: yes # apt update 먼저 실행
    cache_valid_time: 3600 # 캐시가 1시간 이내면 update 생략 (매 실행 시간 절약)

# 2. K8s apt 저장소 등록 — 키 다운로드/변환 + 저장소 등록을 한 태스크로 처리
#    (deb822_repository 모듈 자체가 멱등 — gpg --dearmor 수동 실행은 비멱등이라 금지)
- name: "Add kubernetes apt repository"
  deb822_repository:
    name: kubernetes
    uris: "https://pkgs.k8s.io/core:/stable:/v{{ kubernetes_version }}/deb/"
    suites: /
    signed_by: "https://pkgs.k8s.io/core:/stable:/v{{ kubernetes_version }}/deb/Release.key"
  register: k8s_repo

# 3. 저장소가 새로 등록/변경된 경우만 apt 캐시 갱신
- name: "Update apt cache"
  apt:
    update_cache: yes
  when: k8s_repo.changed

# 4. K8s 패키지 설치 — 인벤토리 kubernetes_package_version으로 버전 고정 (apt 모듈 자체가 멱등)
#    (버전 변경 시 hold 상태여도 해당 버전으로 수렴)
#    (CDN 연결 불안정 대비 재시도 — 이미 받은 .deb는 apt 캐시에 남아 실패분만 다시 받음)
- name: "Install kubernetes packages"
  apt:
    name:
      - "kubelet={{ kubernetes_package_version }}"
      - "kubeadm={{ kubernetes_package_version }}"
      - "kubectl={{ kubernetes_package_version }}"
    state: present
    allow_change_held_packages: true # hold 상태에서도 버전 변경 허용
    allow_downgrade: true # 하위 버전으로 고정 시 다운그레이드 허용
  register: k8s_install
  retries: 3 # 실패 시 재시도 횟수
  delay: 10 # 재시도 간격(초)
  until: k8s_install is succeeded

# 5. 버전 고정 — 의도치 않은 업그레이드로 클러스터 깨짐 방지
#    (dpkg_selections 자체가 멱등 — command apt-mark hold는 매번 changed)
- name: "Hold kubernetes packages"
  dpkg_selections:
    name: "{{ item }}"
    selection: hold
  loop:
    - kubelet
    - kubeadm
    - kubectl

# 6. kubelet node-ip 고정 (copy 자체가 멱등) — 인벤토리 ansible_host(host-only IP) 사용
- name: "Set kubelet node-ip"
  copy:
    content: "KUBELET_EXTRA_ARGS=--node-ip={{ ansible_host }}\n"
    dest: /etc/default/kubelet
    owner: root
    group: root
    mode: "0644"
  register: kubelet_env

# 7. node-ip 설정이 변경된 경우만 kubelet 재시작
#    (init/join 전에는 kubelet이 설정 대기 상태라 재시작해도 무해)
- name: "Restart kubelet on node-ip change"
  systemd:
    name: kubelet
    state: restarted
  when: kubelet_env.changed

# -----------------------------------------------------
# 검증
# -----------------------------------------------------
- name: "Check kubeadm version"
  command: kubeadm version -o short
  register: kubeadm_version_check
  changed_when: false

- name: "Check held packages"
  command: apt-mark showhold
  register: held_k8s_packages
  changed_when: false

- name: "Assert kubernetes packages installed and held"
  assert:
    that:
      - kubeadm_version_check.stdout == "v" ~ kubernetes_package_version.split("-")[0] # 고정 버전 일치 (조건문 안에서는 {{ }} 금지)
      - item in held_k8s_packages.stdout_lines # 라인 단위 정확 일치
    success_msg: "Good!.. | {{ item }} installed & held ({{ kubeadm_version_check.stdout }})"
    fail_msg: "ERROR!.. | {{ item }} NOT held or version mismatch"
  loop:
    - kubelet
    - kubeadm
    - kubectl
```
---
<br>

## 🛠 작업 내용
### 1️⃣ 모듈 의존성 설치 + 저장소 등록 (멱등성 핵심)
- `deb822_repository` 모듈이 요구하는 `python3-debian`을 롤이 직접 설치 — 다른 플레이북 의존 제거
- GPG 키 + 저장소를 `deb822_repository` 한 태스크로 등록 (수동 `gpg --dearmor`는 비멱등)
- 저장소가 **변경된 경우에만** `apt update` 실행
---
### 2️⃣ 패키지 설치 — 버전 고정 + 재시도
- `kubelet={{ kubernetes_package_version }}` 형식으로 인벤토리에 명시한 버전만 설치
- `allow_change_held_packages` + `allow_downgrade` → 버전 변수 변경 시 hold 상태여도 해당 버전으로 수렴
- `retries: 3` + `until` → CDN 연결 일시 장애 시 10초 간격 재시도 (받은 .deb는 apt 캐시 재활용)
- 설치 후 `dpkg_selections`로 hold — hold 상태면 재실행 시 **changed=0** 보장
---
### 3️⃣ kubelet node-ip 고정
- `/etc/default/kubelet`에 `--node-ip={{ ansible_host }}` 설정 (copy 멱등)
- 값이 변경된 경우에만 kubelet 재시작
---
### 4️⃣ 검증
- `kubeadm version`이 **고정 버전(`kubernetes_package_version`)과 정확히 일치**하는지 확인
- `apt-mark showhold`로 3개 패키지 hold 상태를 `assert`로 검증
---
<br>

## ✅ 실행 결과 예시
```bash
TASK [Assert kubernetes packages installed and held]
ok: [ap] => (item=kubelet) => {
    "msg": "Good!.. | kubelet installed & held (v1.34.4)"
}
```
---
