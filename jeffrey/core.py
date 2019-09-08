"""
argparse sucks
this sucks too but less
"""
import os
import sys
import shlex
from functools import partial
from itertools import chain, zip_longest, starmap

from . import errors
from .clumps import And, Or, Xor, ClumpSet
from .entities import Entity, Arg, Flag
from .misc import JeffreyNamespace, _Null


_FILE = os.path.basename(sys.argv[0])


class HelperMixin:
    """
    Provides help-screen functionality to Handlers.
    A bit convoluted; needs reworking.
    """
    
    @property
    def all_commands(self):
        return {*self.commands, *(name for g in self._groups for name in g.commands)}
    
    @property
    def all_flags(self):
        return self.flags.values()
    
    @property
    def all_args(self):
        return map(self.getarg, self.args)
    
    @property
    def usage_info(self):
        return '{}{} {} {}'.format(
          _FILE,
          str(self),
          ' '.join(map(str, self.all_flags)),
          ' '.join(map(str, self.all_args)),
          )
    
    @property
    def help_info(self):
        return '{}\n{}'.format(
          self._label_format('args'),
          self._label_format('flags')
          )
    
    def _label_format(self, label):
        return '{}\n{}'.format(
          label.upper(),
          '\n'.join({
            '\t{: <15} {}'.format(i.name, i.brief)
            for i in getattr(self, 'all_' + label)
            })
          )
    
    def format_help(self, usage=True, commands=True, help=True):
        built = ['', self.desc, ''] if self.desc else ['']
        if usage:
            built.append('usage: {}'.format(self.usage_info))
        if commands and self.commands:
            built.append('commands: {}'.format(', '.join(map(str, self.all_commands))))
        if help:
            if usage or commands:
                built.append('')
            built.append(self.help_info)
        return '\n'.join(built)
    
    def print_help(self, usage=True, commands=True, help=True):
        print(self.format_help(usage, commands, help), end='\n\n')
    
    def error(self, exc=None, help=True):
        self.print_help(help=help)
        if exc is None:
            raise SystemExit
        raise SystemExit(exc if str(exc) else type(exc))
    
    def cli_help(self, name=None):
        """
        name: name of entity to provide help for
        If no name given, provides general help
        """
        if name is None:
            # (this prints the help screen)
            self.error()
        
        entity = self.get(name)
        if entity is None:
            print('No helpable entity named', repr(name))
            raise SystemExit
        
        short = getattr(entity, 'short', '')
        try:
            aliases = ', '.join(map(repr, (k for k, v in self._aliases.items() if v == entity.name and k != short)))
        except AttributeError:
            aliases = ''
        
        name = str(entity).lstrip()
        if aliases:
            print('', name, 'aliases: {}'.format(aliases), entity.help, sep='\n')
        else:
            print('', name, entity.help, sep='\n')
        raise SystemExit


