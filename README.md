# valk-archive

ZIP and TAR for [Valk](https://valk-lang.dev): list, read, stream and extract archives, and write
them entry by entry or from a directory. Written in Valk on top of the standard library's
`valk.compress`, with no os-package dependencies.

Requires Valk 0.7.8 or newer.

## Install

```
vman install github.com/ctxcode/valk-archive
```

## Whole directories

```rust
use archive

archive.extract("release.tar.gz", "out") ! panic(E.message)
archive.create("backup.zip", "photos") ! panic(E.message)
```

`extract` recognizes ZIP, TAR and gzip-compressed TAR by their contents. `create` picks the format
from the extension: `.zip`, `.tar`, `.tar.gz` or `.tgz`.

## ZIP

```rust
let zip = archive.ZipReader.open("site.zip") ! panic(E.message)
each zip.entries as entry {
    println(entry.name + " " + entry.size + " bytes")
}
let html = zip.read("index.html") ! panic(E.message)  // the whole entry
let reader = zip.stream("video.mp4") ! panic(E.message) // an io.Reader over one entry
zip.read_into("big.csv", out) ! panic(E.message)       // into any io.Writer
zip.extract("site") ! panic(E.message)
zip.close()
```

`ZipReader.from_bytes(data)` reads an archive that is in memory. The central directory is read
once, so any entry can be read without the ones before it, and several at the same time. The
CRC-32 and size of every entry are checked as it is read.

```rust
let zip = archive.ZipWriter.create("site.zip") ! panic(E.message)
zip.add("index.html", html) ! panic(E.message)
zip.add("data.bin", bytes, archive.Options { compress: false }) ! panic(E.message)
zip.add_from("video.mp4", source, size) ! panic(E.message)   // streamed from an io.Reader
zip.add_file("/tmp/report.pdf", "docs/report.pdf") ! panic(E.message)
zip.add_dir("empty") ! panic(E.message)
zip.add_tree("assets", "assets/") ! panic(E.message)          // a directory from disk
zip.close() ! panic(E.message)
```

`ZipWriter.new(out)` writes to any `io.Writer`, and never seeks. Entries are deflated, or stored
when that is not smaller. ZIP64 records are added when an entry, the archive or the number of
entries needs them, and names are marked as UTF-8.

It reads stored and deflated entries, ZIP64, data descriptors, UTF-8 names (by flag or by the
Info-ZIP Unicode path field), code page 437 names, Unix modes and symlinks, extended timestamps,
and archives with data in front of them, such as self-extractors.

## TAR

```rust
let tar = archive.TarReader.open("backup.tar.gz") ! panic(E.message)
while true {
    let entry = tar.next() ! panic(E.message)
    if !isset(entry) : break
    if entry.is_file() : println(entry.name + ": " + (tar.read() ! panic(E.message)))
}
```

`TarReader.new(source)` reads any `io.Reader`, such as a socket or `io.stdin()`. Gzip is
recognized and decompressed as it streams, and only one chunk of the input is held in memory.
`tar.read()`, `tar.read_into(out)` and `tar.stream()` give the contents of the current entry;
what is not read is skipped by `next`.

```rust
let tar = archive.TarWriter.create("backup.tar.gz") ! panic(E.message) // gzip by extension
tar.add("notes.txt", "hello") ! panic(E.message)
tar.add_from("db.dump", source, size) ! panic(E.message)
tar.add_symlink("latest", "db.dump") ! panic(E.message)
tar.close() ! panic(E.message)
```

`TarWriter.new(out, gzip)` writes to any `io.Writer`. Archives are written in the PAX format:
ustar headers, with PAX records for names and link targets that do not fit, sizes from 8 GiB and
times before 1970 or after 2242. It reads ustar, PAX (also global headers), GNU long names and
links and base-256 numbers.

## Entries and options

An `Entry` has a `name` (with `/` between components and no trailing `/`), a `kind` (`file`,
`directory`, `symlink`, `hardlink` or `other`), the `size` of its contents, its `mode` such as
`0c644`, its `mtime` in Unix seconds, and the `link` target of a link.

`archive.Options` sets how an entry is written; every field has a default:

| Option | Default | |
|---|---|---|
| `mode` | `0` | Permission bits; `0` means `0c644` for files, `0c755` for directories, `0c777` for symlinks. |
| `mtime` | `null` | Modification time in Unix seconds; `null` means now. |
| `compress` | `true` | ZIP: deflate the contents. |
| `level` | `6` | ZIP: the deflate level, 1 to 9. |

`ZipWriter` and `TarWriter` share the `archive.Writer` interface, so code can write either.

## Safe extraction

Extracting never writes outside the destination. An entry with an absolute name, a drive
letter, a `..` component, a symlink or hard link whose target leads out of the destination, or a
path that runs through a symlink throws `unsafe_path`. A ZIP archive is checked as a whole before
anything is written; a TAR archive is a stream, so the entries before the unsafe one are written.
Files keep their mode without setuid, setgid, sticky and group/other write bits, devices and FIFOs
are skipped, and a hard link becomes a copy. Writers refuse the same names.

## Errors

`archive.Error` has a `message` and one of these codes: `format` (not a valid archive, or cut
short), `checksum` (a CRC-32 or TAR header checksum does not match), `unsupported`, `unsafe_path`,
`missing` (no entry with that name) and `io`.

## Benchmarks

One tree of 1201 files, 360 MB (1000 log files of 100 KB, 200 random files of 250 KB and one
200 MB log), on tmpfs, best of three runs on one machine. Deflate level 6 everywhere. Extraction
reads the same archive for every tool. `python3 bench/bench.py` reproduces it.

| Task | valk-archive | Info-ZIP / GNU tar | Python 3.14 |
|---|---|---|---|
| Create `.zip` | 16.3 s | 16.4 s (`zip -r`) | 7.4 s (`zipfile`) |
| Extract `.zip` | 1.12 s | 1.28 s (`unzip`) | 0.39 s |
| Create `.tar.gz` | 16.5 s | 16.2 s (`tar -czf`) | 11.0 s (`tarfile`) |
| Extract `.tar.gz` | 1.40 s | 0.54 s (`tar -xzf`) | 0.45 s |
| Create `.tar` | 0.21 s | 0.18 s | 0.19 s |
| Extract `.tar` | 0.22 s | 0.18 s | 0.26 s |

Compression and decompression run in `valk.compress`, which is pure Valk; Python uses zlib.

## Not supported

- ZIP: encryption, compression methods other than stored and deflate (bzip2, LZMA, Zstandard,
  Deflate64), split and spanned archives. Updating an archive in place.
- TAR: GNU sparse files (read as `other`), bzip2 and xz compression, writing hard links.
- Extraction does not restore modification times or owners. Symlinks are written only where the
  OS allows it; `add_tree` skips them on Windows.

## Development

`make test` runs the suite, `make example` runs the example, `make lint` checks the sources and
`make docs` regenerates the API documentation. `python3 tests/crosscheck.py` regenerates the
archives in `tests/samples` (written by Python, Info-ZIP and GNU tar) and what Python reads from
them. `sh bench/crosscheck.sh` checks the other direction: archives written by this package must
read and extract the same with Python, `unzip`, GNU tar and bsdtar. `python3 bench/bench.py`
runs the benchmarks.
