#!/bin/sh
# Archives written by valk-archive must read in Python, unzip, GNU tar and bsdtar, and archives
# written by those must extract the same with valk-archive. Run from the repository root.
set -e
work=tests/tmp/crosscheck
rm -rf "$work"
mkdir -p "$work"
python3 tests/crosscheck.py
tree=tests/tmp/sample-tree
tool="$work/tool"
valk build ./bench -o "$tool" > /dev/null

same() {
    # Contents, symlinks and the executable bit must match
    diff -r --no-dereference "$1" "$2"
    [ -x "$2/run.sh" ] || { echo "run.sh lost its mode in $2"; exit 1; }
}

# valk writes, the others read
for name in out.zip out.tar out.tar.gz; do
    "$tool" create "$work/$name" "$tree" 2> /dev/null
done
unzip -tq "$work/out.zip"
mkdir "$work/unzip" && unzip -q "$work/out.zip" -d "$work/unzip" && same "$tree" "$work/unzip"
mkdir "$work/gnutar" && tar -xf "$work/out.tar" -C "$work/gnutar" && same "$tree" "$work/gnutar"
mkdir "$work/gnutargz" && tar -xzf "$work/out.tar.gz" -C "$work/gnutargz" && same "$tree" "$work/gnutargz"
mkdir "$work/bsdtar" && bsdtar -xf "$work/out.tar.gz" -C "$work/bsdtar" && same "$tree" "$work/bsdtar"
python3 - "$work" "$tree" <<'EOF'
import os, sys, zipfile, tarfile
work, tree = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(os.path.join(work, "out.zip")) as z:
    assert z.testzip() is None
    z.extractall(os.path.join(work, "pyzip"))
with tarfile.open(os.path.join(work, "out.tar.gz")) as t:
    t.extractall(os.path.join(work, "pytar"), filter="data")
EOF
same "$tree" "$work/pytar"
# zipfile does not make symlinks or keep modes, so compare the files only
diff -r "$tree/sub" "$work/pyzip/sub"

# Edge cases, checked entry by entry
"$tool" edge "$work" 2> /dev/null
unzip -tq "$work/edge.zip"
tar -tvf "$work/edge.tar" > /dev/null
bsdtar -tvf "$work/edge.tar.gz" > /dev/null
python3 - "$work" <<'EOF'
import os, stat, sys, zipfile, tarfile
work = sys.argv[1]
text = b"edge case contents\n" * 1000
long_name = "dir/" + "n" * 120 + "/" + "m" * 120 + ".txt"
files = {"stored.txt": text, "deflated.txt": text, "streamed.txt": text, "streamed-stored.txt": text,
         long_name: b"long name", "naïve/文字.txt": b"unicode", "run.sh": b"#!/bin/sh\n", "empty.txt": b""}
with zipfile.ZipFile(os.path.join(work, "edge.zip")) as z:
    assert z.testzip() is None
    infos = {i.filename: i for i in z.infolist()}
    for name, data in files.items():
        assert z.read(name) == data, name
    assert infos["stored.txt"].compress_type == 0 and infos["deflated.txt"].compress_type == 8
    assert infos["streamed.txt"].flag_bits & 8 and infos["streamed-stored.txt"].compress_type == 0
    assert infos["stored.txt"].external_attr >> 16 == 0o100600
    assert infos["run.sh"].external_attr >> 16 == 0o100755
    assert infos["empty-dir/"].is_dir() and infos["empty-dir/"].external_attr >> 16 == 0o40700
    assert stat.S_ISLNK(infos["link"].external_attr >> 16) and z.read("link") == b"deflated.txt"
    assert infos["naïve/文字.txt"].flag_bits & 0x800
    assert infos["stored.txt"].date_time == (2009, 2, 13, 23, 31, 30)
for name in ("edge.tar", "edge.tar.gz"):
    with tarfile.open(os.path.join(work, name)) as t:
        members = {m.name: m for m in t.getmembers()}
        for fname, data in files.items():
            assert t.extractfile(fname).read() == data, fname
            assert members[fname].mtime == 1234567890
        assert members["stored.txt"].mode == 0o600 and members["run.sh"].mode == 0o755
        assert members["empty-dir"].isdir() and members["empty-dir"].mode == 0o700
        assert members["link"].issym() and members["link"].linkname == "deflated.txt"
print("edge archives read the same in Python")
EOF

# The others write, valk extracts
(cd "$tree" && zip -q -r -y "../crosscheck/zip.zip" .)
tar -czf "$work/tar.tar.gz" -C "$tree" .
bsdtar -cf "$work/bsdtar.tar" -C "$tree" .
tar --format=gnu -cf "$work/gnu.tar" -C "$tree" .
for name in zip.zip tar.tar.gz bsdtar.tar gnu.tar; do
    "$tool" extract "$work/$name" "$work/x-$name" 2> /dev/null
    same "$tree" "$work/x-$name"
done
for name in py-deflate.zip py-zip64.zip py-stream.zip infozip.zip infozip-stream.zip py-pax.tar.gz py-gnu.tar posix.tar; do
    "$tool" extract "tests/samples/$name" "$work/s-$name" 2> /dev/null
done
diff -r "$tree/sub" "$work/s-py-zip64.zip/sub"
diff -r "$tree/sub" "$work/s-infozip-stream.zip/sub"
echo "Cross-check passed"
