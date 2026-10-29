#!/usr/bin/env python3
"""release-publisher - releasing from the dashboard (TagPulse migrations 187-190). ONE program, two homes.

WHY (2026-10-28, case staged-release-1028; plan Docs/60-Updates/RELEASE_FROM_DASHBOARD_PLAN_2026-10-28.md): the owner
wants to prepare and sign a release on the signing PC and do everything else from the dashboard - "we click to send it
to git, codeberk and our server, it will confirm all got it". The dashboard only queues a request (187,
request_release_publish - super admin with the phone code).
NO RELEASE FILE EVER CROSSES THE HETZNER HOST (owner 2026-10-28: "please not download from hetzer at all... because we
might hit trafic when users use the relay server for the remote desktop"): its line carries TagIO's remote-desktop
relay. And NO NEW KEY (owner 2026-10-28: "i prefer to use the existing keys and not use new"): the files wait under
WAIT_PREFIX/ in the feed's own R2 bucket (WAIT_BUCKET - our download server serves feed/ only, so no PC can reach them);
a GitHub Actions run of RUNNER_WORKFLOW in the feed repository RUNNER_REPO moves them; the Hetzner host only gives the
orders and reads small answers.

On the Hetzner host (root; its GITHUB_TOKEN - Contents read/write on the feed repository only, the key it already had -
starts the runner with a repository_dispatch and reads the runner's answers):
  register                  called over SSH by pre_release.bat with the release's LIST on stdin (the files themselves
                            went from the signing PC straight to the waiting area): check the list, order the runner to
                            check the files and the signature the way a PC does, register the release as WAITING
                            (187 release_job_register). Publishes nothing.
  ready                     the runner's workflow and program are in the feed repository and the key reads them
                            (install.sh asks this before it switches the job over).
  run                       root's cron, every minute: heartbeat, then at most ONE queued request:
                              send_in_steps - the package BESIDE the current one + stable/rollout-v2.json
                              to_everyone   - the ordinary publish (lists, packages, old ones removed, rollout file gone)
                              to_beta       - the ordinary publish into the BETA lists (189: a version ending in b)
                            ordered to the runner; then every place is read back FROM HERE by fingerprints only (file
                            lists of GitHub and Codeberg, the size-free HEAD of our download server) - no file.
In the runner (a GitHub Actions run; its own token pushes to GitHub, the Codeberg and R2 keys are the feed repository's
secrets - all given as RP_KEY_* variables):
  runner                    one order (RP_ORDER ...): fetch the release from the waiting area, check it, and for a send
                            put it on GitHub, Codeberg and R2 and read each back; answers on RESULTS_BRANCH (Answers).
                            A release that went out removes the waiting copies of the older ones of its channel.
  make-pinned-ca            write the CA file of the pinned roots (the 5 key pins of package_signature.cpp) from the
                            system bundle; the signature check accepts a chain only if it ends at one of them.

Every request e-mails the owner (Resend, as /root/tagpulse-health-alert.sh). Python standard library only;
osslsigncode + openssl + git from apt (in the runner).
"""
import base64
import datetime
import fcntl
import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

JOB_VERSION = '4 (2026-10-28, existing keys)'
HOME = os.environ.get('RP_HOME', '/root/release-publisher')
KEYS_FILE = os.environ.get('RP_KEYS', os.path.join(HOME, 'keys.env'))
PINNED_CA = os.environ.get('RP_PINNED_CA', os.path.join(HOME, 'pinned-roots.pem'))
# The waiting area: WAIT_PREFIX/<version>/<upload>/ in the feed's bucket. Our download server (tools\feed-worker) serves
# only keys starting feed/, the bucket has no other public address - so a waiting release reaches no PC.
WAIT_BUCKET = os.environ.get('RP_WAIT_BUCKET', 'tagpulse-feed')
WAIT_PREFIX = 'waiting'                              # = $script:ReleaseWaitingPrefix in tools\release_waiting.ps1
RUNNER_REPO = os.environ.get('RP_RUNNER_REPO', 'gkal/tagpulse-updates')   # the feed repository
RUNNER_WORKFLOW = '.github/workflows/release.yml'     # = supa-ops/release-runner/.github/workflows/release.yml
RUNNER_PROGRAM = '.github/release-runner/release-publisher.py'   # this file, put there by setup_runner.py
RUNNER_EVENT = 'tagpulse-release'                    # the repository_dispatch type release.yml listens to
RESULTS_BRANCH = 'release-results'                   # the runner's answers: a branch no PC reads
GITHUB_API = os.environ.get('RP_GITHUB_API', 'https://api.github.com')
RESULT_FILE = os.environ.get('RP_RESULT', 'result.json')
# GitHub ends a run 25 minutes after it began (release.yml), and a run begins no later than start_by: the host's wait
# outlasts both, so when it gives up the run is over.
RUNNER_WAIT_S = int(os.environ.get('RP_RUNNER_WAIT_S', '2400'))
ORDERS = ('check', 'send_in_steps', 'to_everyone', 'to_beta')
# The runner's keys (RP_KEY_<name>: its own token as GITHUB_TOKEN, the rest the feed repository's secrets). Never
# printed; the run's log is masked by GitHub as well.
RUNNER_KEYS = ('GITHUB_TOKEN', 'CODEBERG_TOKEN', 'R2_ENDPOINT', 'R2_BUCKET', 'R2_FEED_PREFIX', 'R2_ACCESS_KEY_ID',
               'R2_SECRET_ACCESS_KEY', 'R2_PUBLIC_BASE', 'GITHUB_REMOTE', 'CODEBERG_REMOTE')
DB_CONTAINER = os.environ.get('RP_DB_CONTAINER', 'supabase-db')   # exact name: three Supabase stacks share this host
DB_USER = os.environ.get('RP_DB_USER', 'supabase_admin')
LOCK_FILE = os.environ.get('RP_LOCK', '/run/lock/release-publisher.lock')   # register and run never overlap
MAIL_ENV = os.environ.get('RP_MAIL_ENV', '/root/supabase/docker/.env')
MAIL_ON = os.environ.get('RP_MAIL', 'on') == 'on'
MAIL_TO = 'info@tagpulse.ai'
MAIL_FROM = 'TagPulse Releases <alerts@tagpulse.ai>'
ROLLOUT_FILE = 'rollout-v2.json'            # = kRolloutFileName in Core/service-engine/staged_rollout.h
REGISTRY_NUMBER = '069222103000'            # = kCompanyRegistryNumber in Core/shared-utils/src/package_signature.cpp
# = kRootKeyPins in package_signature.cpp: SHA-256 of each pinned root's public key (SubjectPublicKeyInfo).
ROOT_KEY_PINS = {
    '348767cdad3bdd28b2b8dd5351aec30c68cec5cd69d276df3827dbc4f5806464',  # SSL.com EV Root Certification Authority ECC
    '7cd67c248f69d83fc2f9bb01dcb1f7ad67a363d046043796d0984c3a231f6bb0',  # SSL.com EV Root Certification Authority RSA R2
    '42a807cec5ae9c0f03b40ca043ac70468b5219bd75cc5bbea51d921dd100156f',  # SSL.com EV Root Certification Authority RSA
    '272e471daded5c939599be3f826de3b8fdc5343562949b2f6d513c6526be3b66',  # SSL.com Code Signing ECC Root CA 2022
    'a828d6f2e0162f2e43463c1e97c1315510caca765ae2e6e53fd3eabbd2e1ad00',  # SSL.com Code Signing RSA Root CA 2022
}
SYSTEM_CA = '/etc/ssl/certs/ca-certificates.crt'
VERSION_RE = re.compile(r'^[0-9]+\.[0-9]+\.[0-9]+b?$')
# What a release copy holds (written by pre_release.bat), relative to its folder. packages/ = the per-component
# tree; the setup installer is NOT part of it - it is published with `updater --setup` as before.
TOP_FILES = ('manifest.pb', 'manifest.textproto', 'manifest-v2.json', 'updater_versions.md')


class Refused(Exception):
    """A check said no. The message is shown to the owner as it is."""


def log(msg):
    print(f'{datetime.datetime.now(datetime.timezone.utc):%Y-%m-%dT%H:%M:%SZ} {msg}', flush=True)


def run(args, cwd=None, check=True, secret=None, timeout=900):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if check and p.returncode != 0:
        text = (p.stderr or p.stdout or '').strip()
        if secret:
            text = text.replace(secret, '<key>')
        raise Refused(f'{os.path.basename(args[0])} failed: {text[-400:]}')
    return p


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def fingerprints_file(path):
    """(sha256, git blob sha1, md5) of a file: the git blob is what GitHub's and Codeberg's file lists name, the md5 is
    the ETag R2 gives a file put in one piece - so the Hetzner host can read a place back without the file."""
    size = os.path.getsize(path)
    s, g, m = hashlib.sha256(), hashlib.sha1(f'blob {size}\0'.encode()), hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            s.update(chunk)
            g.update(chunk)
            m.update(chunk)
    return s.hexdigest(), g.hexdigest(), m.hexdigest()


