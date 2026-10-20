"""Make the paste-ready .min.js from a collector: drop indentation, whole-line comments and trailing '  // ' comments.
Keep explanations on their own line: a '  // ' note in the middle of a statement would cut off the rest of that line.
Usage: python3 minify.py collectors/maps_collect.js collectors/schema_collect.js"""
import pathlib, re, sys

def minify(text):
    out = []
    for l in text.splitlines():
        s = re.sub(r"\s{2,}// .*$", "", l).strip()
        if s and not s.startswith("//") and not s.startswith("/*") and not s.startswith("*"): out.append(s)
    return "\n".join(out) + "\n"

if __name__ == "__main__":
    for p in map(pathlib.Path, sys.argv[1:]):
        p.with_suffix(".min.js").write_text(minify(p.read_text()))
