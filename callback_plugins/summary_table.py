# ==================================================
# summary_table — 실행 결과 요약 표 callback 플러그인
# ==================================================
# aggregate 타입 — stdout_callback(yaml)을 대체하지 않고
# 기존 출력을 유지한 채 PLAY RECAP 뒤에 요약 표만 덧붙인다.
# assert 태스크는 SUCCESS/FAILED 대신 PASS/FAIL로 표기해
# '검증 블록으로 끝나는 롤' 하우스 스타일과 맞춘다.
from unicodedata import east_asian_width

from ansible import constants as C
from ansible.plugins.callback import CallbackBase


def _disp_w(text):
    """터미널 표시 폭 — 한글 등 동아시아 전각 문자는 2칸으로 계산한다."""
    return sum(2 if east_asian_width(ch) in 'WF' else 1 for ch in text)


def _pad(text, width):
    """표시 폭 기준 왼쪽 정렬 (str.ljust는 글자 수 기준이라 한글이 밀린다)."""
    return text + ' ' * max(0, width - _disp_w(text))

DOCUMENTATION = '''
    name: summary_table
    type: aggregate
    short_description: 롤/태스크/호스트별 실행 결과 요약 표
    description:
      - 플레이북 종료 시 롤·태스크별 결과 표, 호스트별 통계, 총계를 출력한다.
      - assert 태스크는 PASS/FAIL, 일반 태스크는 SUCCESS/FAILED로 표기한다.
    author: Infrastructure-as-Code-Ansible
'''


