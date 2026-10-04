
# Documentation

Namespaces: [main](#main)

---

# main

## Errors for 'main'

```js
// Thrown when an archive cannot be read, written or extracted.
+ error Error (format, checksum, unsupported, unsafe_path, missing, io) payload { message: String }
```

### Error

Thrown when an archive cannot be read, written or extracted.

- `format`: the data is not a valid ZIP or TAR archive, or ends too early.
- `checksum`: an entry's CRC-32, or a TAR header checksum, does not match.
- `unsupported`: a feature this package does not read, such as encryption or a compression
  method other than stored and deflate.
- `unsafe_path`: an entry would be written outside the destination directory: an absolute
  name, a `..` component, or a symlink that leads out of it.
- `missing`: no entry has the name that was asked for.
- `io`: reading the source or writing the destination failed.

## Enums for 'main'

```js
// What an archive entry is.
+ enum EntryKind { file, directory, symlink, hardlink, other }
```

### EntryKind

What an archive entry is.

## Functions for 'main'

```js
// Creates an archive at `path` with everything below the directory `dir`, named relative to it.
+ fn create(path: String, dir: String) void !Error
// Extracts the ZIP or TAR archive at `path` into the directory `dir`, which is created when missing.
+ fn extract(path: String, dir: String) void !Error
```

### create

Creates an archive at `path` with everything below the directory `dir`, named relative to
it.

The format follows the extension: `.zip`, `.tar`, or `.tar.gz` / `.tgz` for a
gzip-compressed TAR. Throws `unsupported` for any other extension. See `Writer.add_tree`.

### extract

Extracts the ZIP or TAR archive at `path` into the directory `dir`, which is created when
missing.

The format is recognized by its contents, so a `.tar.gz` needs no special name. Throws
`unsafe_path` for an entry that would end up outside `dir`: an absolute name, a `..`
component, a symlink or hard link that points out of `dir`, or a path through a symlink.
A ZIP archive is checked before anything is written; a TAR archive is read as a stream,
so the entries before an unsafe one are already written.

Files get their mode without setuid, setgid, sticky and group or other write bits, and
always owner read and write. Existing files are replaced.

## Classes for 'main'

```js
// One file, directory or link in an archive.
+ class Entry {
    // ZIP: the size of the stored data, compressed or not. TAR: the same as `size`.
    + compressed_size: uint
    // What the entry is: a file, a directory, a link or something else.
    + kind: EntryKind
    // The target of a symlink or hard link; empty otherwise.
    + link: String
    // The permission bits, such as `0c644`.
    + mode: u32
    // The modification time in seconds since the Unix epoch.
    + mtime: int
    // The path inside the archive, with `/` between components and no trailing `/`.
    + name: String
    // The size of the contents in bytes; 0 for directories and links.
    + size: uint

    // Whether this is a directory.
    + fn is_dir() bool
    // Whether this is a regular file.
    + fn is_file() bool
}
```

### Entry

One file, directory or link in an archive.

#### compressed_size

ZIP: the size of the stored data, compressed or not. TAR: the same as `size`.

#### kind

What the entry is: a file, a directory, a link or something else.

#### link

The target of a symlink or hard link; empty otherwise.

#### mode

The permission bits, such as `0c644`.

#### mtime

The modification time in seconds since the Unix epoch.

#### name

The path inside the archive, with `/` between components and no trailing `/`.

#### size

The size of the contents in bytes; 0 for directories and links.

#### is_dir

Whether this is a directory.

#### is_file

Whether this is a regular file.

```js
// How an entry is written. Every field has a default:
+ struct Options {
    // ZIP only: deflate the contents. A file that does not get smaller is stored as it is.
    + compress: bool
    // ZIP only: the deflate level, from 1 (fastest) to 9 (smallest).
    + level: uint
    // The permission bits; 0 means `0c644` for files, `0c755` for directories and `0c777` for symlinks.
    + mode: u32
    // The modification time in seconds since the Unix epoch; `null` means now.
    + mtime: ?int
}
```

### Options

How an entry is written. Every field has a default:

```valk
zip.add("run.sh", script, archive.Options { mode: 0c755 }) ! panic(E.message)
```

#### compress

ZIP only: deflate the contents. A file that does not get smaller is stored as it is.

#### level

ZIP only: the deflate level, from 1 (fastest) to 9 (smallest).

#### mode

The permission bits; 0 means `0c644` for files, `0c755` for directories and `0c777` for
symlinks.

#### mtime

The modification time in seconds since the Unix epoch; `null` means now.

```js
// Reads the contents of the current TAR entry; returned by `TarReader.stream`.
+ class TarEntryReader is Reader {
    // Fills `buf` with the next bytes of the entry and returns the count; 0 at the end.
    + fn read(buf: local mut &[u8]) uint !io:IoError
}
```

### TarEntryReader

Reads the contents of the current TAR entry; returned by `TarReader.stream`.

#### read

Fills `buf` with the next bytes of the entry and returns the count; 0 at the end.

```js
// Reads a TAR archive entry by entry from any `io.Reader`, gzip-compressed or not.
+ class TarReader {
    // Closes the file that `open` opened. A reader over another source leaves closing it to its owner.
    + fn close() void
    // Extracts the rest of the archive into the directory `dir`, which is created when missing.
    + fn extract(dir: String) void !Error
    // Reads a TAR archive from `source`. Gzip data is recognized and decompressed.
    + static fn new(source: Reader) TarReader
    // Returns the next entry, or `null` after the last one.
    + fn next() ?Entry !Error
    // Opens the TAR file at `path`, which may be gzip-compressed (`.tar.gz`, `.tgz`).
    + static fn open(path: String) TarReader !Error
    // Returns the contents of the current entry, or what is left of them.
    + fn read() String !Error
    // Writes the contents of the current entry to `out` and returns the bytes written.
    + fn read_into(out: Writer) uint !Error
    // Returns an `io.Reader` over the contents of the current entry.
    + fn stream() TarEntryReader
}
```

### TarReader

Reads a TAR archive entry by entry from any `io.Reader`, gzip-compressed or not.

Only one chunk of the input is held in memory, so a `.tar.gz` of any size streams
through. Reads ustar, PAX (long names, large sizes, exact times) and GNU long names.

```valk
let tar = archive.TarReader.open("backup.tar.gz") ! panic(E.message)
while true {
    let entry = tar.next() ! panic(E.message)
    if !isset(entry) : break
    if entry.is_file() : println(entry.name + ": " + tar.read() ! panic(E.message))
}
```

#### close

Closes the file that `open` opened. A reader over another source leaves closing it to
its owner.

#### extract

Extracts the rest of the archive into the directory `dir`, which is created when missing.

Throws `unsafe_path` for an entry that would end up outside `dir`: an absolute name,
a `..` component, or a symlink or hard link that points out of it. Entries before it are
already written then. Devices and FIFOs are skipped. See `archive.extract`.

#### new

Reads a TAR archive from `source`. Gzip data is recognized and decompressed.

bzip2 and xz are recognized too, and throw `unsupported` on the first `next`.

#### next

Returns the next entry, or `null` after the last one.

The contents of the entry can be read with `read`, `read_into` or `stream` until the
next call; what is left of them is skipped.

#### open

Opens the TAR file at `path`, which may be gzip-compressed (`.tar.gz`, `.tgz`).

The file closes when the last entry was read, or on `close`.

#### read

Returns the contents of the current entry, or what is left of them.

#### read_into

Writes the contents of the current entry to `out` and returns the bytes written.

#### stream

Returns an `io.Reader` over the contents of the current entry.

It reads nothing more once `next` is called.

```js
// Writes a TAR archive in the PAX format, gzip-compressed or not, to any `io.Writer`.
+ class TarWriter is Writer {
    // Adds a file with the contents `data`.
    + fn add(name: String, data: local &[u8], options: Options (Options{})) void !Error
    // Adds a directory.
    + fn add_dir(name: String, options: Options (Options{})) void !Error
    // Adds the file or directory at `path` under `name`, with its mode and modification time.
    + fn add_file(path: String, name: String) void !Error
    // Adds a file of exactly `size` bytes read from `source`, in pieces.
    + fn add_from(name: String, source: Reader, size: uint, options: Options (Options{})) void !Error
    // Adds a symlink that points to `target`.
    + fn add_symlink(name: String, target: String, options: Options (Options{})) void !Error
    // Adds everything below the directory `dir`, with names relative to it after `prefix`.
    + fn add_tree(dir: String, prefix: String ("")) void !Error
    // Ends the archive and writes what is left; closes the file that `create` opened.
    + fn close() void !Error
    // Creates the file at `path`, or replaces it, and writes a TAR archive to it.
    + static fn create(path: String) TarWriter !Error
    // Writes a TAR archive to `out`, gzip-compressed when `gzip` is set.
    + static fn new(out: Writer, gzip: bool (false)) TarWriter
}
```

### TarWriter

Writes a TAR archive in the PAX format, gzip-compressed or not, to any `io.Writer`.

Names and link targets that do not fit a ustar header, sizes from 8 GiB and times outside
the ustar range are written in PAX records, which every current `tar` reads.

```valk
let tar = archive.TarWriter.create("backup.tar.gz") ! panic(E.message)
tar.add("notes.txt", "hello") ! panic(E.message)
tar.add_tree("photos", "photos/") ! panic(E.message)
tar.close() ! panic(E.message)
```

#### add

Adds a file with the contents `data`.

Throws `unsafe_path` for a name that `extract` would refuse: empty, absolute or with a
`..` component.

#### add_dir

Adds a directory.

#### add_file

Adds the file or directory at `path` under `name`, with its mode and modification time.

A file is streamed from disk, so it never has to fit in memory. A directory is added
without its contents; `add_tree` adds those.

#### add_from

Adds a file of exactly `size` bytes read from `source`, in pieces.

TAR needs the size before the contents. Throws `io` when the source ends early; the
archive cannot be used then.

#### add_symlink

Adds a symlink that points to `target`.

#### add_tree

Adds everything below the directory `dir`, with names relative to it after `prefix`.

Entries are added in sorted order, directories included. Symlinks are stored as
symlinks, not followed; on Windows they are skipped.

```valk
zip.add_tree("public", "site/") ! panic(E.message)
```

#### close

Ends the archive and writes what is left; closes the file that `create` opened.

Calling it again does nothing.

#### create

Creates the file at `path`, or replaces it, and writes a TAR archive to it.

A path that ends in `.gz` or `.tgz` gets a gzip-compressed archive. `close` closes the
file.

#### new

Writes a TAR archive to `out`, gzip-compressed when `gzip` is set.

`close` ends the archive but does not close `out`.

```js
// What `ZipWriter` and `TarWriter` have in common, for code that writes either format.
+ interface Writer {
    // Adds a file with the contents `data`.
    + fn add(name: String, data: local &[u8], options: Options (Options{})) void !Error
    // Adds a directory.
    + fn add_dir(name: String, options: Options (Options{})) void !Error
    // Adds the file or directory at `path` under `name`, with its mode and modification time.
    + fn add_file(path: String, name: String) void !Error
    // Adds a file of exactly `size` bytes read from `source`, in pieces.
    + fn add_from(name: String, source: Reader, size: uint, options: Options (Options{})) void !Error
    // Adds a symlink that points to `target`.
    + fn add_symlink(name: String, target: String, options: Options (Options{})) void !Error
    // Adds everything below the directory `dir`, with names relative to it after `prefix`.
    + fn add_tree(dir: String, prefix: String ("")) void !Error
    // Writes what is left and ends the archive.
    + fn close() void !Error
}
```

### Writer

What `ZipWriter` and `TarWriter` have in common, for code that writes either format.

#### add

Adds a file with the contents `data`.

#### add_dir

Adds a directory.

#### add_file

Adds the file or directory at `path` under `name`, with its mode and modification time.

A file is streamed from disk, so it never has to fit in memory. A directory is added
without its contents; `add_tree` adds those.

#### add_from

Adds a file of exactly `size` bytes read from `source`, in pieces.

#### add_symlink

Adds a symlink that points to `target`.

#### add_tree

Adds everything below the directory `dir`, with names relative to it after `prefix`.

Entries are added in sorted order, directories included. Symlinks are stored as
symlinks, not followed; on Windows they are skipped.

```valk
zip.add_tree("public", "site/") ! panic(E.message)
```

#### close

Writes what is left and ends the archive.

```js
// Reads the contents of one ZIP entry; returned by `ZipReader.stream`.
+ class ZipEntryReader is Reader {
    // Fills `buf` with the next bytes of the entry and returns the count; 0 at the end.
    + fn read(buf: local mut &[u8]) uint !io:IoError
}
```

### ZipEntryReader

Reads the contents of one ZIP entry; returned by `ZipReader.stream`.

The CRC-32 and the size are checked when the end is reached: a mismatch, or data that is not
valid deflate, throws `read`.

#### read

Fills `buf` with the next bytes of the entry and returns the count; 0 at the end.

```js
// Reads a ZIP archive from a file or from memory.
+ class ZipReader {
    // The archive comment.
    ~ comment: String
    // Every entry, in the order of the central directory.
    ~ entries: Array[Entry]

    // Closes the file; a reader made by `from_bytes` has nothing to close.
    + fn close() void
    // Extracts every entry into the directory `dir`, which is created when missing.
    + fn extract(dir: String) void !Error
    // Returns the entry with this name, or `null`. A trailing `/` is ignored.
    + fn find(name: String) ?Entry
    // Reads a ZIP archive that is in memory; the bytes are not copied.
    + static fn from_bytes(data: &[u8]) ZipReader !Error
    // Opens the ZIP file at `path` and reads its central directory.
    + static fn open(path: String) ZipReader !Error
    // Returns the contents of the entry with this name.
    + fn read(name: String) String !Error
    // Writes the contents of the entry with this name to `out` and returns the bytes written.
    + fn read_into(name: String, out: Writer) uint !Error
    // Returns an `io.Reader` over the contents of the entry with this name.
    + fn stream(name: String) ZipEntryReader !Error
}
```

### ZipReader

Reads a ZIP archive from a file or from memory.

The central directory is read when the archive is opened, so `entries` lists every entry
at once, and any entry can be read without reading the ones before it.

```valk
let zip = archive.ZipReader.open("site.zip") ! panic(E.message)
each zip.entries as entry : println(entry.name + " " + entry.size)
let html = zip.read("index.html") ! panic(E.message)
zip.close()
```

#### comment

The archive comment.

#### entries

Every entry, in the order of the central directory.

#### close

Closes the file; a reader made by `from_bytes` has nothing to close.

#### extract

Extracts every entry into the directory `dir`, which is created when missing.

Throws `unsafe_path`, before anything is written, when an entry would end up outside
`dir`: an absolute name, a `..` component or a symlink that points out of it. See
`archive.extract`.

#### find

Returns the entry with this name, or `null`. A trailing `/` is ignored.

When a name occurs twice, the last entry wins.

#### from_bytes

Reads a ZIP archive that is in memory; the bytes are not copied.

#### open

Opens the ZIP file at `path` and reads its central directory.

The file stays open until `close`.

#### read

Returns the contents of the entry with this name.

Throws `missing` when there is no such entry, `checksum` when the CRC-32 does not match
and `format` when the data is damaged. A symlink's contents are its target.

#### read_into

Writes the contents of the entry with this name to `out` and returns the bytes written.

The entry is read and written in pieces, so it never has to fit in memory. Throws as
`read` does, and `io` when `out` fails.

#### stream

Returns an `io.Reader` over the contents of the entry with this name.

Several entries can be streamed at the same time. Throws `missing` when there is no such
entry.

```js
// Writes a ZIP archive to any `io.Writer`, entry by entry.
+ class ZipWriter is Writer {
    // The archive comment, written by `close`.
    + comment: String

    // Adds a file with the contents `data`, deflated unless the options say otherwise.
    + fn add(name: String, data: local &[u8], options: Options (Options{})) void !Error
    // Adds a directory.
    + fn add_dir(name: String, options: Options (Options{})) void !Error
    // Adds the file or directory at `path` under `name`, with its mode and modification time.
    + fn add_file(path: String, name: String) void !Error
    // Adds a file of exactly `size` bytes read from `source`, in pieces, deflated unless the options say otherwise.
    + fn add_from(name: String, source: Reader, size: uint, options: Options (Options{})) void !Error
    // Adds a symlink that points to `target`. The target is stored as the entry's contents, as Info-ZIP does.
    + fn add_symlink(name: String, target: String, options: Options (Options{})) void !Error
    // Adds everything below the directory `dir`, with names relative to it after `prefix`.
    + fn add_tree(dir: String, prefix: String ("")) void !Error
    // Writes the central directory and ends the archive; closes the file that `create` opened.
    + fn close() void !Error
    // Creates the file at `path`, or replaces it, and writes a ZIP archive to it. `close` closes the file.
    + static fn create(path: String) ZipWriter !Error
    // Writes a ZIP archive to `out`. `close` ends the archive but does not close `out`.
    + static fn new(out: Writer) ZipWriter
}
```

### ZipWriter

Writes a ZIP archive to any `io.Writer`, entry by entry.

Each entry is stored or deflated as its options say. ZIP64 records are written when an
entry, the archive or the number of entries needs them, and names are marked as UTF-8.

```valk
let zip = archive.ZipWriter.create("site.zip") ! panic(E.message)
zip.add("index.html", html) ! panic(E.message)
zip.add_file("logo.png", "img/logo.png") ! panic(E.message)
zip.close() ! panic(E.message)
```

#### comment

The archive comment, written by `close`.

#### add

Adds a file with the contents `data`, deflated unless the options say otherwise.

Throws `unsafe_path` for a name that `extract` would refuse: empty, absolute or with a
`..` component.

#### add_dir

Adds a directory.

#### add_file

Adds the file or directory at `path` under `name`, with its mode and modification time.

A file is streamed from disk, so it never has to fit in memory. A directory is added
without its contents; `add_tree` adds those.

#### add_from

Adds a file of exactly `size` bytes read from `source`, in pieces, deflated unless the
options say otherwise.

The CRC-32 and the compressed size follow the data in a data descriptor. Throws `io`
when the source ends early; the archive cannot be used then.

#### add_symlink

Adds a symlink that points to `target`. The target is stored as the entry's contents,
as Info-ZIP does.

#### add_tree

Adds everything below the directory `dir`, with names relative to it after `prefix`.

Entries are added in sorted order, directories included. Symlinks are stored as
symlinks, not followed; on Windows they are skipped.

```valk
zip.add_tree("public", "site/") ! panic(E.message)
```

#### close

Writes the central directory and ends the archive; closes the file that `create`
opened.

Calling it again does nothing.

#### create

Creates the file at `path`, or replaces it, and writes a ZIP archive to it. `close`
closes the file.

#### new

Writes a ZIP archive to `out`. `close` ends the archive but does not close `out`.
