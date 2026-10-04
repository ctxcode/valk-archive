
# Documentation

Namespaces: [main](#main)

---

# main

## Errors for 'main'

```js
// Thrown when an archive cannot be read, written or extracted.
+ error Error (format, checksum, unsupported, unsafe_path, missing, io) payload { message: String }
```

## Enums for 'main'

```js
// What an archive entry is.
+ enum EntryKind { file, directory, symlink, hardlink, other }
```

## Functions for 'main'

```js
// Creates an archive at `path` with everything below the directory `dir`, named relative to it.
+ fn create(path: String, dir: String) void !Error
// Extracts the ZIP or TAR archive at `path` into the directory `dir`, which is created when missing.
+ fn extract(path: String, dir: String) void !Error
```

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

```js
// Reads the contents of the current TAR entry; returned by `TarReader.stream`.
+ class TarEntryReader is Reader {
    // Fills `buf` with the next bytes of the entry and returns the count; 0 at the end.
    + fn read(buf: local mut &[u8]) uint !io:IoError
}
```

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

```js
// Reads the contents of one ZIP entry; returned by `ZipReader.stream`.
+ class ZipEntryReader is Reader {
    // Fills `buf` with the next bytes of the entry and returns the count; 0 at the end.
    + fn read(buf: local mut &[u8]) uint !io:IoError
}
```

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
