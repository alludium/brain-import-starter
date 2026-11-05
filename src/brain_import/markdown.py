"""The first ATX H1 outside fenced code and HTML comments, without rewriting text."""

import re


def heading(text):
    fence = None
    comment = False
    for line in text.removeprefix("\ufeff").splitlines():
        if fence:
            if re.fullmatch(
                r" {0,3}" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}\s*", line
            ):
                fence = None
            continue
        if comment:
            if "-->" not in line:
                continue
            line = line.split("-->", 1)[1]
            comment = False
        while "<!--" in line:
            before, after = line.split("<!--", 1)
            if "-->" in after:
                line = before + after.split("-->", 1)[1]
            else:
                line = before
                comment = True
                break
        opened = re.match(r" {0,3}(`{3,}|~{3,})(.*)$", line)
        if opened and not (opened[1][0] == "`" and "`" in opened[2]):
            fence = opened[1]
            continue
        match = re.match(r" {0,3}#(?:[ \t]+(.*)|[ \t]*)$", line)
        if match:
            value = re.sub(r"[ \t]+#+[ \t]*$", "", match[1] or "").strip()
            if value:
                return value[:500]
    return ""
