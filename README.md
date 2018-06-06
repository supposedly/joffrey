# It Sucks Less Than Argparse™


Yet another argparse substitute, this one heavily inspired by [discord.py](https://github.com/Rapptz/discord.py)'s
"[commands extension](http://discordpy.readthedocs.io/en/rewrite/ext/commands/index.html)".
Sorta clunky and the above shoehorning occasionally shows. But it's clearer than argparse, in the designer's humble opinion!

Sample:

```py
from ergo import Parser

parser = Parser()
parser.group('sc', XOR=0)  # 0 is just an identifier; nothing special about it


@parser.arg()
def name(name):
    """Args, positional, are parsed in the order they're added in"""
    return name

@parser.sc.clump(AND='blah')
@parser.sc.flag(short='S')
def scream(text):
    """I have no mouth and I must ... yeah"""
    return text.upper()

@parser.sc.clump(AND='blah')  # this flag and `scream` *must* appear together (same AND)
@parser.sc.flag('verbosity', namespace={'count': 0})
def verbose(nsp):
    """This does nothing but it shows namespaces (which are always passed as the first arg)"""
    if nsp.count < 5:
        nsp.count += 1
    return nsp.count

@parser.clump(XOR=0)  # this flag *cannot* appear alongside any in group `sc` (same XOR)
@parser.flag('addition')
def add(a=0, *b):  # can also provide default args if needed
    """Who needs a calculator"""
    return int(a) + sum(map(int, b))
```
```py
>>> parser.parse('foo -S "test test" -vvvv')  # input will be shlex.split if given as a string (defaults to sys.argv though)
ErgoNamespace(name='foo', scream='TEST TEST', verbosity=4)
>>> parser.parse('foo -v')
<usage/help info...>
Expected all of the following flags/arguments: 'scream', 'verbose' (only got 'verbosity')
>>> parser.parse('foo --add 1 2')
ErgoNamespace(addition=3, name='foo')
>>> parser.parse('foo --add 1 2 -S "this is gonna error" -v')
<usage/help info...>
Expected no more than one of the following flags/arguments: 'scream', 'add', 'verbose' (got 'scream', 'verbosity', 'addition')
>>> # etc
```

The only things not deco-based are "groups" and "commands" -- commands are basically sub-parsers (argparse's subcommands) and groups are so you can do `parser.add_group('name', AND=blah, OR=blah, XOR=blah)` and then `@parser.name.flag`/`.arg` (rather than `@parser.flag`/`.arg`); those clump settings apply to the whole group rather than to each flag/arg within it.

```py
parser = Parser()
# will be accessible as `parser.something`, but also returns
# the object if you'd like to assign it to something for convenience
parser.group('something', XOR='whatever')
cmd = parser.command('etc')
```

# To do
so much
