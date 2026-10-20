"""The .min.js files are what gets pasted into Chrome. They must be exactly what minify.py makes from the .js source,
so a fix in the source can never be missing from (or half-applied to) the pasted copy. Run: python3 tests/test_paste_files.py"""
import pathlib, subprocess, sys
ENG = pathlib.Path(__file__).resolve().parent.parent; fails = 0
sys.path.insert(0, str(ENG)); from minify import minify
for js in sorted((ENG / "collectors").glob("*.js")):
    if js.name.endswith(".min.js"): continue
    want = minify(js.read_text()); have = js.with_suffix(".min.js").read_text()
    ok = want == have; fails += 0 if ok else 1
    print(("PASS " if ok else "FAIL ") + f"{js.with_suffix('.min.js').name} matches its source" + ("" if ok else " (run: python3 minify.py collectors/*.js)"))
    r = subprocess.run(["node", "--check", str(js.with_suffix(".min.js"))], capture_output=True, text=True)
    ok = r.returncode == 0; fails += 0 if ok else 1
    print(("PASS " if ok else "FAIL ") + f"{js.with_suffix('.min.js').name} is valid JavaScript" + ("" if ok else " " + r.stderr[-200:]))
print("ALL PASSED" if not fails else f"{fails} FAILED"); sys.exit(1 if fails else 0)