def version_key(v):
    return tuple(int(x) for x in re.sub(r'[a-z]$', '', v).split('.')) + ((ord(v[-1]) - 96,) if v[-1:].isalpha() else (0,))


def channel_of(version):
    """The feed folder a release goes to: a version ending in 'b' is a beta (prepare_update_feed.ps1 -BetaSuffix), the
    others are stable. The same rule as 189's request_release_publish and the dashboard."""
    return 'beta' if version.endswith('b') else 'stable'


def read_keys():
    keys = {}
    if os.path.exists(KEYS_FILE):
        if os.stat(KEYS_FILE).st_mode & 0o077:
            raise Refused(f'{KEYS_FILE} can be read by others than root - chmod 600 it first')
        for line in open(KEYS_FILE, encoding='utf-8'):
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                keys[k.strip()] = v.strip().strip('"')
    return keys


def keys_from_env():
    """The runner's keys: the repository's secrets, handed to the run as RP_KEY_<name> (release.yml)."""
    return {k: os.environ[f'RP_KEY_{k}'] for k in RUNNER_KEYS if os.environ.get(f'RP_KEY_{k}')}


# ---------------------------------------------------------------------------------------------------------- database
def sql_text(value):
    if value is None:
        return 'NULL'
    value = str(value)
    tag = 'rp' + secrets.token_hex(4)
    while f'${tag}$' in value:
        tag = 'rp' + secrets.token_hex(4)
    return f'${tag}${value}${tag}$'


def db(sql):
    p = subprocess.run(['docker', 'exec', '-i', DB_CONTAINER, 'psql', '-U', DB_USER, '-d', 'postgres', '-X', '-q', '-t',
                        '-A', '-v', 'ON_ERROR_STOP=1'], input=sql, capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        raise Refused(f'database: {(p.stderr or p.stdout).strip()[-300:]}')
    return p.stdout.strip()


def db_json(sql):
    out = db(sql)
    return json.loads(out) if out else None


# ------------------------------------------------------------------------------------------------- the signature check
def pinned_ca_text():
    """The roots from the system bundle whose key pin is one of ROOT_KEY_PINS."""
    pems = re.findall(r'-----BEGIN CERTIFICATE-----.+?-----END CERTIFICATE-----', open(SYSTEM_CA).read(), re.S)
    found = []
    for pem in pems:
        p = subprocess.run(['openssl', 'x509', '-pubkey', '-noout'], input=pem, capture_output=True, text=True)
        if p.returncode != 0:
            continue
        der = subprocess.run(['openssl', 'pkey', '-pubin', '-outform', 'DER'], input=p.stdout.encode(), capture_output=True)
        if hashlib.sha256(der.stdout).hexdigest() in ROOT_KEY_PINS:
            found.append(pem)
    return found


def make_pinned_ca():
    found = pinned_ca_text()
    if not found:
        raise Refused('none of the pinned SSL.com roots is in the system bundle - nothing could be checked')
    with open(PINNED_CA, 'w', encoding='ascii') as f:
        f.write('\n'.join(found) + '\n')
    os.chmod(PINNED_CA, 0o644)
    log(f'{PINNED_CA}: {len(found)} of {len(ROOT_KEY_PINS)} pinned roots found in {SYSTEM_CA}')


def osslsign_verify(args):
    return run(['osslsigncode', 'verify', '-CAfile', PINNED_CA, '-TSA-CAfile', SYSTEM_CA] + args, check=False, timeout=120)


def signer_has_registry_number(signed_file, kind):
    """kind 'pkcs7' for the catalog (DER PKCS#7); for a program the signer comes from osslsigncode's own report."""
    if kind == 'pkcs7':
        p = run(['openssl', 'pkcs7', '-inform', 'DER', '-in', signed_file, '-print_certs', '-noout'], check=False)
        text = p.stdout
    else:
        text = osslsign_verify(['-in', signed_file]).stdout
    return f'serialNumber = {REGISTRY_NUMBER}' in text or f'serialNumber={REGISTRY_NUMBER}' in text


def check_signature(release_dir, version):
    """The checks every PC makes before it installs (package_signature.cpp), as far as a Linux tool can make them:
    the signed list chains to a pinned root, its signer carries our registry number, it was signed for THIS version,
    every program in the package is in the list (its Authenticode hash) and every other file's hash is in it.
    Returns the sentence shown to the owner; raises Refused on the first failure."""
    if not os.path.exists(PINNED_CA):
        raise Refused(f'no pinned roots file ({PINNED_CA}) - run make-pinned-ca once')
    zip_path = os.path.join(release_dir, 'packages-v2', f'tagpulse-{version}.zip')
    if not os.path.isfile(zip_path):
        raise Refused(f'there is no package packages-v2/tagpulse-{version}.zip')
    with tempfile.TemporaryDirectory(prefix='rp-check-') as tmp:
        try:
            with zipfile.ZipFile(zip_path) as z:
                names = [n for n in z.namelist() if not n.endswith('/')]
                if 'tagpulse-package.cat' not in names:
                    raise Refused('the package carries no signed list of its files (tagpulse-package.cat)')
                z.extractall(tmp)
        except zipfile.BadZipFile as e:
            raise Refused(f'the package is not a readable zip ({e})') from e
        cat = os.path.join(tmp, 'tagpulse-package.cat')
        p = osslsign_verify(['-in', cat])
        if p.returncode != 0:
            raise Refused('the signed list is not signed under a pinned SSL.com root: ' + (p.stdout + p.stderr).strip()[-300:])
        if not signer_has_registry_number(cat, 'pkcs7'):
            raise Refused(f'the signed list is not signed by our company (registry number {REGISTRY_NUMBER})')
        cat_hex = open(cat, 'rb').read().hex()
        if (version.encode('utf-16-le') + b'\x00\x00').hex() not in cat_hex:
            raise Refused(f'the signed list was not signed for version {version}')
        checked = 0
        for name in names:
            if name == 'tagpulse-package.cat':
                continue
            path = os.path.join(tmp, name)
            with open(path, 'rb') as f:
                is_program = f.read(2) == b'MZ'
            if is_program:
                q = osslsign_verify(['-catalog', cat, '-in', path])
                if q.returncode != 0:
                    raise Refused(f'{name} is not in the signed list (or was changed)')
            else:
                data = open(path, 'rb').read()
                if hashlib.sha256(data).hexdigest() not in cat_hex and hashlib.sha1(data).hexdigest() not in cat_hex:
                    raise Refused(f'{name} is not in the signed list (or was changed)')
            checked += 1
    # The loose updater the service fetches when its own is missing (packages/updater-<ver>.exe): Authenticode itself.
    for name in sorted(os.listdir(os.path.join(release_dir, 'packages'))):
        if name.startswith('updater-') and name.endswith('.exe'):
            path = os.path.join(release_dir, 'packages', name)
            if osslsign_verify(['-in', path]).returncode != 0 or not signer_has_registry_number(path, 'program'):
                raise Refused(f'packages/{name} is not signed by our company under a pinned root')
    return f'{checked} file(s) match the list signed by AFOI KALOFORIDI OE ({REGISTRY_NUMBER}) for {version}'


# ------------------------------------------------------------------------------------------------------------ register
SAFE_PATH = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]*(?:/[A-Za-z0-9][A-Za-z0-9._-]*)*$')
HEX = {n: re.compile(f'^[0-9a-f]{{{n}}}$') for n in (32, 40, 64)}
STAGED_RE = re.compile(r'^r2://(?P<bucket>[a-z0-9-]+)/(?P<prefix>[a-z]+)/(?P<version>[0-9.]+b?)/(?P<upload>[0-9a-f]{32})'
                       r'/release\.json#sha256=(?P<sha>[0-9a-f]{64})$')


