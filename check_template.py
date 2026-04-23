import re

text = open('/home/ubuntu/tweety_app/Tweety/templates/base.html').read()
lines = text.split('\n')
depth = 0
for i, line in enumerate(lines, 1):
    found = re.findall(r'\{%\s*(if|elif|else|endif|for|endfor)\b', line)
    for tag in found:
        if tag == 'if':
            depth += 1
            indent = "  " * depth
            print("  L{}: {}if (depth={})".format(i, indent, depth))
        elif tag in ('elif', 'else'):
            indent = "  " * depth
            print("  L{}: {}{}  (depth={})".format(i, indent, tag, depth))
        elif tag == 'endif':
            indent = "  " * depth
            print("  L{}: {}endif (depth={})".format(i, indent, depth))
            depth -= 1
            if depth < 0:
                print("  *** UNMATCHED endif at line {} ***".format(i))
                depth = 0
        elif tag == 'for':
            depth += 1
            indent = "  " * depth
            print("  L{}: {}for (depth={})".format(i, indent, depth))
        elif tag == 'endfor':
            indent = "  " * depth
            print("  L{}: {}endfor (depth={})".format(i, indent, depth))
            depth -= 1

print("\nFinal depth: {}".format(depth))
