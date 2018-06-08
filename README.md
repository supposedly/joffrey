# Yet Another Command-Line-Argument Parser


I've gotten tired of working around argparse. This suits my needs a bit better; vaguely inspired by
[discord.py](https://github.com/Rapptz/discord.py)'s brilliant
[ext.commands](http://discordpy.readthedocs.io/en/rewrite/ext/commands/index.html) framework.

Example:

```py
from ergo import Parser

parser = Parser()
parser.group('sc', XOR=0)  # 0 is just an identifier; it can be anything


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
    if nsp.count < 3:
        nsp.count += 1
    return nsp.count

@parser.clump(XOR=0)  # this flag *cannot* appear alongside any in group `sc` (same XOR)
@parser.flag('addition')
def add(a=4, *b):  # can also provide default args if needed
    """Who needs a calculator"""
    return int(a) + sum(map(int, b))
```
```py
>>> parser.parse('foo -S "test test" -vvvv')  # input will be shlex.split if given as a string (defaults to sys.argv though)
ErgoNamespace(name='foo', scream='TEST TEST', verbosity=3)
>>> parser.parse('foo -v')
# <help/usage info...>
Expected all of the following flags/arguments: 'scream', 'verbosity'
(Got 'verbosity')
>>> parser.parse('foo --add 1 6')
ErgoNamespace(addition=7, name='foo')
>>> parser.parse('foo -a')  # same as `foo --add`; default short alias is first letter of name (`short=None` removes entirely)
ErgoNamespace(addition=4, name='foo')
>>> parser.parse('foo -a 1 2 -S "this is gonna error" -v')
# <help/usage info...>
Expected no more than one of the following flags/arguments: 'addition', ['scream', 'verbosity']
(Got 'addition', ['scream', 'verbosity'])
>>> # etc
```
And the mysterious `help/usage info...`:
```
usage: <filename here> [-h | --help] [-a | --addition A *B] [-S | --scream  TEXT] [-v | --verbosity] `name'

ARGS
	name            Args, positional, are parsed in the order they're added in
FLAGS
	scream          I have no mouth and I must ... yeah
	addition        Who needs a calculator
	help            Prints help and exits
	verbosity       This does nothing but it shows namespaces (which are always passed as the first arg)
```
(To get rid of the default `help` flag, pass `no_help=True` to `Parser()`)

The only things not decorator-based are "groups" and "commands". Commands basically sub-parsers that have a 'name' attribute,
and groups -- demo'd above -- are applied their clump settings as a whole rather than applying them to each individual
flag/arg within the group.

```py
parser = Parser()
# Will be accessible as `parser.something`, but also returns
# the object if you'd like to assign it to something for convenience
parser.group('something', XOR='whatever')
# Also passes (*args, **kwargs) to Parser.__init__()
cmd = parser.command('etc')  # first arg is name
```

# To do
so much