def check_list(meta, manifest_bytes):
    """The release's list (release.json, written by pre_release.bat) and its v2 list: a stable or beta version whose v2
    list names the same channel, one package that is the one its v2 list names, every file with its size and its three
    fingerprints, no setup installer. Checked on the Hetzner host before anything is ordered, and in the runner again
    against the files themselves (check_copy). Returns (version, manifest)."""
    version = meta.get('version', '') if isinstance(meta, dict) else ''
    if not isinstance(version, str) or not VERSION_RE.match(version):
        raise Refused(f"'{version}' is not a release version (digits, e.g. 0.7.34 - or 0.7.34b for a beta)")
    files = meta.get('files')
    if not isinstance(files, list) or not files:
        raise Refused('the release lists no files')
    listed = {}
    for f in files:
        rel = f.get('path') if isinstance(f, dict) else None
        if not isinstance(rel, str) or not SAFE_PATH.match(rel) or rel == 'release.json':
            raise Refused(f'{rel!r} is not a file name a release may carry')
        if rel in listed:
            raise Refused(f'{rel} is listed twice')
        if rel not in TOP_FILES and not re.match(r'^packages(-v2)?/[^/]+$', rel):
            raise Refused(f'{rel} is not part of a release')
        if not isinstance(f.get('size'), int) or f['size'] < 0 or not all(
                isinstance(f.get(k), str) and HEX[n].match(f[k]) for k, n in (('sha256', 64), ('git_blob', 40), ('md5', 32))):
            raise Refused(f'{rel}: its size or fingerprints are missing from the list')
        listed[rel] = f
    for rel in TOP_FILES:
        if rel not in listed:
            raise Refused(f'{rel} is missing from the release')
    if hashlib.sha256(manifest_bytes).hexdigest() != listed['manifest-v2.json']['sha256']:
        raise Refused('manifest-v2.json is not the one the release lists (SHA-256 differs)')
    try:
        manifest = json.loads(manifest_bytes.decode('utf-8-sig'))
    except ValueError as e:
        raise Refused(f'manifest-v2.json is not readable ({e})') from e
    zip_rel = f'packages-v2/tagpulse-{version}.zip'
    if manifest.get('version') != version or manifest.get('url') != zip_rel:
        raise Refused(f"manifest-v2.json names {manifest.get('version')} / {manifest.get('url')}, not {version} / {zip_rel}")
    # The channel the release was BUILT for (-BetaSuffix writes "beta") must be the one its version sends it to.
    if manifest.get('channel') != channel_of(version):
        raise Refused(f"manifest-v2.json was made for the {manifest.get('channel')!r} channel, but {version} is a "
                      f"{channel_of(version)} version")
    if [p for p in listed if p.startswith('packages-v2/')] != [zip_rel]:
        raise Refused(f'packages-v2 must hold exactly one package, {zip_rel}')
    if listed[zip_rel]['sha256'] != str(manifest.get('sha256', '')).lower():
        raise Refused('the package is not the one manifest-v2.json names (SHA-256 differs)')
    if any(p.startswith('packages/setup-') for p in listed):
        raise Refused('a setup installer is not part of a dashboard release - publish it with updater --setup')
    return version, manifest


def check_copy(incoming):
    """The copy the runner fetched from the waiting area: nothing more and nothing less than its list, every file whole
    (size and all three fingerprints), and a list that passes check_list. Returns (version, meta, manifest)."""
    meta = json.load(open(os.path.join(incoming, 'release.json'), encoding='utf-8-sig'))
    listed = {f['path']: f for f in meta.get('files', []) if isinstance(f, dict) and isinstance(f.get('path'), str)}
    present = set()
    for root, dirs, files in os.walk(incoming):
        for fn in files + dirs:
            if os.path.islink(os.path.join(root, fn)):
                raise Refused(f'{fn} is a link, not a file - refused')
        for fn in files:
            rel = os.path.relpath(os.path.join(root, fn), incoming).replace(os.sep, '/')
            if rel != 'release.json':
                present.add(rel)
    if present != set(listed):
        raise Refused(f'the waiting copy differs from its list: missing {sorted(set(listed) - present)}, '
                      f'extra {sorted(present - set(listed))}')
    for rel, f in listed.items():
        path = os.path.join(incoming, rel)
        if os.path.getsize(path) != f.get('size') or fingerprints_file(path) != (f.get('sha256'), f.get('git_blob'), f.get('md5')):
            raise Refused(f'{rel} did not arrive whole (size or fingerprints differ)')
    version, manifest = check_list(meta, open(os.path.join(incoming, 'manifest-v2.json'), 'rb').read())
    return version, meta, manifest


def staged_location(version, upload, release_sha):
    """Where a registered release waits (release_candidates.staged_dir): the waiting area, its upload and the SHA-256
    of its list - a send fetches exactly the list that was checked and registered, or refuses."""
    return f'r2://{WAIT_BUCKET}/{WAIT_PREFIX}/{version}/{upload}/release.json#sha256={release_sha}'


def parse_staged(cand):
    m = STAGED_RE.match(cand.get('staged_dir') or '')
    if not m or m['version'] != cand['version'] or m['bucket'] != WAIT_BUCKET or m['prefix'] != WAIT_PREFIX:
        raise Refused(f"{cand['version']} was prepared the old way (its files on the Hetzner host) - run pre_release.bat "
                      f"for it again, then send it")
    return m['upload'], m['sha']


def cmd_register(stdin_text):
    """pre_release.bat put the files in the waiting area and sends their LIST here (JSON on stdin: upload, and the exact
    bytes of release.json and manifest-v2.json, base64). The runner checks the files; this host registers the result."""
    try:
        data = json.loads(stdin_text.lstrip('﻿'))     # a Windows pipe may put a byte-order mark in front
        upload = data['upload']
        release_bytes = base64.b64decode(data['release_json_b64'], validate=True)
        manifest_bytes = base64.b64decode(data['manifest_json_b64'], validate=True)
        meta = json.loads(release_bytes.decode('utf-8-sig'))
    except (ValueError, KeyError, TypeError) as e:
        raise Refused(f'the release list did not arrive readable ({type(e).__name__})') from e
    if not isinstance(upload, str) or not HEX[32].match(upload):
        raise Refused('the release list names no upload of the waiting area')
    version, manifest = check_list(meta, manifest_bytes)
    release_sha = hashlib.sha256(release_bytes).hexdigest()
    log(f'register {version}: the runner checks upload {upload}')
    print(f'Checking {version} in the waiting area (GitHub runner) ...', flush=True)
    result = Runner(read_keys()).order('check', version, upload, release_sha, '', progress=True)
    if not result.get('ok'):
        # The copy could not be checked at all (incomplete, changed, unreadable): nothing is registered.
        raise Refused(str(result.get('says') or 'the runner could not check the release'))
    check_ok, says = bool(result.get('check_ok')), str(result.get('says', ''))[:2000]
    verdict = db_json(
        'SELECT private.release_job_register(' + ', '.join([
            sql_text(version), sql_text(staged_location(version, upload, release_sha)), sql_text(meta.get('notes', '')),
            sql_text(meta.get('prepared_by', '')), sql_text(meta.get('prepared_at')) + '::timestamptz',
            sql_text(json.dumps(manifest)) + '::jsonb', sql_text(json.dumps(meta['files'])) + '::jsonb',
            'true' if check_ok else 'false', sql_text(says)]) + ');')
    if 'replaced' not in verdict:
        # Refused by the database (already sent, or being sent now): what went out stays as it is.
        raise Refused(verdict.get('says', 'refused'))
    # Registered (a release that failed the check is registered too, so the pop-up shows WHY it cannot be sent). A
    # waiting release of the same version is replaced by this one.
    if not check_ok:
        raise Refused(f'registered as NOT usable: {says}')
    log(f'WAITING {version}: {says}')
    print(f'OK {version} is waiting in the private waiting area at Cloudflare - nothing was published. {says}')