class _Handler:
    """
    Base class for anything that 'handles' flags/args.

    _aliases: Dict of {alias: entity's real name}
    _defaults: Dict of {entity name: default value if not called}
      which is used to fill in unprovided values after parsing
    _last_arg_consumes: Whether the last provided positional argument
      has a repeat count of "...", aka infinite
    _and: AND clumps to take into account when parsing
    _or: OR clumps
    _xor: XOR clumps
    _required: Set of all entities created with required=True
      (for which to raise an error if not provided)
    
    arg_map: Dict of {arg name: jeffrey.entity.Arg object}
    commands: Dict of {command name: jeffrey.core.Command object}
    flags: Dict of {flag name: jeffrey.entity.Flag object}
    args: List of positional arguments provided in the current run
    """

    def __init__(self):
        self.arg_map = {}
        self.commands = {}
        self.flags = {}
        self._aliases = {}
        self._defaults = {}
        
        self.args = []
        self._last_arg_consumes = False
        
        self._and = ClumpSet()
        self._or = ClumpSet()
        self._xor = ClumpSet()
        
        self._required = set()
    
    def __repr__(self):
        quote = "'" if hasattr(self, 'name') else ''
        return '<{}{s}{q}{}{q}>'.format(
          self.__class__.__name__,
          getattr(self, 'name', ''),
          s=' ' if hasattr(self, 'name') else '',
          q=quote,
          )
    
    @property
    def defaults(self):
        # All subcommands would have a default value of their own defaults, hence the dict comp
        return JeffreyNamespace(**self._defaults, **{cmd.name: cmd.defaults for cmd in self.commands.values()})
    
    @property
    def parent_and(self):
        # These are defined differently in subclasses
        return self._and
    
    @property
    def parent_or(self):
        return self._or
    
    @property
    def parent_xor(self):
        return self._xor
    
    @property
    def entity_names(self):
        return {*self.arg_map, *self.commands, *self.flags}
    
    def dealias(self, name):
        return self._aliases.get(name, name)
    
    def remove(self, obj):
        name = obj.identifier if isinstance(obj, Entity.cls) else self.dealias(obj)
        if name in self.arg_map:
            if self._last_arg_consumes:
                # If the entity being removed *is* the one that consumes, then
                # _last_arg_consumes can no longer be True
                self._last_arg_consumes = self.arg_map[name].repcount is not Ellipsis
            self.args = [n for n in self.args if n != name]
            del self.arg_map[name]
        elif name in self.commands:
            del self.commands[name]
        elif name in self.flags:
            del self.flags[name]
        else:
            raise KeyError('No such entity: {}'.format(obj))
        self._aliases = {k: v for k, v in self._aliases.items() if v != name}
    
    def get(self, name):
        """
        Generic getter; use getarg/getflag/getcmd for specific type of entity
        (analogous to hasany())
        """
        for func in (self.getarg, self.getflag, self.getcmd):
            try:
                return func(name)
            except KeyError:
                pass
        return None
    
    def getarg(self, name):
        try:
            return self.arg_map[name]
        except KeyError:
            return self.arg_map[self._aliases[name]]
    
    def getflag(self, name):
        try:
            return self.flags[name]
        except KeyError:
            return self.flags[self._aliases[name]]
    
    def getcmd(self, name):
        try:
            return self.commands[name]
        except KeyError:
            return self.commands[self._aliases[name]]
    
    def hasflag(self, name):
        return self.dealias(name) in self.flags
    
    def hascmd(self, name):
        return self.dealias(name) in self.commands
    
    def hasany(self, name):
        # Analogous to get()
        return self.hasflag(name) or self.hascmd(name) or self.dealias(name) in self.arg_map
    
    def _clump(self, obj, AND, OR, XOR):
        """
        AND/OR/XOR: a clump's unique identifier
        obj: Object to clump with any of the above
        
        Clump object will be grabbed according to
        identifier, and obj will be added into it
        """
        if AND is not _Null:
            self._and.add(And(AND, self))
            And(AND, self).add(obj)
        if OR is not _Null:
            self._or.add(Or(OR, self))
            Or(OR, self).add(obj)
        if XOR is not _Null:
            self._xor.add(Xor(XOR, self))
            Xor(XOR, self).add(obj)
    
    def enforce_clumps(self, parsed, groups=None):
        """
        parsed: Set of entities' names that were extracted from user input
        groups: Clump-groups to take into account when checking
        
        Enforce AND/OR/XOR rules. Mostly the 'heart' of jeffrey.
        """
        
        # Entities to eliminate for each clump
        # (elimination means it was receieved as expected)
        elim = {
          'AND': self.parent_and.successes(parsed),
          'OR': self.parent_or.successes(parsed),
          'XOR': self.parent_xor.successes(parsed)
          }
        
        def extract_names(collection):
            """
            Only used if no groups were given to enforce_clumps()
            (which means there's no nesting to take care of, which
            in turn means a simple repr over everything will do)
            """
            return map(repr, collection)
        
        if groups is not None:
            def extract_names(collection):
                """[Visually group together] group's entity names"""
                return (
                  '[{}]'.format(', '.join(map(repr, groups[n].entity_names)))
                  if n in groups else repr(n) for n in collection
                  )
            _g_clumps = {lbl: {groups.get(s) for s in successes.intersection(groups)} for lbl, successes in elim.items()}
            elim = {lbl: elim[lbl] | {name for g in grps for name in g.entity_names} for lbl, grps in _g_clumps.items()}
        
        err_details = {
          'parsed': parsed,
          'groups': groups,
          'handler': repr(self),
          'AND_SUC': elim['AND'],  # SUC = SUCCESSES
          'OR_SUC': elim['OR'],
          'XOR_SUC': elim['XOR'],
          }
        
        for all_failed, received in self._and.failures(parsed):
            # AND failure == member of an AND clump that was not given
            # an AND failure is okay if it's in a satisfied OR clump (i.e. there's at least one other OR in its clump that was given)
            # or if it's in a satisfied XOR clump (i.e. exactly one other XOR in its clump was given)
            not_exempt = (all_failed - received) - elim['OR'] - elim['XOR']
            if not_exempt:
                raise errors.ANDError(
                  'Expected all of the following flags/arguments/commands: {}\n(Got {})'.format(
                      ', '.join(extract_names(all_failed)),
                      ', '.join(extract_names(received)) or 'none'
                    ),
                  **err_details,
                  failed=all_failed, eliminating=received, not_exempt=not_exempt
                  )
        
        for all_failed, received in self._or.failures(parsed):
            # OR failure == member of an OR clump where none were given
            # an OR failure is okay if it's in a satisfied XOR clump (i.e. exactly one other XOR in its clump was given)
            not_exempt = (all_failed - received) - elim['XOR']
            if not_exempt:
                raise errors.ORError(
                  'Expected at least one of the following flags/arguments/commands: {}\n(Got none)'.format(
                      ', '.join(extract_names(all_failed))
                    ),
                  **err_details,
                  failed=all_failed, eliminating=received, not_exempt=not_exempt
                  )
        
        for all_failed, not_received in self._xor.failures(parsed):
            # XOR failure == member of an XOR clump that was given alongside at least one other
            # an XOR failure is okay if it satisfies an AND clump (i.e. all other ANDs in its clump were given)
            ######################################################################################
            #  XXX: SHOULD it be okay if it satisfies an OR clump? What about if it's required?  #
            #  That is: should this actually say `- elim['AND'] - elim['OR'] - self._required`?  #
            ######################################################################################
            not_exempt = (all_failed - not_received) - elim['AND']
            if len(not_exempt) > 1:
                raise errors.XORError(
                  'Expected no more than one of the following flags/arguments/commands: {}\n(Got {})'.format(
                      ', '.join(extract_names(all_failed)),
                      ', '.join(extract_names(all_failed-not_received))
                    ),
                  **err_details,
                  failed=all_failed, eliminating=not_received, not_exempt=not_exempt
                  )
        return True
    
    def clump(self, *, AND=_Null, OR=_Null, XOR=_Null):
        """
        AND/OR/XOR: Identifiers for each clump
        return: Wrapper function

        Decorator that proxies _clump(), adding an entity
        to the requested clumps
        """
        def inner(cb):
            entity = Entity(cb.func if isinstance(cb, Entity.cls) else cb)
            self._clump(entity, AND, OR, XOR)
            return entity
        return inner
    
    def arg(self, n=1, *, required=False, default=_Null, namespace=None, help=None):
        """
        n: number of times this arg should be received consecutively; ... for infinite
        required: Whether this arg is required to be provided
        default: Default value if this arg is not provided
        namespace: Dict with which to initialize Arg entity's namespace (for storing state between repeated calls)
        help: Help text for this arg (preferably None: defaults to function's __doc__)

        Decorator that registers its decorated function as a positional argument
        """
        def inner(cb):
            repeat_count = n
            entity = Arg(cb, n, namespace=namespace, help=help)
            self.arg_map[entity.name] = entity
            if required:
                self._required.add(entity.name)
            if repeat_count is Ellipsis:
                self._last_arg_consumes = True
                repeat_count = 1
            if default is not _Null:
                self._defaults[entity.name] = default
            self.args.extend([entity.name] * repeat_count)
            return entity
        return inner
    
    def flag(self, dest=None, short=_Null, *, aliases=(), required=False, default=_Null, namespace=None, help=None, _='-'):
        """
        dest: What this flag's name should be in the final resultant JeffreyNamespace
        short: Shorthand alias for this flag; _Null => first available letter, None = no short alias
        aliases: Other aliases for this flag
        required: Whether this flag is required to be provided
        default: Default value if this flag is not provided
        namespace: Dict with which to initialize Flag entity's namespace (for storing state between repeated calls)
        help: Help text for this flag (preferably None: defaults to function's __doc__)

        Decorator that registers its decorated function as a flag/option
        """
        def inner(cb):
            entity = Flag(cb, namespace=namespace, name=dest, help=help, _=_)
            # filter out '<lambda>'
            if cb.__name__.isidentifier():
                self._aliases[cb.__name__] = entity.name
            if short is not None:  # _Null == default; None == none
                try:
                    entity.short = short or next(s for s in entity.name if s.isalnum() and s not in self._aliases)
                except StopIteration:
                    pass
                else:
                    self._aliases[entity.short] = entity.name
            if default is not _Null:
                self._defaults[entity.identifier] = default
            if required:
                self._required.add(entity.name)
            self._aliases.update(dict.fromkeys(aliases, entity.name))
            self.flags[entity.name] = entity
            return entity
        return inner
    
    def command(self, name, desc='', *args, AND=_Null, OR=_Null, XOR=_Null, from_cli=None, aliases=(), _='-', **kwargs):
        """
        name: This command's name
        desc: This command's helptext (a short description of it)
        AND/OR/XOR: Clump values for this command as a whole
        from_cli: If not None, jeffrey.core.CLI object to create this command from
        aliases: Aliases for this command
        _: What to replace underscores in this command's name with ((XXX: is that even applicable? commands aren't attrs))
        *args, **kwargs: See Command.__init__()

        Creates and returns a Command object that acts as a sub-command/sub-parser
        """
        if from_cli is None:
            subcmd = Command(*args, **kwargs, name=name, desc=desc, parent=self)
        else:
            subcmd = Command.from_cli(from_cli, self, name)
        visual_name = name.replace('_', _)
        self._aliases.update(dict.fromkeys(aliases, visual_name))
        self._aliases[name] = visual_name
        self.commands[visual_name] = subcmd
        self._clump(subcmd, AND, OR, XOR)
        return subcmd


