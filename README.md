# Yet Another Command-Line-Argument Parser

[![Build Status](https://travis-ci.com/supposedly/jeffrey.svg?branch=master)](https://travis-ci.com/supposedly/jeffrey)
[![codecov](https://codecov.io/gh/supposedly/jeffrey/branch/master/graph/badge.svg)](https://codecov.io/gh/supposedly/jeffrey)

I'm tired of working around argparse. This suits my needs a tad better; vaguely inspired by
[discord.py](https://github.com/Rapptz/discord.py)'s brilliant
[ext.commands](http://discordpy.readthedocs.io/en/rewrite/ext/commands/index.html) framework.

[](#separator-for-pypi)

```nginx
pip install jeffrey
```

## Contents

1. [Why?](#why)
2. [The name](#the-name)
3. [Examples](#examples)
4. [Documentation](#documentation)
    1. [CLI](#cli)
    2. [Callbacks](#callbacks)
    3. [Workflow](#workflow)
    4. [Simple CLI](#simple-cli)
    5. [Typehinting goodies](#more-typehints)

[](#separator-for-pypi)


## Why?
I needed a way to define sort-of-complex interdependencies between command-line options. None of the packages
I found\* were able to handle this out of the box to an acceptable degree, so I decided to try my own hand;
I feel like the lib should be able to handle this stuff itself, without your needing to delegate roles like *"check
that these two flags aren't used at the same time as this arg"* or *"make sure all these things appear
together, or alternatively that this second thing does"* to external functions or post-parsing if-statements.

*Note: about a month after starting I discovered "[RedCLAP](https://github.com/marekjm/clap)", which did beat jeffrey
to the idea of AND/OR/XOR clumps (by the names of "requires", "wants", and "conflicts"), albeit with a very different
design philosophy overall; credit's due for (AFAIK) originating that concept, however! I also at about the same time
found [argh](https://argh.readthedocs.io/en/latest/index.html), which despite not solving the clumping issue appears
to (by pure coincidence) share a number of features with jeffrey -- but it's currently looking for maintainers and does
depend on argparse underneath (which I'm trying my best to get away from), so I'd say we're good.

Jeffrey, by the way, is still an experiment. If it really doesn't solve the same problem for you that it does for me,
I think you'd be better off trying something else -- [here's a list](https://gist.github.com/supposedly/01224262b816df21b601ab0784d5f999)
of alternatives to check out!


## The name
**Pars**ley, for **pars**ing, is called جعفری /d͡ʒæʔfæˈɾi/ in Farsi. That glottal stop is elided into a vowel in Iran,
giving /d͡ʒæːfæˈɾi/, which if you squint hard enough resembles a heavily accented pronunciation of "Jeffrey".

*Jeffrey* was originally called `ergo`. This was a bad name that wasn't related to the project one bit. My largest reason
for choosing it was that it hadn't yet been taken on PyPI, but this now meant that a project whose sole developer was also
its sole user was hogging a pretty good PyPI identifier, and so I changed it to free that spot up.

Then my first choice for a rename was `kizbra`, the name of Chinese **pars**ley (AKA cilantro, coriander) in Lebanese Arabic,
but I bounced it off of a bunch of people and their first impressions were all either strange or downright innuendo-y. That's
never fun.

So... Jeffrey.

[](#separator-for-pypi)

## Examples

```py
from jeffrey import CLI, Group

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
JeffreyNamespace(name='foo', scream='TEST TEST', verbosity=3)
>>> 
>>> cli.parse('foo -v')
# <help/usage info...>
Expected all of the following flags/arguments: 'scream', 'verbosity'
(Got 'verbosity')
>>> 
>>> cli.parse('foo --add 1 6')
JeffreyNamespace(addition=7, name='foo')
>>> 
>>> cli.parse('foo -a')  # same as `foo --add`; default short alias is first letter of name (`short=None` removes entirely)
JeffreyNamespace(addition=4, name='foo')
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

Additionally, one may use the reduced `jeffrey.simple` parser. See the [jeffrey.simple](#simple-cli) section for more.

## Documentation

### CLI
```py
from jeffrey import CLI
```
The main dish.  

`cli = CLI(desc='', flag_prefix='-', *, systemexit=True, no_help=False, propagate_unknowns=False)`

[]()
- `desc` (`str`): A short description of this program. Appears on the help screen.
- `flag_prefix` (`str`): The 'short' prefix used to reference this cli's flags from the command line. Cannot be empty.
    Derived from this as well is `CLI().long_prefix`, constructed by doubling `flag_prefix`.
- `systemexit` (`bool`): Whether, during parsing, to yield to the default behavior of capturing exceptions then printing them
    in a `SystemExit` call alongside the default help/usage info (`True`) -- or to allow exceptions to bubble up as normal (`False`).
- `no_help` (`bool`): If `True`, prevents creation of a default `h` (short) / `help` (long) flag.
- `propagate_unknowns` (`bool`): Only applies if a CLI has subcommands. Determines whether flags not recognized by a command should be
  "bubbled up" and then handled by a parent. This is only supported on a rudimentary level; flags are propagated with no arguments unless
  expressed as `--flag=VALUE` rather than `--flag VALUE`, but even that only allows for one. (This limitation is because it's impossible
  for a subcommand to know how many parameters a flag expects when the flag is unknown to it entirely.)  
  The flag-propagation mechanism in general is useful when, say, one has flags like "verbose" or "quiet" defined on the top-level CLI and
  wishes for them to be accessible in subcommands.

Methods:
- `flag` (decorator):  
    See [`Callbacks`](#callbacks) for more info.  
    
    `@cli.flag(dest=None, short=_Null, *, default=_Null, namespace=None, required=False, help=None, _='-')`
    
    []()
    - `dest` (`str`): The name this flag will be referenced by from the command line (with long prefix), as well as the name it will
        appear as in the final `CLI.parse()` output. Defaults to the decorated function's `__name__`.
    - `short` (`str`): This flag's single-character short alias, to be used from the command line with `cli.flag_prefix`. If `None`,
        no short alias will be made; if left alone (i.e. passed `jeffrey.misc._Null`), defaults to the first alphanumeric character in the
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

    `cli.parse(inp=None, *, systemexit=None, strict=False)`

    []()
    - `inp` (`str`, `list`): Input to parse args of. Converted using `shlex.split()` if given as a string. If `None`/not given,
      defaults to `sys.argv[1:]`.
    - `systemexit`: If not None, overrides the CLI-level `systemexit` attribute. Has the same meaning, then, as `CLI.systemexit`.
    - `strict`: If `True`, parses in "strict mode": Unknown flags will cause an error rather than be ignored, and a bad amount
      of arguments (too few/too many) will do the same.
- `prepare`:  
    Once used, `cli.result` will hold the return value of `cli.parse()` rather than `cli.defaults`. See [Workflow](#workflow) for more info.
    
    `cli.prepare(*args, **kwargs)`  
    *\*args, \*\*kwargs are passed to `CLI.parse()`.*

    []()
- `result` *(property)*:  
    Returns `cli.defaults` until `cli.prepare()` is used, thereafter returning the result of `cli.parse()` (as it had been called with the
    arguments passed to `prepare()`). Again, see [Workflow](#workflow) for further info.
- `defaults` *(property)*:  
    Returns the values of the `default=...` kwargs set from `cli.flag` and `cli.arg` as an `JeffreyNamespace` object.
- `__setattr__`:  
    CLI objects have `__setattr__` overridden to facilitate the creation of "groups", which apply their clump settings to themselves
    as a whole rather than each of their members individually. Entities can also be clumped within groups.
    
    `cli.group_name_here = Group(*, required=False, AND=_Null, OR=_Null, XOR=_Null)`  
    *See identical args of `flag` and `clump`.*

    If the R-value is not an `jeffrey.Group` instance, the setattr call will go through normally.

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
finagling on jeffrey's end: flag callbacks by design are passed as many arguments as the user gives them, up to their number of parameters, and the presence of
a splat simply brings said "number of parameters" up to `sys.maxsize` -- which, presumably, the user will always pass fewer arguments than. The presence of a
default argument, similarly, just allows the callback to not error if the user doesn't pass it all of its parameters.

If this callback were invoked as...
- `--addition 1 2`: would return `3`
- `--addition 1 2 3 4 5 ... n`: would return `sum(range(1, n))` inclusive
- `--addition 1`: would return `1`
- `--addition`: would return `4` (default argument)

### Workflow
Jeffrey allows your whole package to center in functionality around its CLI.  
I don't quite know if that's good or bad design&nbsp;-- leaning toward "bad", perhaps, because I only
needed it for a package that started as a command-line script and grew awkwardly into an importable
module&nbsp;-- but it certainly works, and it hasn't been particularly disagreeable IMO.

Here's the deal: in a small script, one that's (say) only a few files and meant to be run from the command line
rather than being imported, it suffices to define `cli = jeffrey.CLI(...)` and then call `cli.parse()` to get
your input values. However, in a larger package distributed both as a CLI script *and* an importable Python module, a 'problem'
arises: the module will try to read from the command line even if it's only being imported,
leading to errors when it doesn't find in `sys.argv` what it thinks it needs to. This is what `__name__ == '__main__'`
is for, of course, but *then*... what to do with the CLI? Should it be separated, hooking into the main module
and compiling command-line output itself? Or should things go the other way around, with the module hooking into
the CLI and making use of default values to 'fill in the gaps'?

The former is probably the usual way to do things, and any command-line-parsing utility of course allows it by
default. Jeffrey facilitates the latter, too, though. It has three parts to it:

- `cli.result`. A property of `jeffrey.CLI()` objects that, up until `cli.prepare()` is called, only returns default values.
- `cli.prepare()`. Prepares this CLI to parse from the command line *rather than* use default values: specifically,
  causes `cli.result` to call `cli.parse()` the next time it's accessed, returning only those values from then on. This
  method should be called from the main command-line entry point, keeping it untouched if the module is imported.
- `cli.set_defaults()`. Changes the CLI's default values, but importantly: if only called from the command-line entry point, allows
  separation of "command-line defaults" from "module defaults", with the defaults set in this function being command-line-level
  and the defaults set via `@cli.command()` and `@cli.flag()` being the module-level. This is useful, for example, in the
  implementation of a `-q`/`--quiet` flag: when imported as a module the `-q` flag should be set by default, but
  when used from the command line it should only become set if the user sets it.

The module as a whole can use `cli.result` to grab important values, and if `cli.prepare()` and `cli.set_defaults()` are used
correctly, this structure will result in the module's behaving seamlessly regardless of whether it was invoked directly from
the command line or whether it was imported.

Here's an example:

```py
# cli.py
from jeffrey import CLI

cli = CLI('Demo')

@cli.flag(default=False)  # module default: when imported, this module should print nothing
def quiet():
    return True

@cli.arg(default='default value')
def important_value(value):
    return value

...
```
```py
# main file
from modulename.cli import cli

...


def main():
    if not cli.quiet:
        print('hello!')
    do_something_with(cli.result.important_value)


if __name__ == '__main__':
    cli \
      # tell cli.result to call cli.parse() the next time it's used,
      # rather than returning defaults
      .prepare() \
      # set `quiet` to be false by default, because the script is being run from the
      # command line (where output by default is acceptable) rather than being imported
      .set_defaults(quiet=False)
    main()
```
```py
# Any other file
from modulename.cli import cli

def bar():
    # Will be none the wiser as to whether cli.result.important_value
    # gives important_value's default or input from the command line
    do_something_with(cli.result.important_value)

...
```

### Simple CLI

_**NOTE: jeffrey.simple will be deprecated soon -- or, at the very least, demoted to "recipe" status.**_

As an alternative to the full `jeffrey.CLI` parser, one may use (as mentioned above) a reduced form of it, dubbed `jeffrey.simple`. It works as follows:

```py
import jeffrey

@jeffrey.simple
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

`jeffrey.simple` has no concept of AND/OR/XOR clumps, so it isn't suitable for an application requiring those. It also, rather than being only a *parsing*
tool, somewhat submits to the "click philosophy" of intertwining argument parsing with the actual program execution: rather than assign each individual
option a function processing only its own value and provide these values to the user without caring what happens afterward (as the standard `jeffrey.CLI`
does), it expects the actual functions of a given program to be decorated and passes CLI arguments to them directly. This is a bit iffy, but it does
make for less boilerplate... overall, however, `jeffrey.CLI` should be preferred when possible.

Its implementation works because Python already has syntax to define positional parameters and name-only parameters in a function; positional options
& flags on a command line can be likened to these easily. Currently, however, `jeffrey.simple` cannot handle **kwargs by taking arbitrary flags. If that
turns out to be a necessity at some point down the line, this will change.

If one should wish to configure their new `jeffrey.simple` objects, the following class attributes are reassignable:

- `jeffrey.simple._` (`str`): As in `CLI.flag`, this value controls what the `_` character in a Python identifier's name will be replaced with on the command line.
- `jeffrey.simple.flag_prefix` (`str`): Identical to `flag_prefix` in `CLI.__init__()`.
- `jeffrey.simple.no_help` (`bool`): Identical to `no_help` in `CLI.__init__()`.
- `jeffrey.simple.short_flags` (`bool`): Determines whether to create short aliases out of keyword-parameter names (e.g. `flag` becoming both `--flag` and `-f`).

Note that changing these will not change their values for already-instantiated objects.  
Note also that decorated functions still define `__call__`, so they can be called as normal rather than with `.run()` or `.search()`.


### More typehints
Jeffrey itself provides two additional typehint aids: `booly` and `auto`.

`jeffrey.booly`:
- The usual `bool` type isn't particularly useful as a converter, because all the strings it's going to be passed are truthy. `booly`, on the other hand,
    evaluates args that are bool ... -y: booleanlike. Returns `True` if passed any of `yes`, `y`, `true`, `t`, `1`, and `False` if passed any of `no`, `n`, `false`, `f`.
    Argument is `str.lower`ed.

`jeffrey.auto`:
- `auto` by itself:
    - Works identically to a normal converter, but calls `ast.literal_eval()` on the string it's passed. If an error results, meaning the string does
    not contain a literal of any sort, returns the string itself.
- `auto(*types)`:
    - Takes a series of `type` objects, and the resultant `auto` instance will too apply `ast.literal_eval()` on its argument -- but after
    this is done, it will ensure that the resultant object passes an `isinstance(object, types)` check.  
    Applying the bitwise negation operator, as in `~auto(*types)`, will cause it to instead ensure that the object passes a **`not`**`isinstance(object, types)` check.


Feel free to play around with different `cli.parse()` arguments on the below example:

```py
from jeffrey import auto, booly, CLI

cli = CLI()

@cli.flag()
def typehint_stuff(a: booly, b: auto, c: auto(list, tuple), d: ~auto(str)):
    return a, b, c, d
```
