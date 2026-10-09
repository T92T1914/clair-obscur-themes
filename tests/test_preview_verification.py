import hashlib
from html.parser import HTMLParser
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

import verify_preview as verifier


ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def manifest_document(files):
    return {
        'schema_version': 2,
        'generator': 'clair-obscur-preview',
        'source': {'revision': None, 'state': 'unavailable', 'archive': 'source.zip',
                   'sha256': digest(files['source.zip'])},
        'release': {
            'version': '0.1.1',
            'source_url': verifier.RELEASE_PREFIX + 'v0.1.1/source.zip',
            'checksums_url': verifier.RELEASE_PREFIX + 'v0.1.1/release-SHA256SUMS',
        },
        'distribution': {'kind': 'portable-kit'},
        'files': {name: digest(data) for name, data in files.items()},
    }


def encoded(document):
    return (json.dumps(document, sort_keys=True) + '\n').encode('utf-8')


class BinaryOutput:
    def __init__(self):
        self.buffer = io.BytesIO()


class KitFixture(unittest.TestCase):
    def setUp(self):
        self.temp_root = Path(tempfile.gettempdir()).resolve()
        self.temporary = tempfile.TemporaryDirectory(prefix='themes-verification-')
        self.base = Path(self.temporary.name).resolve()
        self.assertTrue(self.base.is_relative_to(self.temp_root))
        self.assertNotEqual(self.base, self.temp_root)
        self.addCleanup(self.cleanup_owned)
        self.kit = self.base / 'kit'
        self.kit.mkdir()
        # Opaque source bytes deliberately are not a ZIP. Verification never
        # interprets the contents of declared members.
        self.files = {name: f'Included {name}\n'.encode() for name in verifier.CORE_FILES}
        self.files['source.zip'] = b'opaque source archive\x00not executable\n'
        self.document = manifest_document(self.files)
        for name, data in self.files.items():
            path = self.kit / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.write_manifest()

    def cleanup_owned(self):
        target = Path(self.temporary.name).absolute()
        if target == self.temp_root or not target.is_relative_to(self.temp_root):
            raise AssertionError('Temporary cleanup escaped its designated root')
        if target.is_symlink() or target.resolve() != self.base:
            raise AssertionError('Temporary cleanup root changed')
        self.temporary.cleanup()

    def write_manifest(self):
        (self.kit / 'site-manifest.json').write_bytes(encoded(self.document))

    def remove_owned_directory(self, path):
        target = path.resolve()
        if path.is_symlink() or target == self.base or not target.is_relative_to(self.base):
            raise AssertionError('Fixture deletion escaped its owned directory')
        shutil.rmtree(path)

    def snapshot(self, root=None):
        root = self.kit if root is None else root
        return {path.relative_to(root).as_posix(): (
            path.read_bytes(), path.stat().st_mtime_ns, path.stat().st_ctime_ns,
        ) for path in root.rglob('*') if path.is_file()}

    def assert_refused(self, status=2, message=None):
        output = BinaryOutput()
        errors = io.StringIO()
        with patch.object(verifier.sys, 'stdout', output), patch.object(verifier.sys, 'stderr', errors):
            self.assertEqual(verifier.main([str(self.kit)]), status)
        self.assertEqual(output.buffer.getvalue(), b'')
        if message is not None:
            self.assertIn(message, errors.getvalue())

    def command(self, *arguments, script=None):
        entry = ROOT / 'verify_preview.py' if script is None else script
        return subprocess.run(
            [sys.executable, '-I', '-S', '-B', str(entry), *arguments],
            cwd=self.base, capture_output=True, timeout=15,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )


