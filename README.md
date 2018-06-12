# Yet Another Command-Line-Argument Parser

[![Build Status](https://travis-ci.com/eltrhn/ergo.svg?branch=master)](https://travis-ci.com/eltrhn/ergo)
[![codecov](https://codecov.io/gh/eltrhn/ergo/branch/master/graph/badge.svg)](https://codecov.io/gh/eltrhn/ergo)

I'm tired of working around argparse. This suits my needs a tad better; vaguely inspired by
[discord.py](https://github.com/Rapptz/discord.py)'s brilliant
[ext.commands](http://discordpy.readthedocs.io/en/rewrite/ext/commands/index.html) framework.

[](#separator-for-pypi)

```nginx
pip install ergo
```

## Contents

1. [Example](#example)
2. [Why?](#why)
3. [Documentation](#documentation)
    1. [Parser](#parser)
    2. [Callbacks](#callbacks)
    3. [Typehinting goodies](#more-typehints)

[](#separator-for-pypi)

## Example

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
def add(a: int = 4, *b: int):  # can also provide default args and a type-coercion hint if needed
    """Who needs a calculator"""
    return a + sum(b)
```
```py
>>> parser.parse('foo -S "test test" -vvvv')  # input will be shlex.split if given as a string (defaults to sys.argv though)
ErgoNamespace(name='foo', scream='TEST TEST', verbosity=3)
>>> 
>>> parser.parse('foo -v')
# <help/usage info...>
Expected all of the following flags/arguments: 'scream', 'verbosity'
(Got 'verbosity')
>>> 
>>> parser.parse('foo --add 1 6')
ErgoNamespace(addition=7, name='foo')
>>> 
>>> parser.parse('foo -a')  # same as `foo --add`; default short alias is first letter of name (`short=None` removes entirely)
ErgoNamespace(addition=4, name='foo')
>>> 
>>> parser.parse('foo -a 1 2 -S "this is gonna error" -v')
# <help/usage info...>
Expected no more than one of the following flags/arguments: 'addition', ['scream', 'verbosity']
(Got 'addition', ['scream', 'verbosity'])
>>> 
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

The only things not decorator-based are "groups" and "commands". Commands (subparsers) are parsers that have a 'name' attribute,
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

## Why?
I needed a way to define sort-of-complex interdependencies between command-line options. None of the available libs
I found were able to handle this out of the box to an acceptable degree, so I decided to try my own hand;
I feel like the lib should be able to handle this stuff itself, without your needing to delegate roles like *"check
that these two flags aren't used at the same time as this arg"* or *"make sure all these things appear
together, or alternatively that this second thing does"* to external functions or post-parsing if-statements.

Ergo, by the way, is still early in alpha. If it really doesn't solve the same problem for you that it does for me,
I think you'd be better off trying something else; docopt, for example, is superb, and Fire's no-assembly-required
philosophy is quite fun in its own right.  
I also, in full disclosure, don't too much enjoy the design of a lot of current argparse-like solutions (really, most
of them except docopt). As such, in addition to aiding in the creation of such interdependent systems as mentioned
above, ergo is also my shot at creating a more-intuitive interface for this sort of stuff.
Time will have to tell whether it succeeds!

[](#separator-for-pypi)

## Documentation

### Parser
```py
from ergo import Parser
```
The main dish.  

`parser = Parser(flag_prefix='-', systemexit=True, no_help=False)`

[]()
- `flag_prefix` (`str`): The 'short' prefix used to reference this parser's flags from the command line. Cannot be empty.
    Derived from this as well is `Parser().long_prefix`, constructed by doubling `flag_prefix`.
- `systemexit` (`bool`): Whether, during parsing, to yield to the default behavior of capturing exceptions then printing them
    in a `SystemExit` call alongside the default help/usage info (`True`) -- or to allow exceptions to bubble up as normal (`False`).
- `no_help` (`bool`): If `True`, prevents creation of a default `h` (short) / `help` (long) flag.

Methods:
- `flag` (decorator):  
    See [`Callbacks`](#callbacks) for more info.  
    
    `@parser.flag(dest=None, short=_Null, *, default=_Null, namespace=None, required=False, help=None, _='-')`
    
    []()
    - `dest` (`str`): The name this flag will be referenced by from the command line (with long prefix), as well as the name it will
        appear as in the final `Parser.parse()` output. Defaults to the decorated function's `__name__`.
    - `short` (`str`): This flag's single-character short alias, to be used from the command line with `parser.flag_prefix`. If `None`,
        no short alias will be made; if left alone (i.e. passed `ergo.core._Null`), defaults to the first alphanumeric character in the
        decorated function's `__name__`.
    - `default`: Default value of this flag if not invoked during parsing. (no default value if `_Null`)
    - `namespace` (`dict`): The starting values for this flag's "namespace", a `types.SimpleNamespace` object passed as the first argument
        to the decorated function. Can be used to store values between repeated flag invocations. If `None`, no namespace will be created
        or passed to said function.
    - `required` (`bool`): Whether to error if this flag is not provided (independent of clump settings; do not use this with `XOR`, for instance).
    - `help`: Help text to appear alongside this flag. If not provided, will be grabbed if present from the decorated function's `__doc__`.
    - `_`: Determines how to replace underscores in the flag's name (be the name from `dest` or the function's `__name__`). Default `'-'`, meaning
        that a flag named `check_twice` will be invoked as `--check-twice` (if `_='.'`, then `--check.twice`). Final output will still use the
        original pre-replacement name, however.
- `arg` (decorator):  
    See [`Callbacks`](#callbacks) for more info.  
    
    `@parser.arg(n=1, *, namespace=None, required=False, help=None, _='-')`  
    *See identical args of `flag`.*
    
    []()
    - `n` (`int`, Ellipsis): How many times this argument should be repeated. If `n` is 2, for example,
        the decorated function will be called on two consecutively-passed command-line arguments.  
    You can use the `namespace`, as in `flag`, to store info about this argument's values betweeen
    calls.
    If `n` is `...` or `Ellipsis`, this arg will consume as many arguments as it can before reaching either a
    flag or a subcommand.  
    Intended to be used as a positional argument, as in `@parser.arg(2)` or `@parser.arg(...)`.
- `clump` (decorator):  
    Each component (AND, OR, XOR) takes an identifier, and any other entity bound to this parser with
    the same identifier is considered part of the same clump.  
    
    `@parser.clump(AND=_Null, OR=_Null, XOR=_Null)`
    
    []()
    - `AND`: Clumps together entities that *must* appear together. An ANDed entity is excused from being invoked if it is
        part of a satisfied OR clump (i.e. at least one other member of its OR clump appeared) or a satisfied XOR clump (i.e.
        exactly one other member of its XOR clump appeared).
    - `OR`: Clumps together entities of which *at least one* must appear. An ORed entity is excused from being invoked if it is
        part of a satisfied XOR clump (i.e. exactly one other member of its XOR clump appeared).
    - `XOR`: Clumps together entities of which *at most one* can appear. An XORed entity is allowed to appear alongside more than one
        other if it satisfies an AND clump (i.e. all other members of its AND clump appeared) or if it is `required`.
- `group`:  
    Creates a "group", which applies its clump settings to itself as a whole rather than to its members. Groups can also clump entities
    within themselves.  
    
    `parser.group(name, *, required=False, AND=_Null, OR=_Null, XOR=_Null)`  
    *See identical args of `flag` and `clump`.*
    
    []()
    - `name` (`str`): This group's name; is added as an attribute to the parser, so `@parser.group('x', ...)` will result in the group being
        accessible as `parser.x`. The `group()` method also returns the created group, however, so it can be assigned to its own variable name
        if need be.
- `command`:  
    Returns a sub-parser of this parser. When a command is detected in parsing input, parsing of its parent's options is abandoned and everything
    to the right is passed to the subparser instance.  
    
    `parser.command(name, *args, aliases=(), AND=_Null, OR=_Null, XOR=_Null, _='-', **kwargs)`  
    *See identical args of `flag` and `clump`.*  
    *\*args, \*\*kwargs are passed to `Parser.__init__()`.*
    
    []()
    - `name` (`str`): The name with which this command is to be invoked from the command line, as well as the name under which its final parsed
        output will appear in its parent's.
    - `aliases` (`tuple`): Alternative names with which this command can be invoked.
- `remove`:
    Removes an entity, be it an arg, flag, or command.
    
    `parser.remove(name)`

    []()
    - `name` (`str`, `Entity`): Name of arg to remove. If passed an Entity instance, uses its name instead.
- `parse`:
    Applies parser's args/flags/commands/groups/clumps to its given input.

    `parser.parse(inp=sys.argv[1:], *, systemexit=None, strict=False)`

    []()
    - `inp` (`str`, `list`): Input to parse args of. If given as a string, converted using `shlex.split()`.
    - `systemexit`: If set, overrides parser-level `systemexit` attribute. Has the same meaning, then, as `Parser.systemexit`.
    - `strict`: If `True`, parses in "strict mode": Unknown flags will cause an error rather than be ignored, and a bad amount
    of arguments (too few/too many) will do the same.


### Callbacks
`Parser.flag` and `Parser.arg` decorate functions; these functions are subsequently called when their flag/arg's name is detected during parsing.

If a callback's parameters are [type-hinted](https://www.python.org/dev/peps/pep-3107/), the arguments passed will attempt to be "converted" by
these typehints. That is, if the hint is a callable object, it will be called on a command-line argument passed in that spot. Consider the
following flag:

```py
@parser.flag('addition')
def add(a: int, b: int):
    """Who needs a calculator"""
    return a + b
```

If this flag is invoked from the command line as `--addition 1 2`, each of `1` and `2` will be given (as a string) to the `int` typehint and thus passed into
the `add()` function as an integer. (No error would result if the hint were not callable; the command-line value would simply not be converted from a string)

The number of arguments to be passed to a *flag* is determined by the number of parameters its function has; *args*, on the other hand, **always pass one value** to their callbacks. Flag callbacks are called as many times as the user
writes the flag's name, and arg callbacks are called as many times as indicated by the `n` argument in `@arg()`. As an example for the latter, consider the following setup:

```py
@parser.arg()  # n = 1
def integer(value: int):
    return value

@parser.arg(2, namespace={'accumulate': []})
def floats(nsp, value: float):
    nsp.accumulate.append(value)
    return nsp.accumulate

@parser.arg(..., namespace={'count': 0})
def num_rest(nsp, _):
    nsp.count += 1
    return str(nsp.count)
```

If this parser.parse() is invoked with the input `1  2.7  3.6  abc  xyz`:
- The `integer` arg will take one value, the first `1`
- The `floats` arg has `n = 2`, so it will be called on each of `2.7` and `3.6` in order, each time
    appending the value to its namespace's `accumulate` list
- The `num_rest` arg simply counts everything else; it has `n = ...`, so it will consume everything
    to the right of the previous args until a subcommand or flag is encountered. It will add 1 to
    its namespace's `count` attribute for each of `abc` and `xyz`

The final namespace returned by this parse will look like this:
```
integer: 1
floats: [2.7, 3.6]
num_rest: '2'
```

Speaking of consuming, now, let's take a look at a more-involved flag-callback example. Here's one from
the [`Example`](#example) above:

```py
@parser.flag('addition')
def add(a: int = 4, *b: int):
    """Who needs a calculator"""
    return a + sum(b)
```

This demonstrates two new things: splat (`*`) parameters and default arguments. These in fact take advantage of standard Python machinery, with no additional
finagling on ergo's end: flag callbacks by design are passed as many arguments as the user gives them, up to their number of parameters, and the presence of
a splat simply brings said "number of parameters" up to `sys.maxsize` -- which, presumably, the user will always pass fewer arguments than. The presence of a
default argument, similarly, just allows the callback to not error if the user doesn't pass it all of its parameters.

If this callback were invoked as...
- `--addition 1 2`: would return `3`
- `--addition 1 2 3 4 5 ... n` would return `sum(range(1, n))` inclusive
- `--addition 1`: would return `1`
- `--addition`: would return `4` (default argument)

### More typehints
Ergo itself provides two additional typehint aids: `booly` and `auto`.

`ergo.booly`:
- The usual `bool` type isn't particularly useful as a converter, because all the strings it's going to be passed are truthy. `booly`, on the other hand,
    evaluates args that are bool ... -y: booleanlike. Returns `True` if passed any of `yes`, `y`, `true`, `t`, `1`, and `False` if passed any of `no`, `n`, `false`, `f`.
    Argument is `str.lower`ed.

`ergo.auto`:
- `auto` by itself:
    - Works identically to a normal converter, but calls `ast.literal_eval()` on the string it's passed. If an error results, meaning the string does
    not contain a literal of any sort, returns the string itself.
- `auto(*types)`:
    - Takes a series of `type` objects, and the resultant `auto` instance will too apply `ast.literal_eval()` on its argument -- but after
    this is done, it will ensure that the resultant object passes an `isinstance(object, types)` check.  
    Applying the bitwise negation operator, as in `~auto(*types)`, will cause it to instead ensure that the object passes a **`not`**`isinstance(object, types)` check.


Feel free to play around with different `parser.parse()` arguments on the below example:

```py
from ergo import auto, booly, Parser

parser = Parser()

@parser.flag()
def typehint_stuff(a: booly, b: auto, c: auto(list, tuple), d: ~auto(str)):
    return a, b, c, d
```