class ParserBase(_Handler, HelperMixin):
    """
    Base class for Handlers that can parse arguments.

    _groups: Clump-groups present in this parser
    _prepared_parse: A functools.partial that is set once prepare() is called
    _result: The result of _prepared_parse(), once called
    
    desc: Helptext (a short description of this parser)
    flag_prefix: What to prefix shorthand flags with
    long_prefix: flag_prefix*2, used to prefix long-form flags
    systemexit: Whether to raise SystemExit on error or just fail w/ the original exception
    """
    
    def __init__(self, desc='', flag_prefix='-', *, systemexit=True, no_help=False):
        """
        desc: Helptext (a short description of this parser)
        flag_prefix: What to prefix shorthand flags with (long prefix is this*2)
        systemexit: Whether to raise SystemExit on error or just fail w/ the original exception
        no_help: Whether NOT to create a default help command
        """
        super().__init__()
        self.desc = desc
        self.flag_prefix = flag_prefix
        self.long_prefix = 2 * flag_prefix
        self.systemexit = systemexit
        self._groups = set()
        self._prepared_parse = None
        self._result = None
        if not flag_prefix:
            raise ValueError('Flag prefix cannot be empty')
        if not no_help:
            self.flag('help',
              help="Prints help and exits\nIf given a valid NAME, displays that entity's help"
            )(lambda name=None: self.cli_help(name))
    
    def __setattr__(self, name, val):
        """
        Special-cased for jeffrey.core.Group objects: re-initializes the
        group as a SubHandler and adds it to self._groups
        """
        if not isinstance(val, Group):
            return object.__setattr__(self, name, val)
        
        if name in vars(self):
            raise ValueError('Group name already in use for this cli: ' + name)
        if val._required:
            self._required.add(name)
        
        self._groups.add(val)
        self._clump(val, val._and, val._or, val._xor)
        
        SubHandler.__init__(val, self, name)
        object.__setattr__(self, name, val)
    
    @property
    def defaults(self):
        return super().defaults
    
    @property
    def result(self):
        """
        Returns the result of self._prepared_parse()
        once that is set to not-None.
        In the grand scheme of things, allows projects to be based
        entirely around the CLI (by getting default-or-passed values
        from cli.result).
        """
        if self._prepared_parse is None:
            return self.defaults
        if self._result is None:
            self._result = self._prepared_parse()
        return self._result
    
    def dealias(self, name):
        try:
            return next(g.dealias(name) for g in self._groups if g.hasany(name))
        except StopIteration:
            return super().dealias(name)
    
    def remove(self, obj):
        name = obj.name if isinstance(obj, Entity.cls) else obj
        for g in self._groups:
            try:
                return g.remove(name)
            except KeyError:
                pass
        return super().remove(name)
    
    def get(self, name):
        try:
            return next(g.get(name) for g in self._groups if g.hasany(name))
        except StopIteration:
            return super().get(name)
    
    def getarg(self, name):
        try:
            return next(g.getarg(name) for g in self._groups if name in g.arg_map)
        except StopIteration:
            return super().getarg(name)
    
    def getflag(self, name):
        try:
            return next(g.getflag(name) for g in self._groups if g.hasflag(name))
        except StopIteration:
            return super().getflag(name)
    
    def getcmd(self, name):
        try:
            return next(g.getcmd(name) for g in self._groups if g.hascmd(name))
        except StopIteration:
            return super().getcmd(name)
    
    def hasflag(self, name):
        return super().hasflag(name) or any(g.hasflag(name) for g in self._groups)
    
    def hascmd(self, name):
        return super().hascmd(name) or any(g.hascmd(name) for g in self._groups)
    
    def hasany(self, name):
        # XXX: What reason does this have for not checking `g.hasany() for g in self._groups`?
        # (is it intentional? I don't remember... my bad for not commenting as soon as I wrote it.)
        return super().hasany(name) or self._aliases.get(name, _Null) in self.arg_map
    
    def enforce_clumps(self, parsed):
        # p is a set of `parsed` PLUS names of all groups that have entities in `parsed`
        # because the group names are what this parser's and/or/xor clumps will be looking for
        p = set(parsed).union(next((g.name for g in self._groups if g.hasany(i)), None) for i in parsed) - {None}
        return (
          super().enforce_clumps(p, {g.name: g for g in self._groups})
          and
          all(g.enforce_clumps(parsed) for g in self._groups if g.name in p)
          )
    
    def _put_nsp(self, namespaces, entity):
        """
        namespaces: dict of namespaces used in current parse session
        entity: entity to pass a namespace to
        return: Callable that provides entity with the appropriate namespace

        Since namespaces are local to each parse-session, they can
        be stored in a single dict (viz. namespaces) of {entity: nsp}.
        """
        return entity if entity.namespace is None else partial(
          entity,
          namespaces.setdefault(
            entity.name,
            JeffreyNamespace(**entity.namespace)
            )
          )
    
    def _check_skip(self, value):
        """
        Check if this value ends a run of flag arguments
        (i.e. if it's another flag or the end-of-flags sentinel)
        """
        return value.startswith(self.flag_prefix) or value == '--'
    
    def _extract_flargs(self, inp, strict=False, propagate_unknowns=False):
        """
        inp: Input to parse
        strict: Whether to disallow unknown flags / excessive positional args
        propagate_unknowns: Whether unknown flags should be regarded as
          an error or just bubbled up to parent handler
        return: flags+args found, subcommand (if any), and unknown flags to propagate
        
        Extract flags/args from user input and return both.
        """
        # args/flags found so far
        flags = []
        args = []
        # number of elements to skip (used when flag has multiple args)
        skip = 0
        # subcommand, if any
        command = None
        # start off assuming there can be flags in the input
        # (changes if we hit a '--')
        allow_flags = True
        
        # errors
        too_many_args = False
        unknown_flags = []
        
        for idx, value in enumerate(inp, 1):
            if skip > 0:
                skip -= 1
                continue
            
            # "No flags beyond this point" sentinel
            if value == '--':
                allow_flags = False
                continue
            
            if (not allow_flags) or (not value.startswith(self.flag_prefix) or value in (self.flag_prefix, self.long_prefix)):
                # Then value is a command or positional argument
                if self.hascmd(value):
                    command = (value, idx)
                    # Commands consume everything to their right, so no point parsing further
                    break
                args.append(value)
                # self._last_arg_consumes == infinite args allowed
                if not self._last_arg_consumes and len(args) > len(self.args):
                    too_many_args = True
            elif allow_flags:
                if '=' in value:
                    # Then it's passing a single arg to the flag
                    name, arg = value.lstrip(self.flag_prefix).split('=', 1)
                    if self.hasflag(name):
                        flags.append((self.dealias(name), [arg] if arg else []))
                    elif propagate_unknowns:
                        unknown_flags.append(('', value.split('=')[0], [arg] if arg else []))
                    else:
                        unknown_flags.append(('', value.split('=')[0]))
                    continue
                
                if value.startswith(self.long_prefix):
                    name = value.lstrip(self.flag_prefix)
                    if self.hasflag(name):  # long-form flag name
                        skip = self.getflag(name).argcount
                        next_pos = next((i for i, v in enumerate(inp[idx:]) if self._check_skip(v)), len(inp))
                        if next_pos < skip:
                            skip = next_pos
                        flags.append((self.dealias(name), inp[idx:skip+idx]))
                    elif propagate_unknowns:
                        # Below is commented out because there's no way of knowing how many args the flag accepts
                        # if it's not this parser's own
                        #skip = next((i for i, v in enumerate(inp[idx:]) if self._check_skip(v)), len(inp))
                        #unknown_flags.append(('', value, inp[idx:skip+idx]))
                        unknown_flags.append(('', value, []))
                    else:
                        unknown_flags.append(('', value))
                    continue
                
                for name in value[1:]:  # collection of shorthand flag names (like '-xcvf')
                    if self.hasflag(name):
                        skip = self.getflag(name).argcount
                        next_pos = next((i for i, v in enumerate(inp[idx:]) if self._check_skip(v)), len(inp))
                        if next_pos < skip:
                            skip = next_pos
                        flags.append((self.dealias(name), inp[idx:skip+idx]))
                    elif propagate_unknowns:
                        unknown_flags.append((value[0], name, []))
                    else:
                        unknown_flags.append((value[0], name))
        
        if strict:
            if too_many_args:
                if self.commands and not self.args:
                    raise TypeError(
                      'Expected a command: {}\n'
                      'Try `--help <command name>` for specific detail'
                      .format(', '.join(map(repr, self.commands)))
                      )
                raise TypeError('Too many positional arguments (expected {}, got {})'.format(
                  len(self.args), len(args)
                  ))
            if unknown_flags and not propagate_unknowns:
                raise TypeError('Unknown flag(s): ' + ' '.join(starmap("`{}{}'".format, unknown_flags)))
        return flags, args, command, unknown_flags if propagate_unknowns else []
    
    def do_parse(self, inp=None, strict=False, systemexit=True, propagate_unknowns=False):
        """
        inp: List of command-line args to parse
        strict: Whether to disallow excessive args and/or unknown non-propagable flags
        systemexit: Whether to raise SystemExit on error or just fail with the original exception
        propagate_unknowns: Whether to bubble up unknown flags to parent handler
        return: Parsed-out JeffreyNamespace from inp, unknown flags found
        
        Backend to parse() -- does the actual parsing and returns result + unknown flags to propagate
        """
        parsed = {}
        flags, positionals, command, unknown_flags = self._extract_flargs(inp, strict, propagate_unknowns)
        # Namespaces to be passed to entities in current run
        # (nsps are parse-session-local)
        namespaces = {}
        prep = partial(self._put_nsp, namespaces)
        
        for flag, args in flags:
            if self.hasflag(flag):
                entity = self.getflag(flag)
                parsed[entity.identifier] = prep(entity)(*args)
        
        if self._last_arg_consumes and len(positionals) > len(self.args):
            # Fill zipped_args with the Arg that's meant to consume trailing values
            zipped_args = zip_longest(map(self.getarg, self.args), positionals, fillvalue=self.getarg(self.args[-1]))
        else:
            zipped_args = zip(map(self.getarg, self.args), positionals)
        
        for entity, value in zipped_args:
            parsed[entity.identifier] = prep(entity)(value)
        
        if command is not None:
            value, idx = command
            command, cmd_obj = self._aliases.get(value, value), self.getcmd(value)
            try:
                parsed[command], cmd_unknown_flags = cmd_obj.do_parse(inp[idx:], strict, systemexit, propagate_unknowns)
            except Exception as e:
                if systemexit is None and cmd_obj.systemexit or systemexit:
                    cmd_obj.error(e, help=False)
                raise
            else:
                if propagate_unknowns:
                    # The _ is the flag's name, which would only have been used for error output
                    for _, flag, args in cmd_unknown_flags:
                        name = flag.lstrip(self.flag_prefix)
                        if self.hasflag(name):
                            entity = self.getflag(name)
                            parsed[entity.identifier] = prep(entity)(*args)
                        else:
                            # Propagate yet further
                            unknown_flags.append((None, name, args))
        self.enforce_clumps(parsed)
        # Place defaults first then override them with provided values
        final = {**self._defaults, **{name: value for g in self._groups for name, value in g._defaults.items()}, **parsed}
        
        nsp = JeffreyNamespace(**final)
        # One final check after enforce_clumps: all required entities must have been provided
        if self._required.difference(nsp):
            raise errors.RequirementError('Expected the following required arguments: {}\nGot {}'.format(
              ', '.join(map(repr, self._required)),
              ', '.join(map(repr, self._required.intersection(nsp))) or 'none'
              ))
        return nsp, unknown_flags
    
    def parse(self, inp=None, *, systemexit=None, strict=False, propagate_unknowns=False):
        """
        inp: Input to parse, either as a string (which is then shlex.split) or a list of string arguments
        systemexit: Whether to raise SystemExit on error or just fail with the original exception
        strict: Whether to disallow excessive args and/or unknown non-propagable flags
        propagate_unknowns: Whether to bubble up unknown flags to parent handler
        return: Resultant JeffreyNamespace from parse

        Parses user input into an JeffreyNamespace. If systemexit, prints usage info on error.
        """
        if inp is None:
            inp = sys.argv[1:]
        if isinstance(inp, str):
            inp = shlex.split(inp)
        
        try:
            nsp, _ = self.do_parse(list(inp), strict, systemexit, propagate_unknowns)  # list(inp) is effectively inp.copy()
        except Exception as e:
            if systemexit is None and self.systemexit or systemexit:
                self.error(e, help=False)
            raise
        except SystemExit:
            if systemexit is None and self.systemexit or systemexit:
                raise
        else:
            return nsp
    
    def prepare(self, *args, **kwargs):
        """
        *args, **kwargs: see parse().
        return: self
        
        Makes self.result return an JeffreyNamespace of actual
        parsed values (not just defaults).
        Returns self to allow a `prepare()` call to be chained
        into `set_defaults()` and/or `result`.
        """
        self._prepared_parse = partial(self.parse, *args, **kwargs)
        return self
    
    def set_defaults(self, **kwargs):
        """
        **kwargs: names and values to insert into self._defaults

        Ensures that each name in kwargs is already present.
        Returns self to allow a `set_defaults()` call to be chained
        into `result` or `prepare()`.
        """
        for name in kwargs:
            if not self.hasany(name):
                raise KeyError('Unknown name {} passed to set_defaults()'.format(name))
        self._defaults.update(kwargs)
        return self