class VerificationComparisonTests(KitFixture):
    def test_pristine_and_relocated_legacy_kit_preserve_inputs(self):
        before = self.snapshot()
        status, report = verifier.verify(self.kit)
        self.assertEqual(status, 0)
        self.assertTrue(report.startswith(b'Portable kit verification: consistent\n'))
        self.assertIn(b'Expected regular files: 11\nExpected directories: 1\n', report)
        self.assertIn(f'Observed manifest SHA-256: {digest(encoded(self.document))}\n'.encode(), report)
        self.assertIn(b'Stored source revision: null\nStored source state: unavailable\n', report)
        self.assertTrue(report.endswith(verifier.DISCLOSURE.encode() + b'\n'))
        self.assertEqual(before, self.snapshot())
        moved = self.base / 'moved kit'
        self.kit.rename(moved)
        self.assertEqual(verifier.verify(moved), (status, report))
        self.assertEqual(before, self.snapshot(moved))

    def test_missing_changed_extra_and_empty_directory_have_exact_sorted_rows(self):
        (self.kit / 'preview.js').unlink()
        (self.kit / 'tokens.css').write_bytes(b'changed tokens\n')
        (self.kit / 'z.txt').write_bytes(b'preserved extra')
        (self.kit / 'a.txt').write_bytes(b'preserved extra')
        (self.kit / 'empty').mkdir()
        before = self.snapshot()
        status, report = verifier.verify(self.kit)
        self.assertEqual(status, 1)
        rows = report.decode().splitlines()[6:-1]
        self.assertEqual(rows, [
            'missing FILE "preview.js"',
            f'changed FILE "tokens.css" expected={digest(self.files["tokens.css"])} '
            f'observed={digest(b"changed tokens" + bytes([10]))}',
            'extra FILE "a.txt"', 'extra FILE "z.txt"', 'extra DIR "empty"',
        ])
        self.assertEqual(before, self.snapshot())

    def test_type_conflicts_report_missing_and_extra_without_reading_extras(self):
        self.remove_owned_directory(self.kit / 'downloads')
        (self.kit / 'downloads').write_bytes(b'never read this replacement')
        (self.kit / 'preview.js').unlink()
        (self.kit / 'preview.js').mkdir()
        original = os.open

        def guarded(path, *args, **kwargs):
            self.assertNotEqual(Path(path), self.kit / 'downloads')
            return original(path, *args, **kwargs)

        with patch.object(verifier.os, 'open', side_effect=guarded):
            status, report = verifier.verify(self.kit)
        self.assertEqual(status, 1)
        self.assertEqual(report.decode().splitlines()[6:-1], [
            'missing FILE "downloads/SHA256SUMS"',
            'missing FILE "downloads/artifact-manifest.json"',
            'missing FILE "preview.js"', 'missing DIR "downloads"',
            'extra FILE "downloads"', 'extra DIR "preview.js"',
        ])

    def test_stable_case_rename_keeps_literal_comparison(self):
        (self.kit / 'LICENSE').rename(self.kit / 'license')
        status, report = verifier.verify(self.kit)
        self.assertEqual(status, 1)
        self.assertEqual(report.decode().splitlines()[6:-1], [
            'missing FILE "LICENSE"', 'extra FILE "license"',
        ])

    def test_selected_files_are_opaque_and_no_process_network_or_generator_runs(self):
        import urllib.request
        (self.kit / 'untrusted.py').write_bytes(b'raise RuntimeError("do not execute")\n')
        original = os.open

        def guarded(path, *args, **kwargs):
            self.assertNotEqual(Path(path).name, 'untrusted.py')
            return original(path, *args, **kwargs)

        with patch('subprocess.run', side_effect=AssertionError('subprocess')), \
                patch('socket.create_connection', side_effect=AssertionError('network')), \
                patch.object(urllib.request, 'urlopen', side_effect=AssertionError('network')), \
                patch.object(verifier.os, 'open', side_effect=guarded):
            status, report = verifier.verify(self.kit)
        self.assertEqual(status, 1)
        self.assertIn(b'extra FILE "untrusted.py"', report)

    def test_stored_clean_and_modified_revision_claims_are_not_git_reads(self):
        for state, revision in (('clean', 'a' * 40), ('modified', 'b' * 64)):
            with self.subTest(state=state):
                self.document['source'].update(state=state, revision=revision)
                self.write_manifest()
                status, report = verifier.verify(self.kit)
                self.assertEqual(status, 0)
                self.assertIn(f'Stored source revision: {revision}\n'.encode(), report)
                self.assertIn(f'Stored source state: {state}\n'.encode(), report)


