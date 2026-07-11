# 🎛 K8s 컨트롤플레인 초기화 + Calico 설치 (Ansible)
- kubeadm init으로 컨트롤플레인을 초기화하고 Calico(Tigera Operator)를 설치한다.
- **스왑을 끄지 않는 구성**: `failSwapOn: false` + `swapBehavior`(인벤토리 `kubernetes_swap_behavior`)를
KubeletConfiguration으로 적용 — 클러스터 ConfigMap으로 저장되어 join하는 워커에도 자동 적용된다.
- kubeadm init은 **1회성 부트스트랩** — `creates` 게이팅으로 재실행 시 스킵.
init 이후 `pod_subnet` 등 변수 변경은 재실행으로 반영되지 않는다 (k8s_reset 후 재구축 필요).
- kubectl 사용 계정은 인벤토리 `kubernetes_admin_user`로 관리한다.
---
<br>

## 🧩 templates
### kubeadm-config.yaml.j2
- `advertiseAddress: {{ ansible_host }}` — host-only IP로 API 서버 광고
- `kubernetesVersion` — `kubernetes_package_version`에서 추출 (버전 고정 일관성)
- `podSubnet: {{ pod_subnet }}` + KubeletConfiguration(failSwapOn/swapBehavior)

### calico-install.yaml.j2
- `linuxDataplane: Iptables` 명시, `cidr: {{ pod_subnet }}` (podSubnet과 일치)
- `nodeAddressAutodetectionV4.cidrs: [{{ node_cidr }}]` — host-only NIC 자동감지
---
<br>

## 🛠 작업 내용
### 1️⃣ kubeadm init — 부트스트랩 게이팅 (멱등성 핵심)
- 설정은 `template`으로 배포 후 `--config`로 init (플래그 나열 대신 선언적 관리)
- `creates: /etc/kubernetes/admin.conf` → 이미 init된 노드는 **스킵** 보장
- `--ignore-preflight-errors=Swap`은 사전 검사 통과용 — 실제 스왑 동작은 KubeletConfiguration이 담당
---
### 2️⃣ kubectl 계정 설정
- `getent passwd`로 `kubernetes_admin_user`의 홈 디렉토리 조회 (하드코딩 없음, 계정 없으면 즉시 실패)
- `.kube/config`에 admin.conf 복사 + 소유권 부여 (file/copy 멱등)
---
### 3️⃣ Calico 설치 — 사전 체크 게이팅 + server-side apply
- Operator 매니페스트는 `get_url` 다운로드 (파일명에 버전 포함 → 버전 변경 시에만 재다운로드)
- **둘 다 존재 확인으로 게이팅** (diff 게이팅 불가): Operator는 대상 네임스페이스가 없으면
`kubectl diff`가 rc=2 에러, Installation CR은 적용 후 operator가 spec 기본값을 채우며
필드 소유권을 가져가 server-side diff가 Conflict(rc=2) 발생
→ 존재 확인(rc=0/1) 후 **미설치일 때만** apply → 재실행 시 **changed=0**
- 설정 변경(pod_subnet 등) 반영은 재실행이 아닌 재구축 영역 (k8s_reset 후 재실행)
- **server-side apply 필수**: `create`는 재실행 실패, client-side apply는 CRD가 커서 annotation 한도 초과
- Operator 적용 직후 CRD 등록 대기(`kubectl wait --for condition=established`) 후 Installation CR 적용
---
### 4️⃣ 검증
- 마스터 노드 `Ready` 대기 — control-plane 라벨 조회 + `until`/`retries` (최대 5분)
- INTERNAL-IP == `ansible_host` 확인 (NAT IP 오인 검출), `swapon`으로 스왑 활성 유지 확인
- 하나라도 실패 시 `assert`로 플레이북 중단
---
<br>

## ✅ 실행 결과 예시
```bash
TASK [Assert control plane ready with swap on]
ok: [ap] => {
    "msg": "Good!.. | Control plane Ready (192.168.56.200, swap on)"
}
```
---