# ---------------------------------------------------------------------------------------------- the runner (GitHub)
class WaitingArea:
    """WAIT_PREFIX/ in the feed's bucket, where the signing PC put the release (tools\\release_waiting.ps1, with the
    feed's own R2 key). Only the runner reads it; our download server serves feed/ only, so no PC can."""

    def __init__(self, keys):
        if not all(keys.get(k) for k in ('R2_ENDPOINT', 'R2_ACCESS_KEY_ID', 'R2_SECRET_ACCESS_KEY')):
            raise Refused('the runner has no key for the waiting area')
        self.s3 = S3Place(keys['R2_ENDPOINT'], WAIT_BUCKET, '', keys['R2_ACCESS_KEY_ID'],
                          keys['R2_SECRET_ACCESS_KEY'], keys.get('R2_REGION', 'auto'), '')

    def _get(self, key):
        code, _h, body = self.s3._request('GET', key)
        if code == 404:
            raise Refused(f'{key} is not in the waiting area')
        if code != 200:
            raise Refused(f'the waiting area could not be read ({key}): HTTP {code}')
        return body

    def fetch(self, version, upload, release_sha, dest):
        base = f'{WAIT_PREFIX}/{version}/{upload}/'
        release_bytes = self._get(base + 'release.json')
        if hashlib.sha256(release_bytes).hexdigest() != release_sha:
            raise Refused('the waiting copy is not the one that was registered (its list changed since)')
        try:
            meta = json.loads(release_bytes.decode('utf-8-sig'))
        except ValueError as e:
            raise Refused(f'the waiting copy\'s list is not readable ({e})') from e
        # Every name first, before anything is fetched or written.
        rels = [f.get('path') if isinstance(f, dict) else None for f in (meta.get('files', []) if isinstance(meta, dict) else [])]
        for rel in rels:
            if not isinstance(rel, str) or not SAFE_PATH.match(rel) or rel == 'release.json':
                raise Refused(f'{rel!r} is not a file name a release may carry')
        for rel in rels:
            path = os.path.join(dest, *rel.split('/'))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'wb') as out:
                out.write(self._get(base + rel))
        with open(os.path.join(dest, 'release.json'), 'wb') as out:
            out.write(release_bytes)

    def clear_sent(self, version):
        """After `version` went out: every waiting copy of its channel BELOW it is removed - none of them can be sent any
        more (each place refuses a version that is not newer than the one it gives everyone). Its own copy stays until
        a newer one goes out: the Hetzner host's own read-back may still fail this send, and a repeated press needs it.
        Returns how many files went."""
        removed = 0
        for key in self._keys(f'{WAIT_PREFIX}/'):
            parts = key.split('/')
            if (len(parts) < 4 or not VERSION_RE.match(parts[1]) or channel_of(parts[1]) != channel_of(version)
                    or version_key(parts[1]) >= version_key(version)):
                continue
            code, _h, _b = self.s3._request('DELETE', key)
            if code not in (200, 204, 404):
                raise Refused(f'{key} could not be removed: HTTP {code}')
            removed += 1
        return removed

    def _keys(self, prefix):
        keys, token = [], None
        while True:
            q = {'list-type': '2', 'prefix': prefix}
            if token:
                q['continuation-token'] = token
            code, _h, body = self.s3._request('GET', '', query=q)
            if code != 200:
                raise Refused(f'the waiting area could not be listed: HTTP {code}')
            text = body.decode()
            keys += re.findall(r'<Key>([^<]+)</Key>', text)
            m = re.search(r'<NextContinuationToken>([^<]+)</NextContinuationToken>', text)
            if not m:
                return keys
            token = m.group(1)


def scrubbed(result, keys):
    """The answers branch is public (the feed repository is): no key, and not the feed's hidden folder name either, may
    stand in an answer - a failure message can carry a storage key or an address."""
    text = json.dumps(result)
    names = ('R2_PUBLIC_BASE', 'R2_FEED_PREFIX', 'R2_ENDPOINT', 'R2_ACCESS_KEY_ID', 'R2_SECRET_ACCESS_KEY',
             'CODEBERG_TOKEN', 'GITHUB_TOKEN')
    values = [(keys.get(n, ''), n) for n in names]
    values += [(part, 'R2_FEED_PREFIX') for part in keys.get('R2_FEED_PREFIX', '').split('/')]
    for value, name in values:
        if len(value) >= 8:
            text = text.replace(value, f'<{name}>')
    return json.loads(text)


def cmd_runner():
    """One order, in the GitHub Actions run (release.yml). Answers the Hetzner host on RESULTS_BRANCH: <nonce>.started
    once it begins, <nonce>.json at the end (also written to RESULT_FILE in the run)."""
    order, version, upload = (os.environ.get(n, '') for n in ('RP_ORDER', 'RP_VERSION', 'RP_UPLOAD'))
    release_sha, open_rollout, nonce = (os.environ.get(n, '') for n in ('RP_RELEASE_SHA', 'RP_OPEN_ROLLOUT', 'RP_NONCE'))
    start_by = os.environ.get('RP_START_BY', '')
    result = {'nonce': nonce, 'order': order, 'version': version, 'ok': False, 'check_ok': False, 'says': '',
              'places': {}}
    keys, answers = {}, None
    try:
        if (order not in ORDERS or not VERSION_RE.match(version) or not HEX[32].match(upload)
                or not HEX[64].match(release_sha) or not HEX[32].match(nonce) or not re.match(r'^[0-9]{10}$', start_by)
                or (open_rollout and not VERSION_RE.match(open_rollout))):
            raise Refused('the order is not one this runner carries out')
        keys = keys_from_env()
        answers = Answers(keys.get('GITHUB_TOKEN', ''))
        # The host cannot stop a run: it stops WAITING for one at start_by (and a little after). A run GitHub began
        # later than that must do nothing - the host has already told the owner nothing was done.
        if time.time() > int(start_by):
            raise Refused('GitHub began this run after the Hetzner host had stopped waiting for it - nothing was done')
        answers.put(f'{nonce}.started', {'nonce': nonce, 'order': order, 'version': version})
        with tempfile.TemporaryDirectory(prefix='rp-release-') as d:
            WaitingArea(keys).fetch(version, upload, release_sha, d)
            got, _meta, _manifest = check_copy(d)
            if got != version:
                raise Refused(f'the waiting copy is {got}, not {version}')
            try:
                result['check_ok'], result['says'] = True, check_signature(d, version)
            except Refused as e:
                result['check_ok'], result['says'] = False, str(e)
            if order == 'check':
                result['ok'] = True
                return
            if not result['check_ok']:
                raise Refused(f'{version} did not pass the signature check: {result["says"]}')
            # The order must fit the release's channel (189 refuses the others before they are queued, the Hetzner
            # host again before it orders; checked here as well, where the keys are).
            if (order == 'to_beta') != (channel_of(version) == 'beta'):
                raise Refused(f'{version} is a {channel_of(version)} release - "{order}" is not for it')
            places = places_from_keys(keys)
            missing = [n for n, p in places.items() if p is None]
            if missing:
                raise Refused('the runner has no key for: ' + ', '.join(missing))
            if not os.path.exists(PINNED_CA) or shutil.which('osslsigncode') is None:
                raise Refused('the runner has no signature checker')
            guard = feed_guard(d, version, order, open_rollout)
            # One place after the other, and the first that fails stops the rest: pressing the button again repeats
            # the request, and a place that already holds the release says so and is read back again.
            ok = True
            for name in ('github', 'codeberg', 'r2'):
                if not ok:
                    result['places'][name] = {'state': 'not started', 'says': 'not started because an earlier place failed'}
                    continue
                place = places[name]
                try:
                    said = place.publish(d, version, order, guard)
                    result['places'][name] = {'state': 'uploaded', 'says': said}
                    said = f'{said}; {place.read_back()}'
                    result['places'][name] = {'state': 'ok', 'says': said}
                except (Refused, OSError, subprocess.SubprocessError) as e:
                    ok = False
                    result['places'][name] = {'state': 'failed', 'says': str(e)}
            result['ok'] = ok
            result['says'] = 'all three places confirmed' if ok else 'not every place confirmed'
            if ok and order in ('to_everyone', 'to_beta'):
                # Tidying only: the release is out whatever this says, and the next release tries again.
                try:
                    gone = WaitingArea(keys).clear_sent(version)
                    result['says'] += f'; {gone} waiting file(s) of {channel_of(version)} releases before {version} removed'
                except Refused as e:
                    result['says'] += f'; the waiting copies stay until the next release ({e})'
    except Refused as e:
        result['ok'], result['says'] = False, str(e)
    except Exception as e:      # whatever stopped it is reported to the dashboard, never lost
        result['ok'], result['says'] = False, f'{type(e).__name__}: {e}'
    finally:
        result = scrubbed(result, keys)
        with open(RESULT_FILE, 'w', encoding='utf-8') as f:
            json.dump(result, f)
        if answers is not None:
            try:
                answers.put(f'{nonce}.json', result)
            except Refused as e:
                log(f'the answer could not be given to the Hetzner host: {e}')
        log(f'{order} {version}: {"OK" if result["ok"] else "NOT OK"} - {result["says"]}')


