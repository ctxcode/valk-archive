#!/usr/bin/env python3
# Writes tests/samples/*: archives made by Python's zipfile/tarfile and by zip and tar, and
# tests/samples.valk, what Python reads from each of them
import calendar, io, os, random, shutil, stat, struct, subprocess, tarfile, zipfile, zlib

here = os.path.dirname(os.path.abspath(__file__))
out_dir = os.path.join(here, "samples")
tree = os.path.join(here, "tmp", "sample-tree")

rng = random.Random(42)
long_dir = "long-" + "d" * 110
files = {
    "a.txt": b"alpha\n",
    "sub/b.bin": bytes(rng.getrandbits(8) for _ in range(20000)),
    "sub/words.txt": (" ".join("word%d" % rng.randrange(60) for _ in range(6000))).encode(),
    long_dir + "/" + "f" * 60 + ".txt": b"long name\n",
    "naïve/文字.txt": "unicode ✓\n".encode(),
    "empty.txt": b"",
    "run.sh": b"#!/bin/sh\necho hi\n",
}
MTIME = 1700000000

def make_tree():
    shutil.rmtree(tree, ignore_errors=True)
    os.makedirs(tree)
    for name, data in files.items():
        path = os.path.join(tree, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
    os.makedirs(os.path.join(tree, "empty-dir"))
    os.chmod(os.path.join(tree, "run.sh"), 0o755)
    os.symlink("sub/b.bin", os.path.join(tree, "link"))
    for root, dirs, names in os.walk(tree):
        for n in dirs + names:
            os.utime(os.path.join(root, n), (MTIME, MTIME), follow_symlinks=False)

def py_zip(name, compression=zipfile.ZIP_DEFLATED, zip64=False, stream=False, cp437=False):
    buf = io.BytesIO()
    target = buf
    if stream:
        class Unseekable(io.RawIOBase):
            def writable(self): return True
            def write(self, b): return buf.write(b)
        target = Unseekable()
    with zipfile.ZipFile(target, "w", compression) as z:
        z.writestr(zipfile.ZipInfo("dir/", (2020, 5, 6, 7, 8, 10)), b"")
        for fname, data in sorted(files.items()):
            if cp437 and not fname.isascii():
                continue
            info = zipfile.ZipInfo(fname, (2021, 2, 3, 4, 5, 6))
            info.external_attr = (0o100755 if fname == "run.sh" else 0o100644) << 16
            info.compress_type = compression
            with z.open(info, "w", force_zip64=zip64) as w:
                w.write(data)
        if cp437:
            class Cp437Info(zipfile.ZipInfo):
                def _encodeFilenameFlags(self):
                    return self.filename.encode("cp437"), self.flag_bits & ~0x800
            info = Cp437Info("café ½.txt", (2022, 1, 1, 0, 0, 0))
            z.writestr(info, b"cp437")
    with open(os.path.join(out_dir, name), "wb") as f:
        f.write(buf.getvalue())

def tool(name, args, cwd=tree):
    path = os.path.join(out_dir, name)
    if os.path.exists(path):
        os.remove(path)
    subprocess.run([a.replace("OUT", path) for a in args], cwd=cwd, check=True, stdout=subprocess.DEVNULL)

def py_tar(name, fmt, mode="w"):
    extra = {"pax_headers": {"comment": "a global header"}} if fmt == tarfile.PAX_FORMAT else {}
    with tarfile.open(os.path.join(out_dir, name), mode, format=fmt, **extra) as t:
        for entry in sorted(os.listdir(tree)):
            t.add(os.path.join(tree, entry), entry)
        # A hard link and a long symlink target
        info = tarfile.TarInfo("hard")
        info.type = tarfile.LNKTYPE
        info.linkname = "a.txt"
        info.mtime = MTIME
        t.addfile(info)
        # Before 1970: base-256 in GNU headers, a PAX record otherwise
        info = tarfile.TarInfo("old.txt")
        info.mtime = -86400 * 400
        info.size = 3
        t.addfile(info, io.BytesIO(b"old"))
        info = tarfile.TarInfo("longlink")
        info.type = tarfile.SYMTYPE
        info.linkname = "sub/" + "../sub/" * 20 + "b.bin"
        info.mtime = MTIME
        t.addfile(info)

def ut_mtime(extra):
    at = 0
    while at + 4 <= len(extra):
        tag, size = struct.unpack_from("<HH", extra, at)
        if tag == 0x5455 and size >= 5 and extra[at + 4] & 1:
            return struct.unpack_from("<i", extra, at + 5)[0]
        at += 4 + size
    return None

def zip_expect(path):
    result = []
    with zipfile.ZipFile(path) as z:
        if any(info.compress_type not in (0, 8) for info in z.infolist()):
            return [dict(error="unsupported")]
        for info in z.infolist():
            name = info.filename.rstrip("/")
            unix = info.create_system in (3, 19) and (info.external_attr >> 16) != 0
            mode = (info.external_attr >> 16) & 0o7777 if unix else (0o755 if info.is_dir() else 0o644)
            kind = "file"
            if info.is_dir():
                kind = "directory"
            elif unix and stat.S_ISLNK(info.external_attr >> 16):
                kind = "symlink"
            mtime = ut_mtime(info.extra)
            if mtime is None:
                mtime = calendar.timegm(info.date_time + (0, 0, 0))
            data = z.read(info)
            link = data.decode() if kind == "symlink" else ""
            size = info.file_size if kind == "file" else 0
            result.append(dict(name=name, kind=kind, size=size, mode=mode, mtime=mtime, link=link,
                               crc=zlib.crc32(data if kind == "file" else b"")))
    return result

def tar_expect(path):
    result = []
    with tarfile.open(path) as t:
        for info in t:
            kind = "other"
            if info.isreg(): kind = "file"
            elif info.isdir(): kind = "directory"
            elif info.issym(): kind = "symlink"
            elif info.islnk(): kind = "hardlink"
            data = t.extractfile(info).read() if info.isreg() else b""
            result.append(dict(name=info.name.rstrip("/"), kind=kind, size=info.size if kind == "file" else 0,
                               mode=info.mode & 0o7777, mtime=int(info.mtime // 1), link=info.linkname if kind in ("symlink", "hardlink") else "",
                               crc=zlib.crc32(data)))
    return result

def valk_string(text):
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("%", "\\%") + '"'

def main():
    os.makedirs(out_dir, exist_ok=True)
    make_tree()
    py_zip("py-deflate.zip")
    py_zip("py-stored.zip", zipfile.ZIP_STORED)
    py_zip("py-zip64.zip", zip64=True)
    py_zip("py-stream.zip", stream=True)
    py_zip("py-cp437.zip", cp437=True)
    py_zip("py-bzip2.zip", zipfile.ZIP_BZIP2)
    tool("infozip.zip", ["zip", "-q", "-r", "-y", "OUT", "."])
    # Written to a pipe, so the entries have data descriptors
    tool("infozip-stream.zip", ["sh", "-c", "zip -q -r - a.txt sub | cat > OUT"])
    py_tar("py-pax.tar", tarfile.PAX_FORMAT)
    py_tar("py-gnu.tar", tarfile.GNU_FORMAT)
    py_tar("py-pax.tar.gz", tarfile.PAX_FORMAT, "w:gz")
    tool("gnu.tar.gz", ["tar", "--format=gnu", "-czf", "OUT", "."])
    tool("posix.tar", ["tar", "--format=posix", "-cf", "OUT", "."])
    tool("bsdtar.tar", ["bsdtar", "-cf", "OUT", "."])
    lines = ["// Generated by tests/crosscheck.py: what Python reads from each sample", "",
             "fn samples() Array[Sample] {", "    return .{"]
    for name in sorted(os.listdir(out_dir)):
        path = os.path.join(out_dir, name)
        expect = zip_expect(path) if name.endswith(".zip") else tar_expect(path)
        lines.append("        Sample { file: %s, entries: .{" % valk_string(name))
        for e in expect:
            if "error" in e:
                lines.append("            Expect { error: %s }" % valk_string(e["error"]))
                continue
            lines.append("            Expect { name: %s, kind: %s, size: %d, mode: 0c%o, mtime: %d, link: %s, crc: %d }" % (
                valk_string(e["name"]), valk_string(e["kind"]), e["size"], e["mode"], e["mtime"], valk_string(e["link"]), e["crc"]))
        lines.append("        } }")
    lines += ["    }", "}", ""]
    with open(os.path.join(here, "samples.valk"), "w") as f:
        f.write("\n".join(lines))

main()
