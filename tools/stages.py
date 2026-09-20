"""Bounded reviewed authoring stages. Exact accepted owner IDs cross stage boundaries."""
from __future__ import annotations
import hashlib
import re
from pathlib import Path

# Quoted application strings (including JavaScript) are never rewritten.
TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|\$[A-Za-z_][A-Za-z0-9_-]*')


def substitute(text: str, identities: dict[str, str]) -> str:
    return TOKEN.sub(lambda m: identities.get(m[0], m[0]) if m[0].startswith('$') else m[0], text)


def type_record(record: str) -> bool:
    return record.startswith(('type.', 'effect.row ')) or record.startswith('effect.requirement parent=@')


def publish(author, revision: str, work: Path, project: Path, run):
    identities: dict[str, str] = {}
    previous_types: list[str] = []
    previous_end = 0
    proofs = []
    current = run('status', project=project)
    observed = re.search(r'^revision id=(rev_[a-f0-9]+)', current, re.MULTILINE)
    if observed is None:
        observed = re.search(r'\b(?:revision|observed)=(rev_[a-f0-9]+)', current)
    observed = observed.group(1) if observed else None
    for ordinal, (name, end) in enumerate(author.stages, 1):
        records = author.records[previous_end:end]
        prefix = f'{ordinal:02d}-{name}'
        request = work / (prefix + '.lkjc')
        body = substitute('\n'.join(previous_types + records), identities)
        candidate = f'request base={revision}\n{body}\n'
        receipt = work / (prefix + '.apply.txt')
        if receipt.exists():
            if not request.exists() or request.read_text() != candidate:
                raise RuntimeError(f'Accepted source prefix changed at {prefix}; build into a fresh project')
            applied = receipt.read_text()
            print(f'AUTHORING stage={prefix} reuse=accepted-prefix', flush=True)
        else:
            if observed is not None and observed != revision:
                raise RuntimeError('Native HEAD differs from the accepted prefix; refuse to resume')
            request.write_text(candidate)
            print(f'AUTHORING stage={prefix} input-bytes={request.stat().st_size}', flush=True)
            plan_path = work / (prefix + '.logical-plan')
            # Preserve a previous rejected/interrupted plan as evidence, not authority.
            if plan_path.exists():
                import time
                plan_path.rename(work / (prefix + f'.interrupted-{time.time_ns()}.logical-plan'))
            planned = run('change', 'plan', '--input-file', str(request), '--output', str(plan_path), project=project)
            (work / (prefix + '.plan.txt')).write_text(planned)
            token = re.search(r'\bplan_[a-f0-9]+\b', planned).group(0)
            applied = run('change', 'apply', '--input-file', str(request), '--plan', token, project=project)
            receipt.write_text(applied)
            observed = None
        match = re.search(r'^revision base=rev_[a-f0-9]+ result=(rev_[a-f0-9]+)', applied, re.MULTILINE)
        if not match:
            raise RuntimeError('Accepted revision is missing from native apply receipt')
        revision = match.group(1)
        package = re.search(r'^project .* package=(pkg_[a-f0-9]+)', applied, re.MULTILINE).group(1)
        for symbol, owner in re.findall(r'^identity symbol=(\$\S+) id=(\S+)', applied, re.MULTILINE):
            identities[symbol] = package + '/' + owner if owner.startswith('req_') else owner
        previous_types.extend(record for record in records if type_record(record))
        previous_end = end
        proofs.append({'stage': name, 'request_sha256': hashlib.sha256(request.read_bytes()).hexdigest(),
                       'accepted_revision': revision, 'request': request.name})
    if previous_end != len(author.records):
        raise RuntimeError('Unpublished records remain after final authoring stage')
    final_status = run('status', project=project)
    if revision not in final_status:
        raise RuntimeError('Final accepted revision does not match native project status')
    return revision, proofs