# ----------------------------------------------------------------------------- the answers (runner -> Hetzner host)
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """A redirect is not followed: Python would send our key along to wherever it points."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


NO_REDIRECT = urllib.request.build_opener(_NoRedirect)
POLL_S = float(os.environ.get('RP_POLL_S', '10'))
RUNNER_START_S = int(os.environ.get('RP_RUNNER_START_S', '600'))     # a run must begin within this (start_by)
START_GRACE_S = int(os.environ.get('RP_START_GRACE_S', '120'))       # its first answer may take this much longer
READBACK_TRIES, READBACK_PAUSE_S = 3, float(os.environ.get('RP_READBACK_PAUSE_S', '15'))


class Answers:
    """results/<name> on RESULTS_BRANCH of the feed repository, through GitHub's contents API: the runner writes them with
    the run's own token, the Hetzner host reads them with its GITHUB_TOKEN (Contents: read). The branch has a history of
    its own (no commit of the feed), and no PC reads it."""

    def __init__(self, token, api=None, repo=None):
        self.token = token
        self.api = (api or GITHUB_API).rstrip('/')
        self.repo = repo or RUNNER_REPO

    def call(self, method, path, body=None, timeout=30):
        if not self.token:
            raise Refused('no GitHub key - the runner at GitHub cannot be reached')
        headers = {'Accept': 'application/vnd.github+json', 'Authorization': f'Bearer {self.token}',
                   'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'tagpulse-release-publisher'}
        if body is not None:
            headers['Content-Type'] = 'application/json'
        req = urllib.request.Request(self.api + path, data=json.dumps(body).encode() if body is not None else None,
                                     method=method, headers=headers)
        try:
            with NO_REDIRECT.open(req, timeout=timeout) as r:
                data = r.read()
                if data and 'json' in (r.headers.get('Content-Type') or ''):
                    data = json.loads(data)
                return r.status, data
        except urllib.error.HTTPError as e:
            data = e.read()[:2000]
            try:
                data = json.loads(data)
            except ValueError:
                pass
            return e.code, data
        except (urllib.error.URLError, OSError) as e:
            raise Refused(f'GitHub could not be reached: {getattr(e, "reason", e)}') from e

    def get(self, name):
        """The answer, or None while there is none (yet)."""
        code, data = self.call('GET', f'/repos/{self.repo}/contents/results/{name}?ref={RESULTS_BRANCH}')
        if code in (401, 403):
            raise Refused(f'GitHub refused the Hetzner host\'s key for {self.repo}: HTTP {code}')
        if code != 200 or not isinstance(data, dict):
            return None         # not there yet - or a passing hiccup: the caller keeps looking until its time is up
        try:
            return json.loads(base64.b64decode(data.get('content', '')).decode('utf-8'))
        except (ValueError, TypeError):
            return None

    def put(self, name, obj):
        """Runner side: one answer (a new file - its name carries the order's nonce)."""
        path = f'/repos/{self.repo}/contents/results/{name}'
        body = {'message': f'release runner: {name}', 'branch': RESULTS_BRANCH,
                'content': base64.b64encode(json.dumps(obj).encode('utf-8')).decode()}
        code, data = self.call('PUT', path, body)
        if code not in (200, 201) and not self._branch_exists():
            self._make_branch()             # the very first answer (or the branch was deleted)
            code, data = self.call('PUT', path, body)
        if code == 422:                     # written once already: replaced
            c2, d2 = self.call('GET', f'{path}?ref={RESULTS_BRANCH}')
            if c2 == 200 and isinstance(d2, dict) and d2.get('sha'):
                code, data = self.call('PUT', path, dict(body, sha=d2['sha']))
        if code not in (200, 201):
            raise Refused(f'the answer {name} could not be written at GitHub: HTTP {code} {str(data)[:200]}')

    def _branch_exists(self):
        return self.call('GET', f'/repos/{self.repo}/branches/{RESULTS_BRANCH}')[0] == 200

    def _make_branch(self):
        code, tree = self.call('POST', f'/repos/{self.repo}/git/trees', {'tree': [{
            'path': 'README.md', 'mode': '100644', 'type': 'blob',
            'content': 'Answers of the TagPulse release runner to its Hetzner host (results/). Not part of the update '
                       'feed: no PC reads this branch.\n'}]})
        if code == 201 and isinstance(tree, dict):
            code, commit = self.call('POST', f'/repos/{self.repo}/git/commits',
                                     {'message': 'release runner answers', 'tree': tree['sha'], 'parents': []})
            if code == 201 and isinstance(commit, dict):
                code, _d = self.call('POST', f'/repos/{self.repo}/git/refs',
                                     {'ref': f'refs/heads/{RESULTS_BRANCH}', 'sha': commit['sha']})
                if code in (201, 422):      # 422: another run made it a moment ago
                    return
        raise Refused(f'the branch {RESULTS_BRANCH} for the answers could not be made at GitHub: HTTP {code}')


# --------------------------------------------------------------------------------------- the Hetzner host's orders
class Runner:
    """Our runner at GitHub as the Hetzner host gives it orders: RUNNER_WORKFLOW in the feed repository, started by a
    repository_dispatch - GitHub asks Contents: write for it, the right the host's GITHUB_TOKEN has had all along. That
    key cannot change the workflow (GitHub asks the Workflows right for that) and never sees the run's secrets. It
    cannot stop a run either: a run checks the order's start_by itself, and GitHub ends one 25 minutes after it
    began (release.yml) - both inside RUNNER_WAIT_S."""

    def __init__(self, keys):
        self.answers = Answers(keys.get('GITHUB_TOKEN', ''), keys.get('RUNNER_API', GITHUB_API),
                               keys.get('RUNNER_REPO', RUNNER_REPO))

    def ready(self):
        """True when the workflow and the runner program are on the feed repository's main branch (the one a
        repository_dispatch runs from), read with the host's own key - a key GitHub refuses is not ready either."""
        try:
            return all(self.answers.call('GET', f'/repos/{self.answers.repo}/contents/{path}')[0] == 200
                       for path in (RUNNER_WORKFLOW, RUNNER_PROGRAM))
        except Refused:
            return False

    def order(self, order, version, upload, release_sha, open_rollout, progress=False):
        nonce = secrets.token_hex(16)
        payload = {'order': order, 'version': version, 'upload': upload, 'release_sha': release_sha,
                   'open_rollout': open_rollout, 'nonce': nonce, 'start_by': str(int(time.time()) + RUNNER_START_S)}
        code, data = self.answers.call('POST', f'/repos/{self.answers.repo}/dispatches',
                                       {'event_type': RUNNER_EVENT, 'client_payload': payload})
        if code != 204:
            raise Refused(f'GitHub did not take the order: HTTP {code} {str(data)[:200]}')
        started, began, shown = time.monotonic(), False, 0
        while True:
            waited = time.monotonic() - started
            result = self.answers.get(f'{nonce}.json')
            if result is not None:
                break
            began = began or self.answers.get(f'{nonce}.started') is not None
            if not began and waited > RUNNER_START_S + START_GRACE_S:
                raise Refused(f'GitHub took the order but began no run within {RUNNER_START_S // 60} minutes - nothing '
                              f'was done (a run that begins later does nothing)')
            if waited > RUNNER_WAIT_S:
                raise Refused(f'the runner gave no answer for "{order}" {version} within {RUNNER_WAIT_S // 60} minutes '
                              f'(GitHub has ended the run by now) - press the button again to repeat it; a place that '
                              f'already holds it says so')
            if progress and waited >= shown + 15:
                shown += 15
                print(f'  ... the runner at GitHub is on it ({int(waited)} s)', flush=True)
            time.sleep(POLL_S)
        if result.get('nonce') != nonce or result.get('order') != order or result.get('version') != version:
            raise Refused('the runner answered for another order')
        return result


def read_back_here(keys, cand, version, action, name):
    """The Hetzner host's OWN read-back of one place, by fingerprints only - it never holds the files: what the
    registered list says the place must serve now, against GitHub's / Codeberg's file list or our download server's
    answer to a HEAD (its ETag is the file's md5). The runner read every place back too; this one does not take its
    word for it. A place's file list can lag a push by seconds: READBACK_TRIES looks, READBACK_PAUSE_S apart."""
    for attempt in range(1, READBACK_TRIES + 1):
        try:
            return _read_back_once(keys, cand, version, action, name)
        except Refused:
            if attempt == READBACK_TRIES:
                raise
            time.sleep(READBACK_PAUSE_S)


def _read_back_once(keys, cand, version, action, name):
    ch = channel_of(version)
    files = {f['path']: f for f in cand['files']}
    zip_rel = f'packages-v2/tagpulse-{version}.zip'
    if action == 'send_in_steps':
        want = {zip_rel: files[zip_rel], ROLLOUT_FILE: files['manifest-v2.json']}
    else:
        top = TOP_FILES if name == 'github' else [t for t in TOP_FILES if t != 'updater_versions.md']
        want = {t: files[t] for t in top}
        want[zip_rel] = files[zip_rel]
        if name in ('github', 'r2'):
            want.update({rel: f for rel, f in files.items() if rel.startswith('packages/')})
        if action == 'to_everyone':
            want[ROLLOUT_FILE] = None
    bad = []
    if name in ('github', 'codeberg'):
        repo = keys.get(f'{name.upper()}_REPO', 'gkal/tagpulse-updates')
        api = 'https://api.github.com' if name == 'github' else 'https://codeberg.org/api/v1'
        remote = keys.get(f'{name.upper()}_REMOTE', '')   # file:// in the tests only; else the public API
        place = GitPlace(name, remote, keys.get(f'{name.upper()}_BRANCH', 'main'), False, api, '', repo, False)
        tree = place.remote_tree()
        for rel, f in want.items():
            got = tree.get(f'{ch}/{rel}')
            if f is None and got is not None:
                bad.append(f'{rel} (still there)')
            elif f is not None and got != f['git_blob']:
                bad.append(f'{rel} ({"missing" if got is None else "different"})')
        if action != 'send_in_steps':
            # Nothing else in the folders a full release replaces whole (Codeberg keeps no packages/ folder).
            for sub in ('packages-v2/',) + (('packages/',) if name == 'github' else ()):
                extra = [p for p in tree if p.startswith(f'{ch}/{sub}') and p[len(ch) + 1:] not in want]
                bad += [f'{p[len(ch) + 1:]} (left over)' for p in extra]
    else:
        base = keys.get('R2_PUBLIC_BASE', '').rstrip('/')
        if not base:
            raise Refused('r2: the Hetzner host has no R2_PUBLIC_BASE - it cannot read the download server back')
        for rel, f in want.items():
            req = urllib.request.Request(f'{base}/{ch}/{rel}', method='HEAD',
                                         headers={'User-Agent': 'tagpulse-release-publisher', 'Cache-Control': 'no-cache'})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    code, etag = r.status, (r.headers.get('ETag') or '').strip('"')
            except urllib.error.HTTPError as e:
                code, etag = e.code, ''
            except (urllib.error.URLError, OSError) as e:
                raise Refused(f'r2: our download server did not answer the Hetzner host ({getattr(e, "reason", e)})') from e
            if f is None and code != 404:
                bad.append(f'{rel} (still there)')
            elif f is not None and (code not in (200, 206) or etag != f['md5']):
                bad.append(f'{rel} ({"missing" if code == 404 else "different" if code in (200, 206) else f"HTTP {code}"})')
    if bad:
        raise Refused(f'{name} read back from the Hetzner host differently: ' + ', '.join(bad[:6]))
    return f'{name}: {len(want)} file(s) read back from the Hetzner host by fingerprint'


# ------------------------------------------------------------------------------------------------------- the 3 places
class GitPlace:
    """GitHub (normal history) or Codeberg (history collapsed to one commit - see prepare_update_feed.ps1)."""

    def __init__(self, name, remote, branch, collapse, api, api_token, repo, copy_v1_and_notes):
        self.name, self.remote, self.branch, self.collapse = name, remote, branch, collapse
        self.api, self.api_token, self.repo, self.copy_v1_and_notes = api, api_token, repo, copy_v1_and_notes
        self.secret = None
        m = re.match(r'https://[^:]+:([^@]+)@', remote)
        if m:
            self.secret = m.group(1)
        self.expected = {}       # path -> git blob sha (or None = must be absent), for the read-back

    def _git(self, args, cwd):
        return run(['git'] + args, cwd=cwd, secret=self.secret)

    def publish(self, release_dir, version, action, previous_feed_version_check):
        channel = channel_of(version)
        with tempfile.TemporaryDirectory(prefix=f'rp-{self.name}-') as tmp:
            run(['git', 'clone', '-q', '--depth', '1', '--branch', self.branch, self.remote, tmp], secret=self.secret)
            ch = os.path.join(tmp, channel)
            os.makedirs(os.path.join(ch, 'packages-v2'), exist_ok=True)
            previous_feed_version_check(self.name, ch)
            zip_name = f'tagpulse-{version}.zip'
            if action == 'send_in_steps':
                shutil.copyfile(os.path.join(release_dir, 'packages-v2', zip_name), os.path.join(ch, 'packages-v2', zip_name))
                shutil.copyfile(os.path.join(release_dir, 'manifest-v2.json'), os.path.join(ch, ROLLOUT_FILE))
                msg = f'release in steps v{version}'
            else:
                top = list(TOP_FILES) if self.copy_v1_and_notes else [f for f in TOP_FILES if f != 'updater_versions.md']
                for f in top:
                    shutil.copyfile(os.path.join(release_dir, f), os.path.join(ch, f))
                for old in os.listdir(os.path.join(ch, 'packages-v2')):
                    os.remove(os.path.join(ch, 'packages-v2', old))
                shutil.copyfile(os.path.join(release_dir, 'packages-v2', zip_name), os.path.join(ch, 'packages-v2', zip_name))
                if self.copy_v1_and_notes:
                    v1 = os.path.join(ch, 'packages')
                    os.makedirs(v1, exist_ok=True)
                    for old in os.listdir(v1):
                        os.remove(os.path.join(v1, old))
                    for f in os.listdir(os.path.join(release_dir, 'packages')):
                        shutil.copyfile(os.path.join(release_dir, 'packages', f), os.path.join(v1, f))
                if action == 'to_everyone' and os.path.exists(os.path.join(ch, ROLLOUT_FILE)):
                    os.remove(os.path.join(ch, ROLLOUT_FILE))
                msg = f'release v{version}'
            status = self._git(['status', '--porcelain'], tmp).stdout.strip()
            if not status:
                said = f'{self.name} already holds it'
            else:
                commit = ['-c', 'user.email=ci@tagpulse.local', '-c', 'user.name=TagPulse CI', 'commit', '-q', '-m', msg]
                if self.collapse:
                    # As prepare_update_feed.ps1: Codeberg's history is collapsed to ONE commit on every publish (a
                    # deleted package's bytes would otherwise stay in the repository forever).
                    self._git(['checkout', '-q', '--orphan', '__publish'], tmp)
                    self._git(['add', '-A'], tmp)
                    self._git(commit, tmp)
                    self._git(['branch', '-D', self.branch], tmp)
                    self._git(['branch', '-m', self.branch], tmp)
                    self._git(['push', '-q', '--force', 'origin', self.branch], tmp)
                else:
                    self._git(['add', '-A'], tmp)
                    self._git(commit, tmp)
                    self._git(['push', '-q', 'origin', self.branch], tmp)
                said = f'{self.name}: {msg} pushed'
            # What this place must hold now: every file of the channel exactly as committed (git blob), and the
            # rollout file gone once the release went to everyone.
            self.expected = {}
            for line in self._git(['ls-tree', '-r', 'HEAD', '--', channel], tmp).stdout.splitlines():
                meta, rel = line.split('	', 1)
                self.expected[rel] = meta.split()[2]
            if action == 'to_everyone':
                self.expected[f'{channel}/{ROLLOUT_FILE}'] = None
            return said

    def read_back(self):
        """Every expected file, as the place serves it now: the same git blob (or absent). One file list of the branch
        as the service holds it - no file is downloaded again."""
        tree = self.remote_tree()
        bad = []
        for rel, want in self.expected.items():
            got = tree.get(rel)
            if got != want:
                bad.append(f'{rel} ({"missing" if got is None else "different"})' if want else f'{rel} (still there)')
        if bad:
            raise Refused(f'{self.name} read back differently: ' + ', '.join(bad[:6]))
        return f'{self.name}: {len(self.expected)} file(s) read back exactly'

    def remote_tree(self):
        """{path: git blob sha} of every file on the branch, as the service answers now."""
        if self.remote.startswith('file://'):        # tests: a local bare repository stands in for the service
            out = run(['git', '--git-dir', self.remote[len('file://'):], 'ls-tree', '-r', self.branch]).stdout
            return {line.split('	', 1)[1]: line.split()[2] for line in out.splitlines()}
        branch = self._api(f'/repos/{self.repo}/branches/{urllib.parse.quote(self.branch)}')
        commit = branch.get('commit', {})
        sha = commit.get('sha') or commit.get('id')         # GitHub says sha, Codeberg (Forgejo) says id
        if not sha:
            raise Refused(f'{self.name} did not say which commit {self.branch} is')
        tree = self._api(f'/repos/{self.repo}/git/trees/{sha}?recursive=1&per_page=10000')
        if tree.get('truncated'):
            raise Refused(f'{self.name} answered with a shortened file list - it cannot be read back whole')
        return {e['path']: e['sha'] for e in tree.get('tree', []) if e.get('type') == 'blob'}

    def _api(self, path):
        headers = {'Accept': 'application/json', 'User-Agent': 'tagpulse-release-publisher'}
        if self.api_token:
            headers['Authorization'] = f'token {self.api_token}'
        try:
            with urllib.request.urlopen(urllib.request.Request(self.api + path, headers=headers), timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            raise Refused(f'{self.name} could not be read back: HTTP {e.code}')
        except urllib.error.URLError as e:
            raise Refused(f'{self.name} could not be read back: {e.reason}')


class S3Place:
    """Our download server's storage (Cloudflare R2), through the S3 API with AWS Signature V4."""

    def __init__(self, endpoint, bucket, prefix, key_id, secret, region, public_base):
        self.name = 'r2'
        self.endpoint, self.bucket, self.prefix = endpoint.rstrip('/'), bucket, prefix.strip('/')
        self.key_id, self.secret, self.region = key_id, secret, region
        self.public_base = public_base.rstrip('/')
        self.channel = 'stable'  # the feed folder of the release being published (set by publish)
        self.expected = {}       # key -> md5 hex (or None = must be absent)
        self.public = {}         # public address -> sha256 hex (or None = must answer 404)

    def _request(self, method, key='', body=b'', query=None, content_type=None):
        host = urllib.parse.urlparse(self.endpoint).netloc
        path = '/' + self.bucket + ('/' + urllib.parse.quote(key) if key else '')
        qs = '&'.join(f'{urllib.parse.quote(k, safe="")}={urllib.parse.quote(v, safe="")}' for k, v in sorted((query or {}).items()))
        now = datetime.datetime.now(datetime.timezone.utc)
        amz_date, date = now.strftime('%Y%m%dT%H%M%SZ'), now.strftime('%Y%m%d')
        payload_hash = hashlib.sha256(body).hexdigest()
        headers = {'host': host, 'x-amz-content-sha256': payload_hash, 'x-amz-date': amz_date}
        if content_type:
            headers['content-type'] = content_type
        signed = ';'.join(sorted(headers))
        canonical = '\n'.join([method, path, qs, ''.join(f'{k}:{headers[k]}\n' for k in sorted(headers)), signed, payload_hash])
        scope = f'{date}/{self.region}/s3/aws4_request'
        to_sign = '\n'.join(['AWS4-HMAC-SHA256', amz_date, scope, hashlib.sha256(canonical.encode()).hexdigest()])
        k = ('AWS4' + self.secret).encode()
        for part in (date, self.region, 's3', 'aws4_request'):
            k = hmac.new(k, part.encode(), hashlib.sha256).digest()
        sig = hmac.new(k, to_sign.encode(), hashlib.sha256).hexdigest()
        headers['Authorization'] = f'AWS4-HMAC-SHA256 Credential={self.key_id}/{scope}, SignedHeaders={signed}, Signature={sig}'
        req = urllib.request.Request(self.endpoint + path + (('?' + qs) if qs else ''), data=body if method == 'PUT' else None,
                                     method=method, headers={k: v for k, v in headers.items() if k != 'host'})
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read()

    def _key(self, rel):
        return f'{self.prefix}/{self.channel}/{rel}'

    def _put(self, rel, path, content_type):
        data = open(path, 'rb').read()
        code, _h, body = self._request('PUT', self._key(rel), data, content_type=content_type)
        if code != 200:
            raise Refused(f'r2 upload of {rel} failed: HTTP {code} {body[:200]!r}')
        self.expected[self._key(rel)] = hashlib.md5(data).hexdigest()

    def _delete(self, rel_key):
        code, _h, body = self._request('DELETE', rel_key)
        if code not in (200, 204, 404):
            raise Refused(f'r2 removal of {rel_key} failed: HTTP {code}')
        self.expected[rel_key] = None

    def _list(self, sub):
        keys, token = [], None
        while True:
            q = {'list-type': '2', 'prefix': self._key(sub)}
            if token:
                q['continuation-token'] = token
            code, _h, body = self._request('GET', '', query=q)
            if code != 200:
                raise Refused(f'r2 listing failed: HTTP {code}')
            text = body.decode()
            keys += re.findall(r'<Key>([^<]+)</Key>', text)
            m = re.search(r'<NextContinuationToken>([^<]+)</NextContinuationToken>', text)
            if not m:
                return keys
            token = m.group(1)

    def _get(self, rel, dest):
        code, _h, body = self._request('GET', self._key(rel))
        if code == 200:
            with open(dest, 'wb') as f:
                f.write(body)
        elif code != 404:
            raise Refused(f'r2 could not be read ({rel}): HTTP {code}')

    def publish(self, release_dir, version, action, previous_feed_version_check):
        self.expected, self.public = {}, {}
        self.channel = channel_of(version)
        with tempfile.TemporaryDirectory(prefix='rp-r2-') as tmp:
            self._get('manifest-v2.json', os.path.join(tmp, 'manifest-v2.json'))
            self._get(ROLLOUT_FILE, os.path.join(tmp, ROLLOUT_FILE))
            previous_feed_version_check(self.name, tmp)
        zip_name = f'tagpulse-{version}.zip'
        zip_path = os.path.join(release_dir, 'packages-v2', zip_name)
        if action == 'send_in_steps':
            self._put(f'packages-v2/{zip_name}', zip_path, 'application/zip')
            self._put(ROLLOUT_FILE, os.path.join(release_dir, 'manifest-v2.json'), 'application/json')
            self._public_check(ROLLOUT_FILE, os.path.join(release_dir, 'manifest-v2.json'))
            return f'r2: {zip_name} and {ROLLOUT_FILE} uploaded'
        self._put(f'packages-v2/{zip_name}', zip_path, 'application/zip')
        wanted = {self._key(f'packages-v2/{zip_name}')}
        for f in sorted(os.listdir(os.path.join(release_dir, 'packages'))):
            ct = 'application/zip' if f.endswith('.zip') else 'application/octet-stream'
            self._put(f'packages/{f}', os.path.join(release_dir, 'packages', f), ct)
            wanted.add(self._key(f'packages/{f}'))
        # The lists last: a PC that reads a new list finds every package it names already there.
        self._put('manifest.pb', os.path.join(release_dir, 'manifest.pb'), 'application/octet-stream')
        self._put('manifest.textproto', os.path.join(release_dir, 'manifest.textproto'), 'text/plain')
        self._put('manifest-v2.json', os.path.join(release_dir, 'manifest-v2.json'), 'application/json')
        self._public_check('manifest-v2.json', os.path.join(release_dir, 'manifest-v2.json'))
        if action == 'to_everyone':
            self._delete(self._key(ROLLOUT_FILE))
            self._public_check(ROLLOUT_FILE, None)
        removed = 0
        for sub in ('packages-v2/', 'packages/'):
            for k in self._list(sub):
                # setup-*.exe is never published here (as prepare_update_feed.ps1) and so never removed either.
                if k not in wanted and not os.path.basename(k).startswith('setup-'):
                    self._delete(k)
                    removed += 1
        return f'r2: release v{version} uploaded, {removed} old package(s) removed'

    def _public_check(self, rel, local_path):
        """Read back what a PC reads: the public address in front of the storage (dl.tagpulse.ai/feed/...)."""
        if self.public_base:
            self.public[f'{self.public_base}/{self.channel}/{rel}'] = sha256_file(local_path) if local_path else None

    def read_back(self):
        bad = []
        for key, want in self.expected.items():
            code, headers, _b = self._request('HEAD', key)
            etag = (headers.get('ETag') or headers.get('etag') or '').strip('"')
            if want is None and code != 404:
                bad.append(f'{key} (still there)')
            elif want is not None and (code != 200 or etag != want):
                bad.append(f'{key} ({"missing" if code == 404 else "different"})')
        for url, want in self.public.items():
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'tagpulse-release-publisher',
                                                                                 'Cache-Control': 'no-cache'}), timeout=60) as r:
                    got = hashlib.sha256(r.read()).hexdigest()
            except urllib.error.HTTPError as e:
                got = None if e.code == 404 else f'HTTP {e.code}'
            except urllib.error.URLError as e:
                got = f'unreachable ({e.reason})'
            if got != want:
                bad.append(f'{url} as a PC reads it ({"missing" if got is None else "still there" if want is None else got if got.startswith(("HTTP", "unreachable")) else "different"})')
        if bad:
            raise Refused('r2 read back differently: ' + ', '.join(b.replace(self.prefix + '/', '') for b in bad[:6]))
        return f'r2: {len(self.expected)} file(s) read back exactly' + (
            f', {len(self.public)} as a PC reads them' if self.public else '')


