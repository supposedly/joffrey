# Yet Another Command-Line-Argument Parser

**Please note that this project was last updated in December 2018. It still works (at least until PEP 563 gets merged),
but argparse has probably gotten better in the meantime. The rest of this README is written as if it's still December 2018.**

[![Build Status](https://travis-ci.com/supposedly/joffrey.svg?branch=master)](https://travis-ci.com/supposedly/joffrey)
[![codecov](https://codecov.io/gh/supposedly/joffrey/branch/master/graph/badge.svg)](https://codecov.io/gh/supposedly/joffrey) <sub>(if the build is failing that's a lie)</sub>

I'm tired of working around argparse. This suits my needs a bit better; vaguely inspired by
[discord.py](https://github.com/Rapptz/discord.py)'s brilliant
[ext.commands](http://discordpy.readthedocs.io/en/rewrite/ext/commands/index.html) framework.

[](#separator-for-pypi)

```nginx
pip install joffrey
```

## Contents

1. [Why?](#why)
2. [Examples](#examples)
3. [Documentation](#documentation)
    1. [CLI](#cli)
    2. [Callbacks](#callbacks)
    3. [Workflow](#workflow)
    4. [Simple CLI](#simple-cli)
    5. [Typehinting goodies](#more-typehints)

[](#separator-for-pypi)

## Why?
I needed a way to define sort-of-complex interdependencies between command-line options. None of the packages
I found\* were able to handle this out of the box to an acceptable degree, so I decided to try my own hand;
I feel like your library should be able to handle this stuff itself, without your needing to delegate roles like
*"check that these two flags aren't used at the same time as this arg"* or *"make sure all these things appear
together, or if not, that this other thing does"* to external functions or post-parsing if-statements.

\*Note: about a month after starting I discovered "[RedCLAP](https://github.com/marekjm/clap)", which did beat Joffrey
to the idea of AND/OR/XOR clumps (by the names of "requires", "wants", and "conflicts"), albeit with a very different
design philosophy overall. Credit's due for (AFAIK) originating that concept! At about the same time, I also found
found [argh](https://argh.readthedocs.io/en/latest/index.html), which coincidentally shares a lot of features with
Joffrey -- it does depend on argparse underneath, though, and I'm trying my best to get away from it.

Joffrey's still an experiment, by the way. If it really doesn't solve the same problem for you that it does for me,
I think you'd be better off trying something else -- [here's a list](https://gist.github.com/supposedly/01224262b816df21b601ab0784d5f999)
of alternatives to check out.

[](#separator-for-pypi)

## Examples

```py
from joffrey import CLI, Group

cli = CLI('Quick demo program')
# CLI.__setattr__() on Group objects is special-cased slightly
cli.sc = Group(XOR=0)
# that 0 can be anything at all; the important thing is for other objects to use
# the same value for XOR if they want to be XOR'd against this one


@cli.arg()
def name(name):
    """Args, positional, are parsed in the order they're defined in"""
    return name

@cli.sc.clump(AND='blah')
@cli.sc.flag(short='S')
def scream(text):
    """This is a flag, and its function gets called whenever it's encountered in input"""
    return text.upper()

@cli.sc.clump(AND='blah')  # this flag and `scream` *must* appear together (same AND)
@cli.sc.flag('verbosity', namespace={'count': 0})
def verbose(nsp):
    """This flag does nothing, but it shows how namespaces work"""
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
JoffreyNamespace(name='foo', scream='TEST TEST', verbosity=3)
>>> 
>>> cli.parse('foo -v')
# <help/usage info...>
Expected all of the following flags/arguments: 'scream', 'verbosity'
(Got 'verbosity')
>>> 
>>> cli.parse('foo --add 1 6')
JoffreyNamespace(addition=7, name='foo')
>>> 
>>> cli.parse('foo -a')  # same as `foo --add`; default short alias is first letter of name (`short=None` removes entirely)
JoffreyNamespace(addition=4, name='foo')
>>> 
>>> cli.parse('foo -a 1 2 -S "this is gonna error" -v')
# <help/usage info...>
Expected no more than one of the following flags/arguments: 'addition', ['scream', 'verbosity']
(Got 'addition', ['scream', 'verbosity'])
>>> 
>>> # etc
```
Here's what that `<help/usage info...>` actually looks like:
```
Quick demo program

usage: <filename here> [-h | --help (NAME)] [-a | --addition (A) B...] [-S | --scream TEXT] [-v | --verbosity] name(1)

ARGS
	name            Args, positional, are parsed in the order they're added in
FLAGS
	scream          This is a flag, and its function gets called whenever it's encountered in input
	addition        Who needs a calculator
	help            Prints help and exits
	verbosity       This flag does nothing, but it shows how namespaces work
```
(To get rid of the default `help` flag, pass `no_help=True` to `CLI()`)

You might alternatively want to check out the reduced `joffrey.simple` parser. See the [joffrey.simple](#simple-cli) section for more.

## Documentation

### CLI
```py
from joffrey import CLI
```
The main dish.  

`cli = CLI(desc='', flag_prefix='-', *, systemexit=True, no_help=False, propagate_unknowns=False)`

[]()
- `desc` (`str`): A short description of this program. Appears on the help screen.
- `flag_prefix` (`str`): The 'short' prefix used to reference this cli's flags from the command line. It can't be empty.
    `CLI().long_prefix` is automatically derived as two `flag_prefix`es back-to-back.
- `systemexit` (`bool`): Whether to capture exceptions and print them in a `SystemExit` call alongside the default help/usage
   info (`True`) -- or to allow exceptions to bubble up like in a normal Python program (`False`).
- `no_help` (`bool`): Whether to nix the `h` (short) / `help` (long) flag that's created by default.
- `propagate_unknowns` (`bool`): Only applies if a CLI has subcommands. Determines whether flags that a command doesn't recognize should be
  "bubbled up" and then handled by a parent. This is only supported on a rudimentary level; flags' arguments aren't bubbled up at all unless
  they get expressed as `--flag=VALUE` rather than `--flag VALUE`, but even that only allows for one argument. (This limitation is because
  it's impossible for a subcommand to know how many parameters a flag expects when it doesn't even know the flag in the first place.)  
  The flag-propagation mechanism is useful when, say, you've got flags like "verbose" or "quiet" defined on the top-level CLI and
  want them to be accessible in subcommands.

Methods:
- `flag` (decorator):  
    See [`Callbacks`](#callbacks) for more info.  
    
    `@cli.flag(dest=None, short=_Null, *, default=_Null, namespace=None, required=False, help=None, _='-')`
    
    []()
    - `dest` (`str`): The name this flag will be referenced by from the command line (with long prefix), as well as the name it'll get
        in the final `CLI.parse()` output. Defaults to the decorated function's `__name__`.
    - `short` (`str`): The single-character alias for this flag, which goes with `cli.flag_prefix` in command-line input. If `short=None`,
        this flag won't have a short alias; if `short` isn't given at all (i.e. if `short=joffrey.misc._Null`), it defaults to the first
	alphanumeric character in the decorated function's `__name__`.
    - `default`: The default value this flag ends up with if it's not encountered at all in input. (If `default` isn't given at all,
      there'll be no default value, and this flag won't show up in the final output if it's not encountered.)
    - `namespace` (`dict`): The starting values for this flag's "namespace", a `types.SimpleNamespace` object passed into the decorated
      function's first argument. The namespace can store values between repeated flag invocations. If `None` or not given, no namespace
      will be created or passed to the function.
    - `required` (`bool`): Whether to error if this flag isn't provided (independent of any clump business; for example, don't use
      `required=True` with `XOR`). Defaults to `False`.
    - `help`: A description that'll appear alongside this flag in the parser's help/usage info. If not given, it'll be filled in with
       the decorated function's `__doc__`.
    - `_`: Determines how to replace underscores in the flag's name (whether the name's from `dest` or the function's `__name__`) on
      the command line. Defaults to `'-'`, meaning that a flag named `check_twice` can be invoked as `--check-twice`. If `_='.'`,
      for example, then that'll be `--check.twice`.
- `arg` (decorator):  
    See [`Callbacks`](#callbacks) for more info.  
    
    `@cli.arg(n=1, *, namespace=None, required=False, help=None, _='-')`  
    *See identical args of `flag`.*
    
    []()
    - `n` (`int`, Ellipsis): How many times this argument should be repeated. If `n` is 2, for example,
      the decorated function will consume two command-line arguments in a row. You can use `namespace`,
      as in `@cli.flag` above, to store info about this argument's values betweeen calls.  
      If `n` is `...` (or `Ellipsis`), this arg will consume as many arguments as it can before reaching either
      a flag or a subcommand.  
      This should be passed as a positional argument for style points, as in `@cli.arg(2)` or `@cli.arg(...)`.
- `clump` (decorator):  
    Clumps this in with other entities. Each component of a clump (AND, OR, XOR) takes an identifier, and any thing else clumped
    in with the same identifier and the same component will count as part of the same "clump".
    
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
    Creates and returns a sub-command of this CLI. When a command is detected in parsing input, its parent's options stop getting
    parsed, and everything rightwards gets parsed by the subcommand instance instead.  
    
    `cli.command(name, desc='', *args, aliases=(), from_cli=None, AND=_Null, OR=_Null, XOR=_Null, _='-', **kwargs)`  
    *See identical args of `flag` and `clump`.*  
    *\*args, \*\*kwargs are passed to `CLI.__init__()`.*
    
    []()
    - `name` (`str`): The name this command can be invoked with from the command line.
    - `aliases` (`tuple`): Alternative names this command can be invoked with.
    - `from_cli` (`CLI`): If given, creates a command instance from an existing top-level CLI or command and binds it to this top-level CLI or command.
- `remove`:  
    Removes an entity from the CLI, whether an arg, flag, or command.

    `cli.remove(name)`

    []()
    - `name` (`str`, `Entity`): Name of arg to remove. If passed an Entity instance, uses its name instead.
- `parse`:  
    Applies cli's args/flags/commands/groups/clumps to its given input.

    `cli.parse(inp=None, *, systemexit=None, strict=False)`

    []()
    - `inp` (`str`, `list`): Input to parse args of. Converted using `shlex.split()` if given as a string. If `None`/not given,
      defaults to `sys.argv[1:]`.
    - `systemexit`: If not None, overrides the CLI-level `systemexit` attribute. That means it means the same thing as `CLI.systemexit`.
    - `strict`: If `True`, parses in "strict mode": unknown flags will cause an error instead of getting ignored, and a bad amount
      of arguments (too few/too many) will also cause an error.
- `prepare`:  
    Once this is called, `cli.result` will hold the return value of `cli.parse()` rather than `cli.defaults`. See [Workflow](#workflow) for more info.
    
    `cli.prepare(*args, **kwargs)`  
    *\*args, \*\*kwargs are passed to `CLI.parse()`.*

    []()
- `result` *(property)*:  
    Returns `cli.defaults` until `cli.prepare()` is used, after which point it'll return the result of `cli.parse()` (as if it'd been called with the
    arguments passed to `prepare()`). Again, see [Workflow](#workflow) for more.
- `defaults` *(property)*:  
    Returns the values of the `default=...` kwargs set from `cli.flag` and `cli.arg` as a `JoffreyNamespace` object.
- `__setattr__`:  
    CLI objects have `__setattr__` overridden to help with creating "groups" of enities, which apply their clump settings to themselves
    as a whole rather than each of their members individually. Entities can also be clumped within groups.
    
    `cli.group_name_here = Group(*, required=False, AND=_Null, OR=_Null, XOR=_Null)`  
    *See identical args of `flag` and `clump`.*

    If the R-value isn't a `joffrey.Group` instance, the setattr call will go through normally.

    After the creation of a group, its methods can be accessed as `@cli.group_name_here.method()` (methods being `.clump()`,
    `.arg()`, `.flag()`, and `.command()`. Using `.clump()` clumps the members of a group internally.)

### Callbacks

**This stuff is based on the original "do whatever you want with em" philosophy that Python's typehints came with.
It'll break once PEP 563 is merged if I forget to update the code to work around it.**

`CLI.flag` and `CLI.arg` decorate functions, which get called when their flag/arg's name is detected during parsing.

If a callback's parameters are [type-hinted](https://www.python.org/dev/peps/pep-3107/), the arguments passed will try to be "converted" by
those typehints. In other words, if the hint is a callable object, it'll be called on any command-line argument passed in that spot. Consider this:

```py
@cli.flag('addition')
def add(a: int, b: int):
    """Who needs a calculator"""
    return a + b
```

If this flag is invoked from the command line as `--addition 1 2`, each of `1` and `2` will be given (as a string) to the `int()`, which'll let them be passed into
the `add()` function as an integer. (There wouldn't be an error if the hint weren't callable; the command-line value would just keep being a string)

The number of arguments to be passed to a *flag* is determined by the number of parameters its function has; *args*, on the other hand, **always pass one value** to their callbacks. Flag callbacks are called as many times as the user
writes the flag's name, and arg callbacks are called as many times as indicated by the `n` argument in `@arg()`. As an example for the latter, look at this setup:

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

If cli.parse() is invoked with the input `1   2.7   3.6   abc   xyz`:
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

This demonstrates two new things: splat (`*`) parameters and default arguments. They both work just like in normal Python: splat
parameters let you pass in as many arguments as you like, and default parameters allow your parser not to error if it doesn' get
an argument it was expecting.

If that callback were invoked as...
- `--addition 1 2`: would return `3`
- `--addition 1 2 3 4 5 ... n`: would return `sum(range(1, n))` inclusive
- `--addition 1`: would return `1`
- `--addition`: would return `4` (default argument)

### Workflow
Joffrey allows your whole package to center in functionality around its CLI.  
I don't quite know if that's good or bad design&nbsp;-- leaning toward "bad", maybe, because I only
needed it for a package that started as a command-line script and grew really awkwardly into an importable
module&nbsp;-- but it definitely works, and it hasn't been that disagreeable IMHO.

Here's the deal: in a small script, one that's (say) only a few files and meant to be run from the command line
rather than being imported, it works just fine to define `cli = joffrey.CLI(...)` and then call `cli.parse()` to get
your input values. However, in a larger package distributed both as a CLI script *and* an importable Python module, a 'problem'
arises: the module will try to read from the command line even if it's only being imported,
leading to errors when it doesn't find anything it needs in `sys.argv`. This is what `__name__ == '__main__'`
is for, of course, but *then*... what to do with the CLI? Should it be separated, hooking into the main module
and compiling command-line output itself? Or should things go the other way around, with the module hooking into
the CLI and making use of default values to 'fill in the gaps'?

The former is probably the usual way to do things, and any command-line-parsing utility of course lets you
go that way by default. Joffrey helps you go the other way around, too, though. It has three parts to it:

- `cli.result`. A property of `joffrey.CLI()` objects that, up until `cli.prepare()` is called, only returns default values.
- `cli.prepare()`. Prepares this CLI to parse from the command line *rather than* use default values: specifically,
  causes `cli.result` to call `cli.parse()` the next time it's accessed, returning only those values from then on. This
  method should be called from the main command-line entry point, keeping it untouched if the module is imported.
- `cli.set_defaults()`. Changes the CLI's default values, but importantly: if only called from the command-line entry point, allows
  separation of "command-line defaults" from "module defaults", with the defaults set in this function being command-line-level
  and the defaults set via `@cli.command()` and `@cli.flag()` being the module-level. This is useful, for example, in the
  implementation of a `-q`/`--quiet` flag: when imported as a module the `-q` flag should be set by default, but
  when used from the command line it should only become set if the user sets it.

The module as a whole can use `cli.result` to grab important values, and if `cli.prepare()` and `cli.set_defaults()` are used
correctly, this structure will help the module behave seamlessly regardless of whether it was invoked directly from
the command line or whether it was imported.

Here's an example:

```py
# cli.py
from joffrey import CLI

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

_**NOTE: Consider joffrey.simple deprecated or something -- it should probably be demoted to "recipe" status.**_

As an alternative to the full `joffrey.CLI` parser, one may use (as mentioned above) a reduced form of it, dubbed `joffrey.simple`. It works as follows:

```py
import joffrey

@joffrey.simple
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

`joffrey.simple` has no concept of AND/OR/XOR clumps, so it isn't suitable for an application requiring those. It also, rather than being only a *parsing*
tool, submits a little bit to the "click philosophy" of intertwining argument parsing with the actual program execution: rather than assigning each individual
option a function processing only its own value and providing these values to the user without caring what happens afterward (as the standard `joffrey.CLI`
does), it expects the actual functions of a given program to be decorated and passes CLI arguments to them directly. This is a bit iffy, but it does
make for less boilerplate. Overall, though, `joffrey.CLI` should be preferred when possible.

`joffrey.simple` currently can't handle \*\*kwargs by taking arbitrary flags. If that turns out to be a necessity at some point down the line, this will change.

If you'd like to configure all new `joffrey.simple` objects in one go, you can reassign these attributes on the class:

- `joffrey.simple._` (`str`): As in `CLI.flag`, this value controls what the `_` character in a Python identifier's name will be replaced with on the command line.
- `joffrey.simple.flag_prefix` (`str`): Identical to `flag_prefix` in `CLI.__init__()`.
- `joffrey.simple.no_help` (`bool`): Identical to `no_help` in `CLI.__init__()`.
- `joffrey.simple.short_flags` (`bool`): Determines whether to create short aliases out of keyword-parameter names (e.g. `flag` becoming both `--flag` and `-f`).

Note that changing these won't change their values for already-instantiated objects.  
Also note that decorated functions still define `__call__`, so they can be called as normal rather than with `.run()` or `.search()`.


### More typehints
Joffrey itself provides two extra typehint aids: `booly` and `auto`.

`joffrey.booly`:
- The usual `bool` type isn't particularly useful as a converter, because all the strings it's going to be passed are truthy. `booly`, on the other hand,
    evaluates args that are bool ... -y: booleanlike. Returns `True` if passed any of `yes`, `y`, `true`, `t`, `1`, and `False` if passed any of
    `no`, `n`, `false`, `f`, `0`. Argument is `str.lower`ed.

`joffrey.auto`:
- `auto` by itself:
    - Works identically to a normal converter, but calls `ast.literal_eval()` on the string it's passed. If an error results, meaning the string does
    not contain a literal of any sort, returns the string itself.
- `auto(*types)`:
    - Takes a series of `type` objects, and the resultant `auto` instance also applies `ast.literal_eval()` on its argument -- but after that, it
      ensures that the resultant object passes an `isinstance(object, types)` check.  
      Applying the bitwise negation operator, as in `~auto(*types)`, will cause it to instead ensure that the object passes a **`not`**`isinstance(object, types)` check.


Feel free to play around with different `cli.parse()` arguments on the below example:

```py
from joffrey import auto, booly, CLI

cli = CLI()

@cli.flag()
def typehint_stuff(a: booly, b: auto, c: auto(list, tuple), d: ~auto(str)):
    return a, b, c, d
```
