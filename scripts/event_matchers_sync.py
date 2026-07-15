"""Fetch `eventTypeMatchers` from a GitHub branch and translate to Python.

Usage examples:
    from event_matchers_sync import generate_python_matchers_from_github

    # fetch and return a python dict mapping -> list of (pattern, flags)
    matchers = generate_python_matchers_from_github(
        owner='tylerbarna', repo='gcn.nasa.gov', branch='Fix-matcher-commits',
        path='app/routes/circulars/circulars.lib.ts', const_name='eventTypeMatchers'
    )

    # write a module file to disk
    write_python_matchers(matchers, 'event_matchers.py')

This module uses only the standard library.
"""

import re
import urllib.request
import typing as t
import io


def fetch_raw_from_github(owner: str, repo: str, branch: str, path: str, timeout: int = 10) -> str:
    """Return the raw file contents from raw.githubusercontent.com.

    Example URL constructed:
      https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}
    """
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.read().decode('utf-8')


def _strip_js_comments(s: str) -> str:
    # remove /* ... */ and //...
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"//.*?$", "", s, flags=re.M)
    return s


def extract_js_constant_object(js: str, const_name: str = 'eventTypeMatchers') -> str:
    """Find the object literal assigned to a top-level const/let/var with given name.

    Returns the object text (including surrounding braces) or raises ValueError.
    """
    js_nocomments = _strip_js_comments(js)
    # find start of assignment
    # Allow optional TypeScript type annotation between the name and '=' (e.g. "const name: Type = {")
    m = re.search(rf"(?:export\s+)?(?:const|let|var)\s+{re.escape(const_name)}(?:\s*:\s*[^=]+)?\s*=\s*\{{", js_nocomments)
    if not m:
        raise ValueError(f"Could not find assignment for '{const_name}'")
    start = m.end() - 1  # position of '{'

    # find matching closing brace by counting
    depth = 0
    for i in range(start, len(js_nocomments)):
        ch = js_nocomments[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return js_nocomments[start:i + 1]
    raise ValueError('Unterminated object literal')


def _extract_array_text(js_obj: str, key_pos: int) -> t.Tuple[str, int]:
    """Given object text and position of '[' return array text and end index."""
    # find opening '[' from key_pos
    open_idx = js_obj.find('[', key_pos)
    if open_idx == -1:
        raise ValueError('No array found for key')
    depth = 0
    for i in range(open_idx, len(js_obj)):
        ch = js_obj[i]
        if ch == '[':
            depth += 1
        elif ch == ']':
            depth -= 1
            if depth == 0:
                return js_obj[open_idx:i + 1], i + 1
    raise ValueError('Unterminated array')


def parse_js_matchers_object(obj_text: str) -> t.Dict[str, t.List[t.Tuple[str, str]]]:
    """Parse the JS object literal and return mapping: key -> list of (pattern, flags).

    Only supports regex literals (/.../flags) and RegExp("...", "flags").
    Returns pattern as raw JS string and flags as string (e.g. 'i', 'm', '').
    """
    out: t.Dict[str, t.List[t.Tuple[str, str]]] = {}
    cleaned = _strip_js_comments(obj_text)

    # iterate keys: either 'key' or "key" possibly with whitespace
    # this simple approach assumes keys are quoted
    # match either quoted keys or bare identifiers (TypeScript object keys)
    key_iter = re.finditer(r"(?:(['\"])(?P<qkey>.*?)\1|(?P<ukey>[A-Za-z_$][A-Za-z0-9_$]*))\s*:\s*", cleaned)
    for km in key_iter:
        key = km.group('qkey') or km.group('ukey')
        # extract the array text following this key
        try:
            array_text, end_idx = _extract_array_text(cleaned, km.end())
        except ValueError:
            out[key] = []
            continue


        patterns: t.List[t.Tuple[str, str]] = []

        # robustly extract regex literals from the array text by scanning
        def extract_regex_literals(s: str) -> t.List[t.Tuple[str, str]]:
            out_literals: t.List[t.Tuple[str, str]] = []
            i = 0
            n = len(s)
            while i < n:
                ch = s[i]
                if ch == '/':
                    # start of regex literal - scan until unescaped '/' not inside char class
                    j = i + 1
                    in_class = False
                    while j < n:
                        c = s[j]
                        if c == '\\':
                            j += 2
                            continue
                        if c == '[':
                            in_class = True
                            j += 1
                            continue
                        if c == ']' and in_class:
                            in_class = False
                            j += 1
                            continue
                        if c == '/' and not in_class:
                            # end of literal
                            # collect flags
                            k = j + 1
                            flags = ''
                            while k < n and s[k].isalpha():
                                flags += s[k]
                                k += 1
                            pat = s[i+1:j]
                            out_literals.append((pat, flags))
                            i = k
                            break
                        j += 1
                    else:
                        # unterminated - bail
                        i += 1
                else:
                    i += 1
            return out_literals

        patterns.extend(extract_regex_literals(array_text))

        # also support RegExp('pat','flags') or new RegExp("pat","flags")
        for r2 in re.finditer(r"RegExp\s*\(\s*(['\"])(?P<pat>.*?)\1\s*(?:,\s*(['\"])(?P<flags>.*?)\3\s*)?\)", array_text):
            pat = r2.group('pat')
            flags = r2.group('flags') or ''
            patterns.append((pat, flags))

        out[key] = patterns

    return out


def js_flags_to_re_flags(flags: str) -> t.List[str]:
    out = []
    if not flags:
        return out
    if 'i' in flags:
        out.append('re.IGNORECASE')
    if 'm' in flags:
        out.append('re.MULTILINE')
    if 's' in flags:
        out.append('re.DOTALL')
    # ignore 'u' and other JS-specific flags for now
    return out


def build_python_matchers_source(parsed: t.Dict[str, t.List[t.Tuple[str, str]]], module_name: str = 'event_matchers') -> str:
    """Generate Python source for EVENT_TYPE_MATCHERS from parsed data.

    Returns the source string.
    """
    out = io.StringIO()
    out.write("import re\n\n")
    out.write("# Auto-generated from JavaScript eventTypeMatchers\n")
    out.write("EVENT_TYPE_MATCHERS = {\n")
    # ensure deterministic order
    keys = list(parsed.keys())
    if 'Misc' not in parsed:
        keys.append('Misc')
    for key in keys:
        patterns = parsed.get(key, [])
        out.write(f"    {repr(key)}: [\n")
        for pat, flags in patterns:
            # produce a safe Python string literal for the pattern
            py_pat = repr(pat)
            flag_exprs = js_flags_to_re_flags(flags)
            if flag_exprs:
                flags_joined = ' | '.join(flag_exprs)
                out.write(f"        re.compile({py_pat}, {flags_joined}),\n")
            else:
                out.write(f"        re.compile({py_pat}),\n")
        out.write("    ],\n")
    out.write("}\n")
    return out.getvalue()


def generate_python_matchers_from_github(owner: str, repo: str, branch: str, path: str, const_name: str = 'eventTypeMatchers') -> t.Dict[str, t.List[t.Tuple[str, str]]]:
    """Fetch JS constant from GitHub and return parsed structure.

    Returns mapping: key -> list of (pattern, flags)
    """
    js = fetch_raw_from_github(owner, repo, branch, path)
    obj_text = extract_js_constant_object(js, const_name=const_name)
    parsed = parse_js_matchers_object(obj_text)
    return parsed


def write_python_matchers(parsed: t.Dict[str, t.List[t.Tuple[str, str]]], out_path: str = 'event_matchers.py') -> None:
    src = build_python_matchers_source(parsed)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(src)


if __name__ == '__main__':
    # quick CLI: generate and write module
    import argparse

    p = argparse.ArgumentParser(description='Fetch JS eventTypeMatchers and write Python module')
    p.add_argument('--owner', default='tylerbarna')
    p.add_argument('--repo', default='gcn.nasa.gov')
    p.add_argument('--branch', default='Fix-matcher-commits')
    p.add_argument('--path', default='app/routes/circulars/circulars.lib.ts')
    p.add_argument('--const', dest='const_name', default='eventTypeMatchers')
    p.add_argument('--out', default='event_matchers.py')
    args = p.parse_args()

    parsed = generate_python_matchers_from_github(args.owner, args.repo, args.branch, args.path, const_name=args.const_name)
    write_python_matchers(parsed, args.out)
    print(f'Wrote {args.out} with {len(parsed)} categories')