class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'aggregate'
    CALLBACK_NAME = 'summary_table'

    # 상태별 출력 색 (파이프로 내보내면 Ansible이 색을 자동 제거)
    _COLORS = {
        'SUCCESS': C.COLOR_OK, 'PASS': C.COLOR_OK,
        'FAILED': C.COLOR_ERROR, 'FAIL': C.COLOR_ERROR,
        'UNREACHABLE': C.COLOR_UNREACHABLE,
        'SKIPPED': C.COLOR_SKIP, 'IGNORED': C.COLOR_WARN,
        'RESCUED': C.COLOR_WARN,
    }

    def __init__(self):
        super().__init__()
        self._tasks = {}   # task_uuid → {'role', 'task', 'is_assert', 'hosts': {host: 상태}}
        self._order = []   # 실행 순서 보존용 task_uuid 목록

    # ---------- 결과 수집 ----------
    def _record(self, result, status):
        task = result._task
        uuid = task._uuid
        if uuid not in self._tasks:
            role = task._role.get_name() if task._role else '-'
            name = task.get_name()
            # 롤 소속 태스크는 이름이 "롤명 : 태스크명"이라 롤 컬럼과 중복 — 접두어 제거
            prefix = '%s : ' % role
            if name.startswith(prefix):
                name = name[len(prefix):]
            self._order.append(uuid)
            self._tasks[uuid] = {
                'role': role,
                'task': name,
                'is_assert': task.action.rsplit('.', 1)[-1] == 'assert',
                'hosts': {},
            }
        self._tasks[uuid]['hosts'][result._host.get_name()] = status

    def v2_runner_on_ok(self, result):
        self._record(result, 'ok')

    def v2_runner_on_failed(self, result, ignore_errors=False):
        self._record(result, 'ignored' if ignore_errors else 'failed')

    def v2_runner_on_skipped(self, result):
        self._record(result, 'skipped')

    def v2_runner_on_unreachable(self, result):
        # ignore_unreachable 태스크는 PLAY RECAP과 동일하게 통과(ignored)로 집계
        ignore = getattr(result._task, 'ignore_unreachable', False)
        self._record(result, 'ignored' if ignore else 'unreachable')

    # ---------- 표기 결정 ----------
    @staticmethod
    def _task_result(entry):
        statuses = set(entry['hosts'].values())
        if 'unreachable' in statuses:
            return 'UNREACHABLE'
        if 'failed' in statuses:
            return 'FAIL' if entry['is_assert'] else 'FAILED'
        if 'rescued' in statuses:
            return 'RESCUED'
        if statuses == {'skipped'}:
            return 'SKIPPED'
        if 'ignored' in statuses:
            return 'IGNORED'
        return 'PASS' if entry['is_assert'] else 'SUCCESS'

    # ---------- 요약 표 출력 ----------
    def v2_playbook_on_stats(self, stats):
        if not self._order:
            return
        entries = [self._tasks[u] for u in self._order]

        # block/rescue 보정: PLAY RECAP 기준 실제 실패(stats.failures)보다 많은
        # 'failed' 기록은 rescue로 구제된 것 — 실행 순서 앞쪽부터 재라벨한다
        # (구제되지 않은 fatal 실패는 해당 호스트의 마지막 failed일 수밖에 없다)
        for host in {h for e in entries for h in e['hosts']}:
            failed_entries = [e for e in entries if e['hosts'].get(host) == 'failed']
            rescued_n = len(failed_entries) - stats.failures.get(host, 0)
            for e in failed_entries[:rescued_n]:
                e['hosts'][host] = 'rescued'
        role_w = max(_disp_w('Role'), max(_disp_w(e['role']) for e in entries))
        task_w = max(_disp_w('Task'), max(_disp_w(e['task']) for e in entries))
        line_w = role_w + task_w + len('UNREACHABLE') + 4
        bar = '=' * line_w
        d = self._display.display

        d('')
        d(bar)
        d(' Ansible Execution Summary')
        d(bar)
        d('')
        d('%s  %s  %s' % (_pad('Role', role_w), _pad('Task', task_w), 'Result'))
        d('-' * line_w)
        prev_role = None
        for e in entries:
            if prev_role is not None and e['role'] != prev_role:
                d('')   # 롤 그룹 사이 빈 줄
            prev_role = e['role']
            res = self._task_result(e)
            d('%s  %s  %s' % (_pad(e['role'], role_w), _pad(e['task'], task_w), res),
              color=self._COLORS.get(res))

        # 호스트별 집계 (ignored는 통과로 계산, skipped는 분모 제외)
        per_host = {}
        for e in entries:
            for host, st in e['hosts'].items():
                c = per_host.setdefault(
                    host, {'ok': 0, 'failed': 0, 'skipped': 0,
                           'unreachable': 0, 'rescued': 0})
                c['ok' if st == 'ignored' else st] += 1

        d('')
        d(bar)
        d('HOST SUMMARY')
        d('')
        host_w = max(_disp_w(h) for h in per_host)
        for host in sorted(per_host):
            c = per_host[host]
            executed = c['ok'] + c['failed'] + c['rescued']
            if c['unreachable']:
                label = 'UNREACHABLE'
            elif c['failed']:
                label = 'FAIL'
            elif executed == 0:
                label = 'SKIPPED'   # 실행 0건 — 통과(PASS)로 오해하지 않게 구분
            else:
                label = 'PASS'
            d('%s : %s (%d/%d)' % (_pad(host, host_w), label, c['ok'], executed),
              color=self._COLORS.get(label))

        # 총계 (호스트 x 태스크 실행 건수 기준)
        passed = sum(c['ok'] for c in per_host.values())
        failed = sum(c['failed'] for c in per_host.values())
        skipped = sum(c['skipped'] for c in per_host.values())
        unreach = sum(c['unreachable'] for c in per_host.values())
        rescued = sum(c['rescued'] for c in per_host.values())
        d('')
        d('TOTAL')
        d('Tasks : %d' % (passed + failed + skipped + unreach + rescued))
        d('Passed: %d' % passed)
        d('Failed: %d' % failed)
        if skipped:
            d('Skipped: %d' % skipped)
        if rescued:
            d('Rescued: %d' % rescued)
        if unreach:
            d('Unreachable: %d' % unreach)
        d(bar)
