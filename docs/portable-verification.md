# Verify an extracted portable preview

The preview works offline by opening `index.html`. Python is optional. Use the
included verifier when you want to check whether a copied or extracted directory
still matches its included `site-manifest.json` and see named discrepancies.

## Run the check

Install or select Python 3.11 or later. No themeforge package, browser automation,
Git checkout or third-party dependency is needed. Keep the complete extracted kit
together, including the verifier and manifest. From its directory, run:

```text
python -I -S -B "verify_preview.py" "."
```

You can also select another extracted copy. Quote paths that contain spaces:

```text
python -I -S -B "path to verifier/verify_preview.py" "path to extracted kit"
```

The command reads the selected directory. It does not execute its theme files or
source archive, fetch URLs, extract archives, repair files or change settings. It
does not write into the kit or create bytecode. A separately retained verifier can
check an older portable kit with the supported schema even if that kit predates
the included verifier and this guide. A published preview directory has a
different distribution manifest and is refused.

## Read the result

| Exit | Result |
| --- | --- |
| 0 | Completed comparison with no discrepancies. |
| 1 | Completed comparison with missing, changed or extra entries. |
| 2 | Invalid arguments, unsupported manifest or entries, or a content limit. |
| 3 | A read, permission, changing-file or output failure prevented completion. |
| 130 | Interrupted without a completed verdict. |

A completed report names expected file and directory counts, identifies the
observed manifest bytes by SHA-256, and labels its source revision and state as
stored claims. Discrepancies appear in this order: missing files, missing
directories, changed files, extra files and extra directories. Paths within each
group are sorted by UTF-8 bytes and quoted as JSON strings. Changed files show
both declared and observed hashes. Comparisons preserve literal spelling. A
stable case-only rename can produce missing and extra entries.

An unexpected empty directory or an OS-created metadata file counts as an extra.
A file where a directory was expected produces the corresponding missing and
extra entries. The command never removes extras. Keep your original download and
working copy. If you need a complete replacement, obtain and extract a new kit
into a separate directory, then compare that copy.

Refusals and incomplete checks write a contextual error to stderr and no verdict
to stdout before output begins. A failing output stream may already have emitted
part of the report. Those bytes cannot be retracted and are not a completed
verdict. `-h` and `--help` only display usage and do not inspect a kit.

## Supported content and limits

The verifier supports schema 2 from `clair-obscur-preview` with distribution
`portable-kit`. Its inventory consists of every declared regular file, the
unhashed `site-manifest.json`, and the directories derived from their paths. The
manifest is parsed and rechecked, but has no recorded self-hash. Hashes describe
opaque file bytes, including `source.zip`. Nested archives are not inspected.

The command refuses duplicate JSON keys, unsupported metadata, unsafe paths,
case-insensitive path collisions, links, reparse points and nonregular entries.
Relative member paths have at most 240 ASCII characters and eight components.
Windows device names, parent traversal and file/directory prefix conflicts are
unsupported. These rules also apply to extra entries before any content is read.

The measured 0.26.0 candidate uses the following finite allowances.

| Limit | Value |
| --- | --- |
| Manifest | 70,656 bytes |
| Declared hashes | 677 |
| Expected or observed files and directories | 701, excluding the root |
| Each declared member | 8,388,608 bytes |
| Total returned read bytes, including both manifest reads | 27,262,976 |
| Read chunk | At most 65,536 bytes |
| Complete stdout report, including LF newlines | 262,144 bytes |

The first corrected 0.26.0 precommit candidate measured 678 regular files and
19 directories, giving 697 entries. It includes the current collection and all
25 preserved SVG archives. The limits retain room to report four extra entries.
Its 69,969-byte manifest exceeds the former 68 KiB limit, so the finite allowance
is 69 KiB. Declared content and both manifest reads totaled 26,846,251 returned
bytes. Admission also needs two bytes of headroom for EOF and final-manifest
reservation, giving a minimum allowance of 26,846,253 bytes. The aggregate bound
is 26 MiB. That reservation is distinct from returned data or the ZIP file size.
These measurements identify the first corrected precommit candidate. Qualify
the final source artifact and kit separately.

The accepted 0.25.0 main kit remains separate: 669 regular files, 668 hashes,
19 directories, 688 entries, a 69,069-byte manifest and 25,502,403 returned read
bytes. Its former 668-hash, 692-entry, 68 KiB-manifest and 25 MiB-read boundaries
remain covered as positive historical cases. Other path, member, chunk and
report limits remain in force.

It checks path metadata against opened regular-file handles, repeats the bounded
inventory, and requires the final manifest bytes to equal the captured bytes.
Observations compare device, inode, mode, size, modification time and file
attributes, plus a platform-specific timestamp. Windows uses `st_birthtime_ns`
when available and falls back to legacy `st_ctime_ns` when birth time is absent.
Windows path and handle observations can report different `ctime` values for an
unchanged file. Creation time keeps those observations comparable. Other
platforms continue comparing `st_ctime_ns` even when birth time is available.
Timestamp comparisons remain exact, with no rounding or tolerance. Creation time
is not a Windows metadata-change timestamp, so a change reflected only in `ctime`
is outside that comparison.

Observed disappearance, replacement or compared metadata change makes the result
unverified. The content limits do not bound filesystem latency or guarantee a
simultaneous snapshot. Portable standard-library observations cannot prevent an
adversary from swapping directories between checks, or detect every race when
metadata is restored or changes occur outside the observation window.

## What consistency establishes

A consistent result means that the directory matches its included declarations.
The manifest and verifier are not authenticated. Coordinated edits to files and
their declarations can pass. Stored source labels are not a verified Git identity.
The result establishes no origin, safety, signature, installation, font, native
compatibility or physical-comfort claim.

Check the downloaded kit's external `portable-SHA256SUMS` separately when you
have a trusted reference. Its archive digest, the kit's included directory
manifest, the current source snapshot and the original versioned release describe
different objects. Keep those identities distinct.