class SubHandler(_Handler):
    """
    Base class for handlers that cannot parse, but are 'attached' to handlers that can.
    """
    def __init__(self, parent, name):
        if not name:
            raise ValueError('Sub-handler name cannot be empty')
        self.name = name
        self.parent = parent
        super().__init__()
    
    @property
    def parent_and(self):
        return ClumpSet(self._aliases.get(i, i) for i in chain(self._and, self.parent.parent_and))
    
    @property
    def parent_or(self):
        return ClumpSet(self._aliases.get(i, i) for i in chain(self._or, self.parent.parent_or))
    
    @property
    def parent_xor(self):
        return ClumpSet(self._aliases.get(i, i) for i in chain(self._xor, self.parent.parent_xor))


class Group(SubHandler):
    """
    Clump-group that hosts clumps within itself but can be itself passed to clumps whole.
    Strange implementation to streamline group creation a little bit: __init__() only
    sets up the shell of a Group, and nothing happens with the obj until it is assigned as
    an attribute of a ParserBase object (which will then assign the group's name and set it
    up to be an actual SubHandler and everything).
    """
    def __init__(self, *, required=False, AND=_Null, OR=_Null, XOR=_Null):
        """
        CLI later calls `SubHandler.__init__(Group(), self, name)` in its __setattr__()
        (All instance attributes are overridden by this)
        """
        self._required = required
        self._and = AND
        self._or = OR
        self._xor = XOR
    
    def arg(self, n=1, **kwargs):
        """
        See _Handler.arg()
        
        n: number of times this arg should be received consecutively; pass ... for infinite
        Expected kwargs: _ (str), help (str)
        """
        def inner(cb):
            entity = Arg(cb, n, namespace=kwargs.get('namespace'), help=kwargs.get('help'))
            self.arg_map[entity.name] = entity
            if kwargs.get('required'):
                self._required.add(entity.name)
            return self.parent.arg(n, **kwargs)(entity.func)
        return inner
    
    def flag(self, dest=None, short=_Null, **kwargs):
        """
        See _Handler.flag().
        """
        def inner(cb):
            entity = Flag(cb, namespace=kwargs.get('namespace'), name=dest, help=kwargs.get('help'), _=kwargs.get('_', '-'))
            if cb.__name__.isidentifier():
                self._aliases[cb.__name__] = entity.name
            if short is not None:  # _Null == default; None == none
                try:
                    entity.short = short or next(s for s in entity.name if s.isalnum() and s not in self._aliases)
                except StopIteration:
                    pass
                else:
                    self._aliases[entity.short] = entity.name
            if kwargs.get('default', _Null) is not _Null:  # could be `'default' not in kwargs` but we don't want them using _Null either
                self._defaults[entity.identifier] = kwargs['default']
            if kwargs.get('required'):
                self._required.add(entity.name)
            self.flags[entity.name] = entity
            return self.parent.flag(dest, short, **kwargs)(entity.func)
        return inner