class ManifestAdmissionTests(KitFixture):
    def test_invalid_encoding_json_duplicates_constants_and_numeric_conversion(self):
        valid = encoded(self.document)
        cases = [b'\xff', b'\xef\xbb\xbf' + valid, b'{',
                 valid.replace(b'"schema_version": 2', b'"schema_version": NaN'),
                 valid.replace(b'"schema_version": 2', b'"schema_version": ' + b'9' * 5000),
                 valid.replace(b'"schema_version": 2', b'"schema_version": 2, "schema_version": 2'),
                 valid.replace(b'"kind": "portable-kit"', b'"kind": "portable-kit", "kind": "portable-kit"'),
                 b'[' * 2000 + b'0' + b']' * 2000]
        for data in cases:
            with self.subTest(prefix=data[:60]):
                (self.kit / 'site-manifest.json').write_bytes(data)
                self.assert_refused()

    def test_exact_schema_type_identity_release_and_distribution_refusals(self):
        mutations = [
            ('schema bool', lambda doc: doc.update(schema_version=True)),
            ('schema float', lambda doc: doc.update(schema_version=2.0)),
            ('extra root key', lambda doc: doc.update(extra='unsupported')),
            ('wrong generator', lambda doc: doc.update(generator='other')),
            ('published', lambda doc: doc.update(distribution={'kind': 'published-preview'})),
            ('extra distribution', lambda doc: doc['distribution'].update(extra=1)),
            ('missing source key', lambda doc: doc['source'].pop('archive')),
            ('revision pair', lambda doc: doc['source'].update(revision='a' * 40)),
            ('revision uppercase', lambda doc: doc['source'].update(revision='A' * 40, state='clean')),
            ('source hash', lambda doc: doc['source'].update(sha256='0' * 64)),
            ('source archive', lambda doc: doc['source'].update(archive='other.zip')),
            ('version', lambda doc: doc['release'].update(version='1.2')),
            ('version nonascii', lambda doc: doc['release'].update(version='１.2.3')),
            ('wrong release URL', lambda doc: doc['release'].update(source_url='https://example.invalid/source.zip')),
            ('uppercase digest', lambda doc: doc['files'].update(LICENSE='A' * 64)),
            ('bool digest', lambda doc: doc['files'].update(LICENSE=True)),
            ('missing core', lambda doc: doc['files'].pop('index.html')),
            ('self hash', lambda doc: doc['files'].update({'site-manifest.json': '0' * 64})),
            ('verifier alone', lambda doc: doc['files'].update({'verify_preview.py': '0' * 64})),
            ('guide alone', lambda doc: doc['files'].update({'portable-verification.md': '0' * 64})),
        ]
        for label, mutation in mutations:
            with self.subTest(label=label):
                self.document = manifest_document(self.files)
                mutation(self.document)
                self.write_manifest()
                self.assert_refused()

    def test_unsafe_collision_and_prefix_paths_include_unhashed_manifest(self):
        for name in ('../file', '/file', 'C:/file', 'a\\b', 'a:b', 'a//b', 'a/./b',
                     'name.', 'CON.txt', 'aux', 'Lpt9.log', 'a/COM1.data', 'café',
                     'a\x85b', 'a' * 241, 'a/b/c/d/e/f/g/h/i', 'Site-manifest.json',
                     'INDEX.html', 'index.html/child', 'downloads'):
            with self.subTest(name=name):
                self.document = manifest_document(self.files)
                self.document['files'][name] = '0' * 64
                self.write_manifest()
                self.assert_refused()

    def test_manifest_declared_and_expected_combined_caps(self):
        (self.kit / 'site-manifest.json').write_bytes(b' ' * 65_537)
        self.assert_refused(message='File byte limit')
        self.document = manifest_document(self.files)
        for number in range(119):
            self.document['files'][f'file{number}.txt'] = '0' * 64
        self.write_manifest()
        self.assert_refused(message='declared file count')
        self.document = manifest_document(self.files)
        for number in range(40):
            self.document['files'][f'a{number}/b/c/d/e/f/g/file'] = '0' * 64
        self.write_manifest()
        self.assert_refused(message='Combined inventory')

    def test_actual_inventory_depth_and_unsafe_extra_are_refused_before_reads(self):
        for number in range(245):
            (self.kit / f'extra{number}.txt').touch()
        with patch.object(verifier, '_read', side_effect=AssertionError('content read')):
            with self.assertRaisesRegex(verifier.VerificationInputError, 'Actual inventory'):
                verifier.verify(self.kit)
        for number in range(245):
            (self.kit / f'extra{number}.txt').unlink()
        nested = self.kit / 'a/b/c/d/e/f/g/h/i'
        nested.mkdir(parents=True)
        self.assert_refused(message='depth')
        self.remove_owned_directory(self.kit / 'a')
        (self.kit / 'bad name.txt').touch()
        self.assert_refused(message='Unsupported relative path')

    def test_actual_case_collision_is_refused_when_filesystem_supports_it(self):
        extra = self.kit / 'INDEX.html'
        if extra.exists():
            self.skipTest('Filesystem does not support distinct case-colliding names')
        extra.write_bytes(b'extra case spelling')
        self.assert_refused(message='Case-insensitive inventory paths collide')

    def test_root_missing_manifest_type_empty_and_root_selection(self):
        with self.assertRaises(verifier.VerificationInputError):
            verifier.verify('')
        with self.assertRaises(verifier.VerificationInputError):
            verifier.verify(Path(self.kit.anchor))
        with self.assertRaises(verifier.VerificationInputError):
            verifier.verify(self.base / 'absent')
        with self.assertRaises(verifier.VerificationInputError):
            verifier.verify(self.kit / 'LICENSE')
        (self.kit / 'site-manifest.json').unlink()
        self.assert_refused(message='Missing regular site-manifest.json')
        (self.kit / 'site-manifest.json').mkdir()
        self.assert_refused(message='Missing regular site-manifest.json')

    def test_links_and_linked_ancestor_are_refused_before_content(self):
        linked = self.base / 'linked kit'
        try:
            linked.symlink_to(self.kit, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f'Symlink fixture unavailable: {error}')
        with patch.object(verifier, '_read', side_effect=AssertionError('content read')):
            for selected in (linked, linked / 'downloads', linked / '..' / 'kit'):
                with self.subTest(selected=str(selected)):
                    with self.assertRaisesRegex(verifier.VerificationInputError, 'Linked'):
                        verifier.verify(selected)
        linked.unlink()
        (self.kit / 'extra-link').symlink_to(self.kit / 'LICENSE')
        self.assert_refused(message='Linked')

    def test_reparse_and_nonregular_metadata_are_refused(self):
        info = (self.kit / 'LICENSE').stat()
        values = {name: getattr(info, name) for name in (
            'st_dev', 'st_ino', 'st_mode', 'st_size', 'st_mtime_ns', 'st_ctime_ns',
        )}
        values['st_file_attributes'] = 0x400
        with self.assertRaisesRegex(verifier.VerificationInputError, 'reparse'):
            verifier._observation(SimpleNamespace(**values))
        values.update(st_file_attributes=0, st_mode=stat.S_IFIFO)
        with self.assertRaisesRegex(verifier.VerificationInputError, 'Nonregular'):
            verifier._observation(SimpleNamespace(**values))