def places_from_keys(keys):
    """The three places, from the keys file. A place whose keys are missing is None (the pop-up shows it not ready)."""
    gh = cb = r2 = None
    if keys.get('GITHUB_TOKEN') or keys.get('GITHUB_REMOTE', '').startswith('file://'):
        repo = keys.get('GITHUB_REPO', 'gkal/tagpulse-updates')
        remote = keys.get('GITHUB_REMOTE') or f'https://x-access-token:{keys["GITHUB_TOKEN"]}@github.com/{repo}.git'
        gh = GitPlace('github', remote, keys.get('GITHUB_BRANCH', 'main'), False, 'https://api.github.com',
                      keys.get('GITHUB_TOKEN', ''), repo, True)
    if keys.get('CODEBERG_TOKEN') or keys.get('CODEBERG_REMOTE', '').startswith('file://'):
        repo = keys.get('CODEBERG_REPO', 'gkal/tagpulse-updates')
        remote = keys.get('CODEBERG_REMOTE') or f'https://gkal:{keys["CODEBERG_TOKEN"]}@codeberg.org/{repo}.git'
        cb = GitPlace('codeberg', remote, keys.get('CODEBERG_BRANCH', 'main'), True, 'https://codeberg.org/api/v1',
                      keys.get('CODEBERG_TOKEN', ''), repo, False)
    if all(keys.get(k) for k in ('R2_ENDPOINT', 'R2_BUCKET', 'R2_FEED_PREFIX', 'R2_ACCESS_KEY_ID', 'R2_SECRET_ACCESS_KEY')):
        r2 = S3Place(keys['R2_ENDPOINT'], keys['R2_BUCKET'], keys['R2_FEED_PREFIX'], keys['R2_ACCESS_KEY_ID'],
                     keys['R2_SECRET_ACCESS_KEY'], keys.get('R2_REGION', 'auto'), keys.get('R2_PUBLIC_BASE', ''))
    return {'github': gh, 'codeberg': cb, 'r2': r2}


