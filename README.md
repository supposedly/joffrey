# It Sucks Less Than Argparse™


Yet another argparse substitute, this one heavily inspired by [discord.py](Rapptz/discord.py)'s "[commands extension](http://discordpy.readthedocs.io/en/rewrite/ext/commands/index.html)".
Sorta clunky and the above shoehorning occasionally shows. But it's clearer than argparse, in the designer's humble opinion!


Sample:

```py
from ergo import Parser

parser = Parser()

@parser.arg()
def name(name):
    """Args, positional, are parsed in the order they're added in"""
    return name

@parser.clump(XOR=0, AND='blah')  # nothing special about the rvalues as long as they're unique to their clump
@parser.flag(short='S')
def scream(text: str):
    """I have no mouth and I must ... yeah"""
    return text.upper()

@parser.clump(AND='blah')  # i.e. this flag and `scream` *must* appear together (same AND)
@parser.flag('verbosity', namespace={'count': 0})
def verbose(nsp):
    """This nothing but it demos namespaces (which are always passed as the first arg)"""
    if nsp.count < 5:
        nsp.count += 1
    return nsp.count

@parser.clump(XOR=0)  # i.e. this flag *cannot* appear alongside `scream` (same XOR)
@parser.flag('addition')
def add(a: int, b: int):  # can also provide default args if needed
    """Who needs a calculator tbh"""
    return a + b

```
```py
>>> parser.parse('foo -S "test test" -vvvv')  # input will be shlex.split() if isinstance(..., str)
{'name': 'foo', 'scream': 'TEST TEST', 'verbosity': 4}
>>> parser.parse('foo -v')
ValueError: Expected all of the following arguments: 'verbosity', 'scream' (only got 'verbosity')
>>> parser.parse('foo --add 1 2')
{'name': 'foo', 'addition': 3}
>>> parser.parse('foo --add 1 2 -S "this is gonna error" -v')
ValueError: Expected at most one of the following arguments: 'scream', 'addition' (got 'scream', 'addition')
>>> # etc
```

The only things not deco-based are "groups" and "commands" -- commands are basically sub-parsers (so like argparse's subcommands) and groups are so you can do `mygroup = parser.add_group(AND=blah, OR=blah, XOR=blah)` and then `@mygroup.flag`/`.arg` (rather than `@parser.flag`/`.arg`); those clump settings apply to the whole group rather than to each flag/arg within it.

```py
parser = Parser()
# will be accessible as `parser.something`, but also returns
# the object if you'd like to assign it to something for convenience
parser.group('something', XOR='whatever')
cmd = parser.command('etc')
```

# To do
so much