class ReadObservationTests(KitFixture):
    def test_inventory_uses_fresh_path_identity_not_direntry_stat(self):
        original = os.scandir

        def deny_cached_stat(*args, **kwargs):
            raise AssertionError('DirEntry.stat cannot provide admitted identity')

        class Listing:
            def __init__(self, path):
                self.entries = original(path)

            def __enter__(self):
                return (SimpleNamespace(name=entry.name, stat=deny_cached_stat)
                        for entry in self.entries.__enter__())

            def __exit__(self, *arguments):
                return self.entries.__exit__(*arguments)

        with patch.object(verifier.os, 'scandir', Listing):
            self.assertEqual(verifier.verify(self.kit)[0], 0)

    def test_file_size_refusal_precedes_opening_large_member(self):
        with (self.kit / 'LICENSE').open('wb') as stream:
            stream.truncate(8_388_609)
        original = os.open

        def guarded(path, *args, **kwargs):
            self.assertNotEqual(Path(path), self.kit / 'LICENSE')
            return original(path, *args, **kwargs)

        with patch.object(verifier.os, 'open', side_effect=guarded):
            self.assert_refused(message='File byte limit')

    def test_aggregate_reserves_final_manifest_and_every_read_is_charged(self):
        observed = []
        original = verifier.ReadBudget.read

        def track(budget, stream, count, reserve):
            self.assertLessEqual(count, 65_536)
            self.assertLessEqual(count, verifier.MAX_READ_BYTES - budget.used - reserve)
            before = budget.used
            data = original(budget, stream, count, reserve)
            self.assertEqual(budget.used, before + len(data))
            observed.append((len(data), reserve, budget.used))
            return data

        with patch.object(verifier.ReadBudget, 'read', track):
            self.assertEqual(verifier.verify(self.kit)[0], 0)
        self.assertEqual(observed[-1][2],
                         2 * len(encoded(self.document)) + sum(map(len, self.files.values())))
        self.assertTrue(any(reserve == len(encoded(self.document)) + 1 for _, reserve, _ in observed))
        budget = 2 * len(encoded(self.document)) + len(self.files['LICENSE'])
        with patch.object(verifier, 'MAX_READ_BYTES', budget), \
                patch.object(verifier.ReadBudget, 'read', track):
            self.assert_refused(message='Aggregate read limit')

    def test_permission_disappearance_and_opened_identity_are_unverified(self):
        original = os.open
        for error in (PermissionError('read denied'), FileNotFoundError('disappeared')):
            def fail(path, *args, **kwargs):
                if Path(path) == self.kit / 'LICENSE':
                    raise error
                return original(path, *args, **kwargs)
            with self.subTest(error=type(error).__name__), patch.object(verifier.os, 'open', side_effect=fail):
                self.assert_refused(3, 'Cannot read stable file')
        swapped = False

        def replace_before_open(path, *args, **kwargs):
            nonlocal swapped
            if Path(path) == self.kit / 'LICENSE' and not swapped:
                replacement = self.base / 'replacement'
                replacement.write_bytes(self.files['LICENSE'])
                os.replace(replacement, path)
                swapped = True
            return original(path, *args, **kwargs)

        with patch.object(verifier.os, 'open', side_effect=replace_before_open):
            self.assert_refused(3)
        self.assertTrue(swapped)

    def test_growth_sentinel_is_charged_and_refuses_partial_verdict(self):
        original = verifier.ReadBudget.read
        grew = False

        def grow(budget, stream, count, reserve):
            nonlocal grew
            data = original(budget, stream, count, reserve)
            if data == self.files['LICENSE'] and not grew:
                with (self.kit / 'LICENSE').open('ab') as writer:
                    writer.write(b'x')
                grew = True
            return data

        with patch.object(verifier.ReadBudget, 'read', grow):
            self.assert_refused(3)
        self.assertTrue(grew)

    def test_final_handle_becoming_unsupported_is_unverified_not_invalid_input(self):
        original_open, original_fstat = os.open, os.fstat
        for label in ('reparse', 'nonregular'):
            target_descriptor = None
            target_observations = 0

            def track_open(path, *args, **kwargs):
                nonlocal target_descriptor
                descriptor = original_open(path, *args, **kwargs)
                if Path(path) == self.kit / 'LICENSE':
                    target_descriptor = descriptor
                return descriptor

            def changed_final(descriptor):
                nonlocal target_observations
                info = original_fstat(descriptor)
                if descriptor == target_descriptor:
                    target_observations += 1
                    if target_observations == 2:
                        values = {name: getattr(info, name) for name in (
                            'st_dev', 'st_ino', 'st_mode', 'st_size',
                            'st_mtime_ns', 'st_ctime_ns',
                        )}
                        values['st_file_attributes'] = getattr(info, 'st_file_attributes', 0)
                        if label == 'reparse':
                            values['st_file_attributes'] |= 0x400
                        else:
                            values['st_mode'] = stat.S_IFIFO
                        return SimpleNamespace(**values)
                return info

            with self.subTest(label=label), \
                    patch.object(verifier.os, 'open', side_effect=track_open), \
                    patch.object(verifier.os, 'fstat', side_effect=changed_final):
                self.assert_refused(3, 'Cannot read stable file')
            self.assertEqual(target_observations, 2)

    def test_admitted_pending_directory_becoming_unsupported_is_unverified(self):
        original = verifier._lstat
        observations = 0

        def changed_pending(path):
            nonlocal observations
            if path == self.kit / 'downloads':
                observations += 1
                if observations == 2:
                    raise verifier.VerificationInputError('Observed new reparse metadata')
            return original(path)

        with patch.object(verifier, '_lstat', side_effect=changed_pending):
            self.assert_refused(3, 'Directory changed during inventory')
        self.assertEqual(observations, 2)

    def test_second_inventory_change_and_manifest_recheck_are_unverified(self):
        original = verifier.inventory
        calls = 0

        def change_inventory(root):
            nonlocal calls
            calls += 1
            if calls == 2:
                (self.kit / 'new.txt').write_bytes(b'intervening file')
            return original(root)

        with patch.object(verifier, 'inventory', side_effect=change_inventory):
            self.assert_refused(3, 'Inventory changed')
        (self.kit / 'new.txt').unlink()
        original_read = verifier._read
        manifest_reads = 0

        def changed_final_manifest(root, name, *args, **kwargs):
            nonlocal manifest_reads
            value = original_read(root, name, *args, **kwargs)
            if name == 'site-manifest.json':
                manifest_reads += 1
                if manifest_reads == 2:
                    return digest(value[1] + b' '), value[1] + b' '
            return value

        with patch.object(verifier, '_read', side_effect=changed_final_manifest):
            self.assert_refused(3, 'Manifest changed')
        self.assertEqual(manifest_reads, 2)

    def test_injected_inventory_read_failure_and_report_cap_have_empty_stdout(self):
        with patch.object(verifier.os, 'scandir', side_effect=PermissionError('denied')):
            self.assert_refused(3, 'inventory')
        with patch.object(verifier, 'MAX_REPORT_BYTES', 10):
            self.assert_refused(message='report byte limit')