# ---------------------------------------------------------------------------------------------------------------- run
def mail(subject, text):
    if not MAIL_ON:
        log(f'mail (off): {subject}')
        return
    key = ''
    if os.path.exists(MAIL_ENV):
        for line in open(MAIL_ENV, encoding='utf-8'):
            if line.startswith('RESEND_API_KEY='):
                key = line.split('=', 1)[1].strip().strip('"')
    if not key:
        log('mail: no RESEND_API_KEY - not sent')
        return
    body = json.dumps({'from': MAIL_FROM, 'to': [MAIL_TO], 'subject': subject, 'text': text}).encode()
    req = urllib.request.Request('https://api.resend.com/emails', data=body, method='POST',
                                 headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req, timeout=20).read()
    except Exception as e:          # a lost e-mail must never stop a release - it is logged
        log(f'mail failed: {e}')


def feed_guard(release_dir, version, action, open_rollout):
    """What each place holds now must allow this request: the version everyone gets is older (or, for a repeated
    'give to everyone', this same one), and a release in steps of this version, if one is there, is this package.
    A release file of ANOTHER version is replaced only when that version's steps are over (open_rollout = the version
    of the release in steps that is still open, '' for none): a withdrawn release leaves its file behind, harmless to
    the PCs (no step lets them in) - the next release's file takes its place."""
    ours = json.load(open(os.path.join(release_dir, 'manifest-v2.json'), encoding='utf-8-sig')).get('sha256')

    def check(place_name, channel_dir):
        mf = os.path.join(channel_dir, 'manifest-v2.json')
        if os.path.exists(mf):
            current = json.load(open(mf, encoding='utf-8-sig')).get('version', '')
            if current and version_key(current) >= version_key(version) and not (action in ('to_everyone', 'to_beta')
                                                                                  and current == version):
                raise Refused(f'{place_name} already gives everyone {current} - {version} is not newer')
        rf = os.path.join(channel_dir, ROLLOUT_FILE)
        if os.path.exists(rf):
            other = json.load(open(rf, encoding='utf-8-sig'))
            if other.get('version') == version and other.get('sha256') != ours:
                raise Refused(f'{place_name} already carries {version} in steps with ANOTHER package')
            if action == 'send_in_steps' and other.get('version') != version and other.get('version') == open_rollout:
                raise Refused(f"{open_rollout} is being sent in steps right now - finish it before sending {version}")
    return check


