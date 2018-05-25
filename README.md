# It Sucks Less Than Argparse™


Yet another argparse substitute, this one heavily inspired by [discord.py](Rapptz/discord.py)'s "[commands extension](http://discordpy.readthedocs.io/en/rewrite/ext/commands/index.html)".
Sorta clunky and the above shoehorning occasionally shows. But it's clearer than argparse, in the designer's humble opinion!


Sample:

```py
from ergo import Parser

parser = Parser()
parser.group('sc', XOR=0)  # nothing special about 0; it's just an identifier


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

@parser.clump(XOR=0)  # this flag *cannot* appear alongside group `sc` (same XOR)
@parser.flag('addition')
def add(a: int, b: int = 0):  # can also provide default args if needed
    """Who needs a calculator"""
    return a + b
```
```py
>>> parser.parse('foo -S "test test" -vvvv')  # input will be shlex.split if given as a string (defaults to sys.argv though)
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

(step 1 would be figuring out aliases for commands, and making groups transparent)