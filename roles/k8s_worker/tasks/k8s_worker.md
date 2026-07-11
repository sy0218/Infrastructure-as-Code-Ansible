# 🔗 K8s 워커 노드 조인 (Ansible)
- 워커 노드(s1, s2)를 kubeadm join으로 클러스터에 합류시킨다.
- join은 **1회성 부트스트랩** — `/etc/kubernetes/kubelet.conf` 존재 게이팅으로 재실행 시 스킵.
- kubelet 스왑 설정(failSwapOn/swapBehavior)은 클러스터 ConfigMap(kubelet-config)에서
자동 수신되므로 워커에 별도 설정이 없다.
- 마지막에 **전체 클러스터 검증**(노드 수/Ready/INTERNAL-IP/스왑 유지)을 수행한다.
---
<br>

## 🧩 main.yml
```yaml
# -----------------------------------------------------
# K8s 워커 노드 조인 (kubeadm join)
# -----------------------------------------------------
# [주의] join은 1회성 부트스트랩 — kubelet.conf 존재 게이팅으로 재실행 시 스킵
#  - kubelet 스왑 설정(failSwapOn/swapBehavior)은 클러스터 ConfigMap(kubelet-config)
#    에서 자동 수신 — 워커에 별도 설정 없음
#  - 조인 해제/재조인은 k8s_reset으로 해체 후 재실행
# -----------------------------------------------------

# 1. 조인 여부 확인 (stat 자체가 멱등)
- name: "Check kubelet conf"
  stat:
    path: /etc/kubernetes/kubelet.conf
  register: kubelet_conf

# 2. 미조인 워커만 마스터에서 조인 명령 발급
#    (token create는 비멱등 — 필요할 때만 실행하도록 게이팅, 토큰은 TTL 24시간 후 자동 만료)
- name: "Create join command on master"
  command: kubeadm token create --print-join-command
  delegate_to: "{{ groups['kubernetes_master'][0] }}"
  register: join_cmd
  when: not kubelet_conf.stat.exists

# 3. 클러스터 조인 (creates 게이팅 이중 안전장치)
#    (--ignore-preflight-errors=Swap: 사전 검사 통과용 — 스왑 동작은 클러스터 설정이 담당)
- name: "Join cluster"
  command:
    cmd: "{{ join_cmd.stdout }} --ignore-preflight-errors=Swap"
    creates: /etc/kubernetes/kubelet.conf
  when: not kubelet_conf.stat.exists

# -----------------------------------------------------
# 검증 — 전체 클러스터 (워커 CNI 기동까지 수 분 걸릴 수 있어 재시도 대기)
# -----------------------------------------------------
# 스왑 활성 유지 확인 (LimitedSwap 구성 전제 — 워커 각자 확인)
- name: "Check active swap"
  command: swapon --noheadings --show=NAME
  register: worker_swap_check
  changed_when: false

# 전체 노드 Ready 대기 (마스터에서 1회만 조회 — 결과는 모든 워커에 공유됨)
- name: "Wait for all nodes Ready"
  command: kubectl get nodes --no-headers
  delegate_to: "{{ groups['kubernetes_master'][0] }}"
  run_once: true
  register: all_nodes_status
  changed_when: false
  until:
    - all_nodes_status.stdout_lines | length == groups['kubernetes'] | length
    - "'NotReady' not in all_nodes_status.stdout"
  retries: 30 # 최대 5분 대기 (30회 x 10초)
  delay: 10
  environment:
    KUBECONFIG: /etc/kubernetes/admin.conf

# 전체 노드 INTERNAL-IP 조회 (NAT IP(10.0.2.15) 오인 사고 검출용)
- name: "Check node internal IPs"
  command: >-
    kubectl get nodes -o
    'jsonpath={.items[*].status.addresses[?(@.type=="InternalIP")].address}'
  delegate_to: "{{ groups['kubernetes_master'][0] }}"
  run_once: true
  register: node_internal_ips
  changed_when: false
  environment:
    KUBECONFIG: /etc/kubernetes/admin.conf

# 워커별 최종 검증 — 클러스터 노드 수/Ready + 자기 IP 등록 + 스왑 유지
- name: "Assert cluster complete with swap on"
  assert:
    that:
      - all_nodes_status.stdout_lines | length == groups['kubernetes'] | length # 노드 수 일치 (조건문 안에서는 {{ }} 금지)
      - "'NotReady' not in all_nodes_status.stdout" # 전체 노드 Ready
      - ansible_host in node_internal_ips.stdout.split() # 이 워커가 host-only IP로 조인됐는지
      - swap_file_path in worker_swap_check.stdout_lines # 스왑 활성 유지 확인
    success_msg: "Good!.. | Worker joined & cluster {{ all_nodes_status.stdout_lines | length }}/{{ groups['kubernetes'] | length }} nodes Ready ({{ ansible_host }}, swap on)"
    fail_msg: "ERROR!.. | Cluster incomplete, node NOT ready, wrong IP or swap off"
```
---
<br>

## 🛠 작업 내용
### 1️⃣ 조인 게이팅 (멱등성 핵심)
- `stat`으로 `/etc/kubernetes/kubelet.conf` 확인 → 이미 조인된 워커는 이후 작업 전부 스킵
- `creates` 게이팅을 join 명령에도 걸어 이중 안전장치
---
### 2️⃣ 조인 명령 발급 + 조인
- 미조인 워커가 있을 때만 `delegate_to`(마스터)로 `kubeadm token create --print-join-command` 실행
- 토큰은 TTL 24시간 후 자동 만료 — 별도 정리 불필요
- 발급받은 명령에 `--ignore-preflight-errors=Swap`만 추가해 조인
---
### 3️⃣ 전체 클러스터 검증
- 마스터에 delegate + `run_once`로 `kubectl get nodes` 조회 — **노드 수 일치 + 전체 Ready**를
`until`/`retries`로 대기 (최대 5분)
- 워커별로 자기 `ansible_host`가 INTERNAL-IP 목록에 있는지 확인 (NAT IP 오인 검출)
- `swapon`으로 스왑 활성 유지 확인 후 `assert` — 이 롤의 assert가 **클러스터 최종 검증**
---
<br>

## ✅ 실행 결과 예시
```bash
TASK [Assert cluster complete with swap on]
ok: [s1] => changed=false
  msg: Good!.. | Worker joined & cluster 3/3 nodes Ready (192.168.56.201, swap on)
ok: [s2] => changed=false
  msg: Good!.. | Worker joined & cluster 3/3 nodes Ready (192.168.56.202, swap on)
```
---