def cmd_run():
    keys = read_keys()
    runner = Runner(keys)
    up = runner.ready()
    # The places and the checker live in the runner now: one answer for all four (the pop-up's "ready" line).
    ready = {'github': up, 'codeberg': up, 'r2': up, 'checker': up}
    db(f'SELECT private.release_job_heartbeat({sql_text(JOB_VERSION)}, {sql_text(json.dumps(ready))}::jsonb);')
    req = db_json('SELECT private.release_job_take();')
    if not req:
        return
    rid, version, action, who = req['id'], req['version'], req['action'], req['requested_by']
    what = {'send_in_steps': 'send in steps', 'to_everyone': 'give to everyone',
            'to_beta': 'send to the beta PCs'}.get(action, action)
    log(f'request {rid}: {who} asked to {what} {version}')
    mail(f'TagPulse release {version}: {who} pressed "{what}"',
         f'{who} pressed "{what}" for TagPulse {version} at {req["requested_at"]}.\n'
         f'Our runner at GitHub is carrying it out now; the dashboard shows the result per place.')
    ok, results = True, []
    try:
        if not up:
            raise Refused('not ready: the runner at GitHub cannot be reached with the host\'s key, or its workflow or '
                          'program is not in the feed repository')
        cand = req['candidate']
        if not cand['check_ok']:
            raise Refused(f'{version} did not pass the signature check: {cand["check_says"]}')
        upload, release_sha = parse_staged(cand)
        # The request must fit the release's channel (189 refuses the others before they are queued; checked again
        # here, as a request put straight into the table would not pass through it).
        if (action == 'to_beta') != (channel_of(version) == 'beta'):
            raise Refused(f'{version} is a {channel_of(version)} release - "{what}" is not for it')
        open_rollout = db("SELECT coalesce((SELECT version FROM public.release_rollouts "
                          "WHERE channel = 'stable' AND finished_at IS NULL LIMIT 1), '');")
        result = runner.order(action, version, upload, release_sha, open_rollout)
        places = result.get('places') if isinstance(result.get('places'), dict) else {}
        if not places:
            raise Refused(str(result.get('says') or 'the runner said nothing per place'))
        for name in ('github', 'codeberg', 'r2'):
            p = places.get(name) if isinstance(places.get(name), dict) else {}
            state, said = str(p.get('state', 'not started')), str(p.get('says', 'the runner did not say'))[:1500]
            if state == 'ok':
                try:
                    said = f'{said}; {read_back_here(keys, cand, version, action, name)}'
                except Refused as e:
                    state, said = 'failed', f'{said}; {e}'
            elif state not in ('failed', 'not started'):
                state = 'failed'        # 'uploaded' and not read back: not confirmed
            ok = ok and state == 'ok'
            db(f'SELECT private.release_job_place({rid}, {sql_text(name)}, {sql_text(state)}, {sql_text(said)});')
            results.append(f'{name}: {"OK" if state == "ok" else state.upper()} - {said}')
        says = ('all three places confirmed' if ok else 'not every place confirmed') + ' - ' + '; '.join(results)
    except Refused as e:
        ok, says = False, str(e)
    db(f'SELECT private.release_job_finish({rid}, {"true" if ok else "false"}, {sql_text(says)});')
    log(f'request {rid}: {"DONE" if ok else "FAILED"} - {says}')
    mail(f'TagPulse release {version}: {"done" if ok else "FAILED"} ({what})', says)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ('register', 'run', 'ready', 'runner', 'make-pinned-ca'):
        print(__doc__)
        return 2
    try:
        if sys.argv[1] == 'make-pinned-ca':
            make_pinned_ca()
            return 0
        if sys.argv[1] == 'ready':
            if Runner(read_keys()).ready():
                print(f'ready: {RUNNER_WORKFLOW} and {RUNNER_PROGRAM} are in {RUNNER_REPO} and the key reads them')
                return 0
            print(f'NOT ready: {RUNNER_REPO} cannot be read with this host\'s GITHUB_TOKEN, or {RUNNER_WORKFLOW} / '
                  f'{RUNNER_PROGRAM} is not in it yet')
            return 1
        if sys.argv[1] == 'runner':
            cmd_runner()            # always 0: the result file says how it went
            return 0
        with open(LOCK_FILE, 'w') as lock:
            if sys.argv[1] == 'run':
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    return 0            # the previous minute's run is still publishing
                cmd_run()
            else:
                fcntl.flock(lock, fcntl.LOCK_EX)   # a registration waits until a publish in progress has finished
                cmd_register(sys.stdin.read())
        return 0
    except Refused as e:
        print(f'REFUSED: {e}')
        log(f'REFUSED: {e}')
        return 1


if __name__ == '__main__':
    sys.exit(main())
