#!/usr/bin/env python3
# Times valk-archive against zip/unzip, GNU tar and Python on one large tree.
# Usage: python3 bench/bench.py [work-dir]   (from the repository root)
import os, random, shutil, subprocess, sys, tarfile, time, zipfile

work = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "tests/tmp/bench")
tree = os.path.join(work, "tree")
tool = os.path.join(work, "tool")

def make_tree():
    if os.path.isdir(tree):
        return
    rng = random.Random(1)
    words = ["%s%d" % (w, i) for i in range(40) for w in ("info", "warn", "user", "path", "GET")]
    def text(size):
        parts, length = [], 0
        while length < size:
            line = "2026-10-04T12:%02d:%02d %s\n" % (rng.randrange(60), rng.randrange(60), " ".join(rng.choice(words) for _ in range(8)))
            parts.append(line)
            length += len(line)
        return "".join(parts).encode()
    for i in range(1000):
        path = os.path.join(tree, "logs", "d%02d" % (i % 20), "f%04d.log" % i)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(text(100000))
    for i in range(200):
        path = os.path.join(tree, "bin", "b%03d.bin" % i)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(rng.randbytes(250000))
    with open(os.path.join(tree, "big.log"), "wb") as f:
        chunk = text(1 << 20)
        for _ in range(200):
            f.write(chunk)

def run(label, fn):
    best = None
    for _ in range(3):
        start = time.perf_counter()
        fn()
        took = time.perf_counter() - start
        best = took if best is None or took < best else best
    print("| %-40s | %6.2f s |" % (label, best))

def sh(*args, cwd=None):
    return lambda: subprocess.run(args, cwd=cwd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def fresh(path):
    shutil.rmtree(path, ignore_errors=True)
    if os.path.exists(path):
        os.remove(path)
    return path

def then(*steps):
    def f():
        for s in steps:
            s()
    return f

def py_zip(out):
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, names in os.walk(tree):
            for n in sorted(dirs + names):
                p = os.path.join(root, n)
                z.write(p, os.path.relpath(p, tree))

def py_tar(out, mode):
    with tarfile.open(out, mode) as t:
        t.add(tree, ".")

def main():
    os.makedirs(work, exist_ok=True)
    make_tree()
    subprocess.run(["valk", "build", "./bench", "--release", "-o", tool], check=True, stdout=subprocess.DEVNULL)
    size = sum(os.path.getsize(os.path.join(r, n)) for r, _, ns in os.walk(tree) for n in ns)
    print("Tree: %d files, %.0f MB\n" % (sum(len(ns) for _, _, ns in os.walk(tree)), size / 1e6))
    print("| Task | Time |\n|---|---|")
    z, t, tgz = (os.path.join(work, n) for n in ("out.zip", "out.tar", "out.tar.gz"))
    x = os.path.join(work, "x")
    run("zip create: valk-archive", then(lambda: fresh(z), sh(tool, "create", z, tree)))
    run("zip create: zip -r (Info-ZIP)", then(lambda: fresh(z), sh("zip", "-q", "-r", z, ".", cwd=tree)))
    run("zip create: python zipfile", then(lambda: fresh(z), lambda: py_zip(z)))
    run("zip extract: valk-archive", then(lambda: fresh(x), sh(tool, "extract", z, x)))
    run("zip extract: unzip", then(lambda: fresh(x), sh("unzip", "-q", z, "-d", x)))
    run("zip extract: python zipfile", then(lambda: fresh(x), lambda: zipfile.ZipFile(z).extractall(x)))
    run("zip list: valk-archive", sh(tool, "list", z))
    run("zip list: unzip -l", sh("unzip", "-l", z))
    run("tar.gz create: valk-archive", then(lambda: fresh(tgz), sh(tool, "create", tgz, tree)))
    run("tar.gz create: tar -czf", sh("tar", "-czf", tgz, "-C", tree, "."))
    run("tar.gz create: python tarfile", then(lambda: fresh(tgz), lambda: py_tar(tgz, "w:gz")))
    run("tar.gz extract: valk-archive", then(lambda: fresh(x), sh(tool, "extract", tgz, x)))
    run("tar.gz extract: tar -xzf", then(lambda: fresh(x), lambda: os.makedirs(x), sh("tar", "-xzf", tgz, "-C", x)))
    run("tar.gz extract: python tarfile", then(lambda: fresh(x), lambda: tarfile.open(tgz).extractall(x, filter="data")))
    run("tar create: valk-archive", then(lambda: fresh(t), sh(tool, "create", t, tree)))
    run("tar create: tar -cf", sh("tar", "-cf", t, "-C", tree, "."))
    run("tar create: python tarfile", then(lambda: fresh(t), lambda: py_tar(t, "w")))
    run("tar extract: valk-archive", then(lambda: fresh(x), sh(tool, "extract", t, x)))
    run("tar extract: tar -xf", then(lambda: fresh(x), lambda: os.makedirs(x), sh("tar", "-xf", t, "-C", x)))
    run("tar extract: python tarfile", then(lambda: fresh(x), lambda: tarfile.open(t).extractall(x, filter="data")))
    fresh(x)

main()