class CommandTests(KitFixture):
    def test_actual_isolated_copied_command_has_exact_lf_and_no_bytecode(self):
        copied = self.base / 'copied verifier.py'
        copied.write_bytes((ROOT / 'verify_preview.py').read_bytes())
        before = self.snapshot()
        result = self.command(str(self.kit), script=copied)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, verifier.verify(self.kit)[1])
        self.assertEqual(result.stderr, b'')
        self.assertTrue(result.stdout.endswith(b'\n'))
        self.assertFalse(result.stdout.endswith(b'\n\n'))
        self.assertNotIn(b'\r\n', result.stdout)
        self.assertEqual(before, self.snapshot())
        self.assertFalse(list(self.base.rglob('__pycache__')))
        (self.kit / 'preview.js').unlink()
        missing = self.command(str(self.kit), script=copied)
        self.assertEqual(missing.returncode, 1, missing.stderr)
        self.assertIn(b'missing FILE "preview.js"\n', missing.stdout)
        invalid = self.command('', script=copied)
        self.assertEqual(invalid.returncode, 2)
        self.assertEqual(invalid.stdout, b'')

    def test_help_and_misuse_do_not_start_verification(self):
        with patch.object(verifier, 'verify', side_effect=AssertionError('verification read')):
            for arguments, status in ((['--help'], 0), ([], 2), (['a', 'b'], 2)):
                with self.subTest(arguments=arguments), patch.object(verifier.sys, 'stdout', io.StringIO()), \
                        patch.object(verifier.sys, 'stderr', io.StringIO()):
                    with self.assertRaises(SystemExit) as raised:
                        verifier.main(arguments)
                    self.assertEqual(raised.exception.code, status)
        result = self.command('--help')
        self.assertEqual(result.returncode, 0)
        self.assertIn(b'usage:', result.stdout)
        self.assertNotIn(b'Portable kit verification: consistent', result.stdout)

    def test_actual_buffered_flush_refusal_preserves_exit_three_not_120(self):
        entry = ROOT / 'verify_preview.py'
        bootstrap = '''import io, runpy, sys
class Refuse(io.RawIOBase):
    def writable(self):
        return True
    def write(self, data):
        raise OSError('deliberate buffered flush refusal')
sys.stdout = io.TextIOWrapper(io.BufferedWriter(Refuse(), 16384), encoding='ascii')
sys.argv = [sys.argv[1], sys.argv[2]]
runpy.run_path(sys.argv[0], run_name='__main__')
'''
        result = subprocess.run(
            [sys.executable, '-I', '-S', '-B', '-c', bootstrap, str(entry), str(self.kit)],
            cwd=self.base, capture_output=True, timeout=15,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertEqual(result.stdout, b'')
        self.assertIn(b'output failed', result.stderr)
        self.assertNotIn(b'Traceback', result.stderr)
        self.assertNotIn(b'Exception ignored', result.stderr)

    def test_interruption_does_not_emit_completed_verdict(self):
        with patch.object(verifier, 'verify', side_effect=KeyboardInterrupt()):
            self.assert_refused(130, 'interrupted')


class ProducerInclusionTests(KitFixture):
    def test_one_capture_drives_public_kit_source_archive_and_deterministic_hashes(self):
        from preview import PORTABLE_ARCHIVE, PORTABLE_CHECKSUMS, preview_files, source_files
        from themeforge.build import build_release

        source = self.base / 'source'
        for name, data in source_files(ROOT).items():
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        captured = source_files(source)
        artifacts = self.base / 'artifacts'
        build_release(source / 'tokens.json', artifacts)
        native_before = {path.relative_to(artifacts).as_posix(): path.read_bytes()
                         for path in artifacts.rglob('*') if path.is_file()}

        def edit_after_capture(root):
            self.assertEqual(root, source)
            (source / 'verify_preview.py').write_bytes(b'later live entry\n')
            (source / 'docs/portable-verification.md').write_bytes(b'later live guide\n')
            return captured

        with patch('preview.source_files', side_effect=edit_after_capture):
            public = preview_files(source, artifacts)
            self.assertEqual(public, preview_files(source, artifacts))
        self.assertEqual(public['verify_preview.py'], captured['verify_preview.py'])
        self.assertEqual(public['portable-verification.md'], captured['docs/portable-verification.md'])
        self.assertNotEqual(public['verify_preview.py'], (source / 'verify_preview.py').read_bytes())
        published = json.loads(public['site-manifest.json'])
        self.assertNotIn('site-manifest.json', published['files'])
        self.assertEqual(set(published['files']), set(public) - {'site-manifest.json'})
        with zipfile.ZipFile(io.BytesIO(public[PORTABLE_ARCHIVE])) as archive:
            names = archive.namelist()
            self.assertEqual(len(names), len(set(names)))
            members = {name: archive.read(name) for name in names}
        portable = json.loads(members['site-manifest.json'])
        self.assertEqual(set(portable['files']), set(members) - {'site-manifest.json'})
        self.assertNotIn(PORTABLE_ARCHIVE, members)
        self.assertNotIn(PORTABLE_CHECKSUMS, members)
        for name in ('verify_preview.py', 'portable-verification.md'):
            self.assertEqual(members[name], public[name])
        for outputs, manifest in ((public, published), (members, portable)):
            for name, expected in manifest['files'].items():
                self.assertEqual(digest(outputs[name]), expected)
            page = outputs['index.html']
            self.assertIn(b'href="portable-verification.md"', page)
            self.assertIn(b'Python', page)

        class DeliveryCode(HTMLParser):
            def __init__(self):
                super().__init__()
                self.delivery = False
                self.current = None
                self.breaks = []
                self.codes = []

            def handle_starttag(self, tag, attrs):
                if tag == 'p' and dict(attrs).get('id') == 'portable-delivery':
                    self.delivery = True
                elif tag == 'code' and self.delivery:
                    self.current = []
                    self.breaks = []
                elif tag == 'wbr' and self.current is not None:
                    self.breaks.append(sum(map(len, self.current)))

            def handle_data(self, data):
                if self.current is not None:
                    self.current.append(data)

            def handle_endtag(self, tag):
                if tag == 'code' and self.current is not None:
                    self.codes.append((''.join(self.current), self.breaks))
                    self.current = None
                elif tag == 'p':
                    self.delivery = False

        for outputs, expected_text in (
            (public, 'verify_preview.py'),
            (members, 'python -I -S -B "verify_preview.py" "."'),
        ):
            parsed = DeliveryCode()
            parsed.feed(outputs['index.html'].decode('utf-8'))
            selected = [(text, breaks) for text, breaks in parsed.codes if text == expected_text]
            self.assertEqual(len(selected), 1)
            text, breaks = selected[0]
            self.assertIn(text.index('verify_') + len('verify_'), breaks)
            self.assertIn(text.index('preview.') + len('preview.'), breaks)
        with zipfile.ZipFile(io.BytesIO(public['source.zip'])) as archive:
            self.assertEqual(archive.read('verify_preview.py'), captured['verify_preview.py'])
            self.assertEqual(archive.read('docs/portable-verification.md'),
                             captured['docs/portable-verification.md'])
        manifest = json.loads(native_before['artifact-manifest.json'])
        packages = {item['path'] for item in manifest['downloads']}
        self.assertEqual(len(packages), 13)
        for path in packages:
            self.assertEqual(public['downloads/' + path], native_before[path])
            self.assertEqual(members['downloads/' + path], native_before[path])
        self.assertEqual(public['downloads/artifact-manifest.json'], native_before['artifact-manifest.json'])
        self.assertEqual(native_before, {path.relative_to(artifacts).as_posix(): path.read_bytes()
                                         for path in artifacts.rglob('*') if path.is_file()})
        extracted = self.base / 'extracted kit'
        for name, data in members.items():
            path = extracted / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.assertEqual(verifier.verify(extracted)[0], 0)


if __name__ == '__main__':
    unittest.main()
