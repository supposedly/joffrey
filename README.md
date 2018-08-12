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

1. [Why?](#why)
2. [Examples](#examples)
3. [Documentation](#documentation)
    1. [CLI](#cli)
    2. [Callbacks](#callbacks)
    3. [Simple CLI](#simple-cli)
    4. [Typehinting goodies](#more-typehints)

[](#separator-for-pypi)


## Why?
I needed a way to define sort-of-complex interdependencies between command-line options. None of the packages
I found\* were able to handle this out of the box to an acceptable degree, so I decided to try my own hand;
I feel like the lib should be able to handle this stuff itself, without your needing to delegate roles like *"check
that these two flags aren't used at the same time as this arg"* or *"make sure all these things appear
together, or alternatively that this second thing does"* to external functions or post-parsing if-statements.

*Note: about a month after starting I discovered "[RedCLAP](https://github.com/marekjm/clap)", which did beat ergo
to the idea of AND/OR/XOR clumps (by the names of "requires", "wants", and "conflicts"), albeit with a very different
design philosophy overall; credit's due for (AFAIK) originating that concept, however! I also at about the same time
found [argh](https://argh.readthedocs.io/en/latest/index.html), which despite not solving the clumping issue appears
to (by pure coincidence) share a number of features with ergo -- but it's currently looking for maintainers and does
depend on argparse underneath (which I'm trying my best to get away from), so I'd say we're good.

Ergo, by the way, is still early in alpha. If it really doesn't solve the same problem for you that it does for me,
I think you'd be better off trying something else; docopt, for example, is superb, and Fire's no-assembly-required
philosophy is quite fun in its own right.  
I also, in full disclosure, don't too much enjoy the design of a lot of current argparse-like solutions (really, most
of them except docopt). As such, in addition to aiding in the creation of such interdependent systems as mentioned
above, ergo's also my shot at making something that's just enjoyable to work with. Time will have to tell whether it
succeeds!

[](#separator-for-pypi)

## Examples

```py
from ergo import CLI, Group

cli = CLI('Quick demo program')
# CLI.__setattr__() on Group objects is special-cased slightly
cli.sc = Group(XOR=0)  # 0 is just an identifier; it can be anything


@cli.arg()
def name(name):
    """Args, positional, are parsed in the order they're added in"""
    return name

@cli.sc.clump(AND='blah')
@cli.sc.flag(short='S')
def scream(text):
    """I have no mouth and I must ... yeah"""
    return text.upper()

@cli.sc.clump(AND='blah')  # this flag and `scream` *must* appear together (same AND)
@cli.sc.flag('verbosity', namespace={'count': 0})
def verbose(nsp):
    """This does nothing but it shows namespaces (which are always passed as the first arg)"""
    if nsp.count < 3:
        nsp.count += 1
    return nsp.count

@cli.clump(XOR=0)  # this flag *cannot* appear alongside any in group `sc` (same XOR)
@cli.flag('addition')
def add(a: int = 4, *b: int):  # can also provide default args and a type-coercion hint if needed
    """Who needs a calculator"""
    return a + sum(b)
```
```py
>>> cli.parse('foo -S "test test" -vvvv')  # input will be shlex.split if given as a string (defaults to sys.argv though)
ErgoNamespace(name='foo', scream='TEST TEST', verbosity=3)
>>> 
>>> cli.parse('foo -v')
# <help/usage info...>
Expected all of the following flags/arguments: 'scream', 'verbosity'
(Got 'verbosity')
>>> 
>>> cli.parse('foo --add 1 6')
ErgoNamespace(addition=7, name='foo')
>>> 
>>> cli.parse('foo -a')  # same as `foo --add`; default short alias is first letter of name (`short=None` removes entirely)
ErgoNamespace(addition=4, name='foo')
>>> 
>>> cli.parse('foo -a 1 2 -S "this is gonna error" -v')
# <help/usage info...>
Expected no more than one of the following flags/arguments: 'addition', ['scream', 'verbosity']
(Got 'addition', ['scream', 'verbosity'])
>>> 
>>> # etc
```
And the mysterious `help/usage info...`:
```
Quick demo program

usage: <filename here> [-h | --help (NAME)] [-a | --addition (A) B...] [-S | --scream TEXT] [-v | --verbosity] name(1)

ARGS
	name            Args, positional, are parsed in the order they're added in
FLAGS
	scream          I have no mouth and I must ... yeah
	addition        Who needs a calculator
	help            Prints help and exits
	verbosity       This does nothing but it shows namespaces (which are always passed as the first arg)
```
(To get rid of the default `help` flag, pass `no_help=True` to `CLI()`)

Additionally, one may use the reduced `ergo.simple` parser. See the [ergo.simple](#ergo-simple) section for more.

## Documentation

### CLI
```py
from ergo import CLI
```
The main dish.  

`cli = CLI(desc='', flag_prefix='-', *, systemexit=True, no_help=False)`

[]()
- `desc` (`str`): A short description of this program. Appears on the help screen.
- `flag_prefix` (`str`): The 'short' prefix used to reference this cli's flags from the command line. Cannot be empty.
    Derived from this as well is `CLI().long_prefix`, constructed by doubling `flag_prefix`.
- `systemexit` (`bool`): Whether, during parsing, to yield to the default behavior of capturing exceptions then printing them
    in a `SystemExit` call alongside the default help/usage info (`True`) -- or to allow exceptions to bubble up as normal (`False`).
- `no_help` (`bool`): If `True`, prevents creation of a default `h` (short) / `help` (long) flag.

Methods:
- `flag` (decorator):  
    See [`Callbacks`](#callbacks) for more info.  
    
    `@cli.flag(dest=None, short=_Null, *, default=_Null, namespace=None, required=False, help=None, _='-')`
    
    []()
    - `dest` (`str`): The name this flag will be referenced by from the command line (with long prefix), as well as the name it will
        appear as in the final `CLI.parse()` output. Defaults to the decorated function's `__name__`.
    - `short` (`str`): This flag's single-character short alias, to be used from the command line with `cli.flag_prefix`. If `None`,
        no short alias will be made; if left alone (i.e. passed `ergo.misc._Null`), defaults to the first alphanumeric character in the
        decorated function's `__name__`.
    - `default`: Default value of this flag if not invoked during parsing. (no default value if `_Null`)
    - `namespace` (`dict`): The starting values for this flag's "namespace", a `types.SimpleNamespace` object passed as the first argument
        to the decorated function. Can be used to store values between repeated flag invocations. If `None`, no namespace will be created
        or passed to said function.
    - `required` (`bool`): Whether to error if this flag is not provided (independent of clump settings; do not use this with `XOR`, for instance).
    - `help`: Help text to appear alongside this flag. If not provided, will be grabbed if present from the decorated function's `__doc__`.
    - `_`: Determines how to replace underscores in the flag's name (be the name from `dest` or the function's `__name__`). Default `'-'`, meaning
        that a flag named `check_twice` will be invoked as `--check-twice` (or if `_='.'`, then `--check.twice`). Final output will still use the
        original pre-replacement name, however.
- `arg` (decorator):  
    See [`Callbacks`](#callbacks) for more info.  
    
    `@cli.arg(n=1, *, namespace=None, required=False, help=None, _='-')`  
    *See identical args of `flag`.*
    
    []()
    - `n` (`int`, Ellipsis): How many times this argument should be repeated. If `n` is 2, for example,
        the decorated function will be called on two consecutively-passed command-line arguments.  
    You can use the `namespace`, as in `flag`, to store info about this argument's values betweeen
    calls.
    If `n` is `...` or `Ellipsis`, this arg will consume as many arguments as it can (excluding flags)
    before reaching either a flag or a subcommand.  
    Intended to be used as a positional argument, as in `@cli.arg(2)` or `@cli.arg(...)`.
- `clump` (decorator):  
    Each component (AND, OR, XOR) takes an identifier, and any other entity bound to this cli with
    the same identifier is considered part of the same clump.  
    
    `@cli.clump(AND=_Null, OR=_Null, XOR=_Null)`
    
    []()
    - `AND`: Clumps together entities that *must* appear together. An ANDed entity is excused from being invoked if it is
        part of a satisfied OR clump (i.e. at least one other member of its OR clump appeared) or a satisfied XOR clump (i.e.
        exactly one other member of its XOR clump appeared).
    - `OR`: Clumps together entities of which *at least one* must appear. An ORed entity is excused from being invoked if it is
        part of a satisfied XOR clump (i.e. exactly one other member of its XOR clump appeared).
    - `XOR`: Clumps together entities of which *at most one* can appear. An XORed entity is allowed to appear alongside more than one
        other if it satisfies an AND clump (i.e. all other members of its AND clump appeared).
- `command`:  
    Returns a sub-command of this cli. When a command is detected in parsing input, parsing of its parent's options is abandoned and everything
    to the right is passed to the subcommand instance.  
    
    `cli.command(name, desc='', *args, aliases=(), from_cli=None, AND=_Null, OR=_Null, XOR=_Null, _='-', **kwargs)`  
    *See identical args of `flag` and `clump`.*  
    *\*args, \*\*kwargs are passed to `CLI.__init__()`.*
    
    []()
    - `name` (`str`): The name with which this command is to be invoked from the command line, as well as the name under which its final parsed
        output will appear in its parent's.
    - `aliases` (`tuple`): Alternative names with which this command can be invoked.
    - `from_cli` (`CLI`): If given, creates a command instance from an existing top-level CLI or command and binds it to this top-level CLI or command.
- `remove`:
    Removes an entity from the CLI, be it an arg, flag, or command.

    `cli.remove(name)`

    []()
    - `name` (`str`, `Entity`): Name of arg to remove. If passed an Entity instance, uses its name instead.
- `parse`:
    Applies cli's args/flags/commands/groups/clumps to its given input.

    `cli.parse(inp=sys.argv[1:], *, systemexit=None, strict=False, require_main=False, ignore_pkgs=None)`

    []()
    - `inp` (`str`, `list`): Input to parse args of. Converted using `shlex.split()` if given as a string.
    - `systemexit`: If not None, overrides the CLI-level `systemexit` attribute. Has the same meaning, then, as `CLI.systemexit`.
    - `strict`: If `True`, parses in "strict mode": Unknown flags will cause an error rather than be ignored, and a bad amount
      of arguments (too few/too many) will do the same.
    - `require_main` (`bool`, `int`): If set, *only* executes the parse if the module it's being used from is `__main__`, determined
      by peeking up the stack. This can optionally be an integer instead of a boolean `True`, in which case it represents the amount of
      stack frames (relative to the ergo module itself) to cover before checking that its `__name__` equals `'__main__'` (anything related
      to the importlib stack is ignored). Hence, if this is `True` or `1` then the module importing ergo will be checked; if it is `2` then
      the module importing that module will be checked; and so on.
    - `ignore_pkgs` (`tuple`): Tuple of package-name prefixes to ignore when counting stack frames for `require_main`. If `None`, will
      ignore packages whose names start with `'importlib'` or `'pkg_resources'` (a.k.a. default behavior).
- `__setattr__`:  
    CLI objects have `__setattr__` overridden to facilitate the creation of "groups", which apply their clump settings to themselves
    as a whole rather than each of their members individually. Entities can also be clumped within groups.
    
    `cli.group_name_here = Group(*, required=False, AND=_Null, OR=_Null, XOR=_Null)`  
    *See identical args of `flag` and `clump`.*

    If the R-value is not an `ergo.Group` instance, the setattr call will go through normally.

    After the creation of a group, its methods such as `clump` (for internal clumping) can be accessed as `@cli.group_name_here.clump()`;
    others are `arg`, `flag`, and `command`.


### Callbacks
`CLI.flag` and `CLI.arg` decorate functions; these functions are subsequently called when their flag/arg's name is detected during parsing.

If a callback's parameters are [type-hinted](https://www.python.org/dev/peps/pep-3107/), the arguments passed will attempt to be "converted" by
these typehints. That is, if the hint is a callable object, it will be called on a command-line argument passed in that spot. Consider the
following flag:

```py
@cli.flag('addition')
def add(a: int, b: int):
    """Who needs a calculator"""
    return a + b
```

If this flag is invoked from the command line as `--addition 1 2`, each of `1` and `2` will be given (as a string) to the `int` typehint and thus passed into
the `add()` function as an integer. (No error would result if the hint were not callable; the command-line value would simply not be converted from a string)

The number of arguments to be passed to a *flag* is determined by the number of parameters its function has; *args*, on the other hand, **always pass one value** to their callbacks. Flag callbacks are called as many times as the user
writes the flag's name, and arg callbacks are called as many times as indicated by the `n` argument in `@arg()`. As an example for the latter, consider the following setup:

```py
@cli.arg()  # n = 1
def integer(value: int):
    return value

@cli.arg(2, namespace={'accumulate': []})
def floats(nsp, value: float):
    nsp.accumulate.append(value)
    return nsp.accumulate

@cli.arg(..., namespace={'count': 0})
def num_rest(nsp, _):
    nsp.count += 1
    return str(nsp.count)
```

If this cli.parse() is invoked with the input `1   2.7   3.6   abc   xyz`:
- The `integer` arg will take one value, the first `1`
- The `floats` arg has `n = 2`, so it will be called on each of `2.7` and `3.6` in order, each time
    appending the value to its namespace's `accumulate` list
- The `num_rest` arg simply counts everything else; it has `n = ...`, so it will consume everything
    to the right of the previous args, excluding flags, until a subcommand or EOF is encountered. It will add 1 to
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
@cli.flag('addition')
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
- `--addition 1 2 3 4 5 ... n`: would return `sum(range(1, n))` inclusive
- `--addition 1`: would return `1`
- `--addition`: would return `4` (default argument)

### Simple CLI

As an alternative to the full `ergo.CLI` parser, one may use (as mentioned above) a reduced form of it, dubbed `ergo.simple`. It works as follows:

```py
import ergo

@ergo.simple
def main(positional, *consuming, flag):
    """Simple-CLI demo"""
    print('MAIN:', positional, consuming, flag)

@main.command
def cmd(conv: list = None, *, flag: str.upper):
    """Subcommand of main"""
    print('CMD:', conv, flag)

@cmd.command
def subcmd(*consuming: set, flag: str.lower):
    """Subcommand of the subcommand"""
    print('SUBCMD:', consuming, flag)
```
```py
# Simple CLIs can be run on a string (which will be shlex.split), list, or None/nothing -> sys.argv[1:]
>>> main.run('one two three four --flag five')
MAIN: one ('two', 'three', 'four') five
# Flags get their short aliases; commands are usable as normal
>>> main.run('hhh -f value cmd test -f screamed')
MAIN: hhh () value
CMD: ['t', 'e', 's', 't'] SCREAMED
# Default argument means no value is required; commands can also be run directly
>>> cmd.run('-f uppercase')
CMD: None UPPERCASE
# Commands can be nested arbitrarily
>>> main.run('none -f none cmd -f none subcmd sets sets -f WHISPER')
MAIN: none () none
CMD: None NONE
SUBCMD: ({'s', 'e', 't'}, {'s', 'e', 't'}) whisper
# Commands can also search for their own name in input and run themselves
# (rudimentary search, though: skips flag values, but not positional arguments)
>>> subcmd.search('none -f subcmd cmd -f none subcmd sets sets -f WHISPER')
SUBCMD: ({'s', 'e', 't'}, {'s', 'e', 't'}) whisper
```

`ergo.simple` has no concept of AND/OR/XOR clumps, so it isn't suitable for an application requiring those. It also, rather than being only a *parsing*
tool, somewhat submits to the "click philosophy" of intertwining argument parsing with the actual program execution: rather than assign each individual
option a function processing only its own value and provide these values to the user without caring what happens afterward (as the standard `ergo.CLI`
does), it expects the actual functions of a given program to be decorated and passes CLI arguments to them directly. This is a bit iffy, but it does
make for less boilerplate... overall, however, `ergo.CLI` should be preferred when possible.

Its implementation works because Python already has syntax to define positional parameters and name-only parameters in a function; positional options
& flags on a command line can be likened to these easily. Currently, however, `ergo.simple` cannot handle **kwargs by taking arbitrary flags. If that
turns out to be a necessity at some point down the line, this will change.

If one should wish to configure their new `ergo.simple` objects, the following class attributes are reassignable:

- `ergo.simple._` (`str`): As in `CLI.flag`, this value controls what the `_` character in a Python identifier's name will be replaced with on the command line.
- `ergo.simple.flag_prefix` (`str`): Identical to `flag_prefix` in `CLI.__init__()`.
- `ergo.simple.no_help` (`bool`): Identical to `no_help` in `CLI.__init__()`.
- `ergo.simple.short_flags` (`bool`): Determines whether to create short aliases out of keyword-parameter names (e.g. `flag` becoming both `--flag` and `-f`).

Note that changing these will not change their values for already-instantiated objects.  
Note also that decorated functions still define `__call__`, so they can be called as normal rather than with `.run()` or `.search()`.


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


Feel free to play around with different `cli.parse()` arguments on the below example:

```py
from ergo import auto, booly, CLI

cli = CLI()

@cli.flag()
def typehint_stuff(a: booly, b: auto, c: auto(list, tuple), d: ~auto(str)):
    return a, b, c, d
```