class Command(SubHandler, ParserBase):
    """
    Subcommand: attached to a parser but is also one in its own right.
    """
    def __init__(self, flag_prefix='-', *, parent, name, desc):
        SubHandler.__init__(self, parent, name)
        ParserBase.__init__(self, desc, flag_prefix, systemexit=getattr(parent, 'systemexit', True))
    
    def __str__(self):
        return ' {}'.format(self.name)
    
    @classmethod
    def from_cli(cls, cli, parent, name):
        """
        cli: jeffrey.core.CLI object to create command from
        parent: ParserBase object to attach new command to
        name: name of new command

        Creates a command from a preexisting ParserBase object. Helps with extensibility.
        """
        obj = cls(cli.flag_prefix, parent=parent, name=name, desc=cli.desc)
        obj.__dict__.update(vars(cli))
        return obj
    
    @property
    def help(self):
        return self.format_help()


class CLI(ParserBase):
    """
    The 'main dish', as phrased in the README.
    This is what users import and base their jeffrey applications off of.
    """
    def __str__(self):  # for help screen (because main CLI shouldn't show its own name)
        return ''
    
    def _extract_flargs(self, *args, **kwargs):
        # Top-level CLI has nothing to bubble its unknowns up to
        kwargs['propagate_unknowns'] = False
        # Propagate_unknowns is the last pos arg for now, so we can do [:-1] to get rid of it
        return super()._extract_flargs(*args[:-1], **kwargs)
