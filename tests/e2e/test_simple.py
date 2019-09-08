from textwrap import dedent

import jeffrey
import pytest


@jeffrey.simple
def main(a: int, *b: list, c: set = None):
    return a, b, c


@main.command
def FFF(one: str.upper, *, two: lambda x: tuple(map(int, x))):
    print(one, two)
    return one, two


jeffrey.simple._ = '.'
jeffrey.simple.short_flags = False


@jeffrey.simple
def main2(*, asd_f):
    return asd_f


jeffrey.simple._ = '-'
jeffrey.simple.short_flags = True


@jeffrey.simple
def segundo(positional, *consuming, flag):
    """Simple-CLI demo"""
    print('MAIN:', positional, consuming, flag)


@segundo.command
def cmd(conv: list = None, *, flag: str.upper):
    """Subcommand of main"""
    print('CMD:', conv, flag)


@cmd.command
def subcmd(*consuming: set, flag: str.lower):
    """Subcommand of the subcommand"""
    global SETS_HAVE_NO_ORDER_SO_THIS_GLOBAL_LETS_US_TEST_FOR_THEIR_STR
    SETS_HAVE_NO_ORDER_SO_THIS_GLOBAL_LETS_US_TEST_FOR_THEIR_STR = consuming
    print('SUBCMD:', consuming, flag)


jeffrey.simple.no_top_level()  # just so that part runs /shrug


def test_simple():
    assert main.run('1 2 3 4 --c 5') == (1, (['2'], ['3'], ['4']), {'5'})


def test_simple_cmd(capsys):
    assert FFF.run('one -t 234') == ('ONE', (2, 3, 4))
    capsys.readouterr()  # discard that ^
    assert main.run('1 FFF blah -t 2') == (1, (), None)
    assert capsys.readouterr().out == 'BLAH (2,)\n'


def test_delayed_simple_config():
    assert main2.run('--asd.f 3') == '3'
    with pytest.raises(TypeError):
        main2.run('-a 3')


def test_nested_commands__this_is_also_the_example_in_the_readme(capsys):
    segundo.run('one two three four --flag five')
    assert capsys.readouterr().out == "MAIN: one ('two', 'three', 'four') five\n"
    segundo.run('hhh -f value cmd test --f screamed')
    assert capsys.readouterr().out == dedent('''\
      MAIN: hhh () value
      CMD: ['t', 'e', 's', 't'] SCREAMED
      ''')
    cmd.run('-f uppercase')
    assert capsys.readouterr().out == 'CMD: None UPPERCASE\n'
    segundo.run('none -f none cmd -f none subcmd sets sets -f WHISPER')
    assert capsys.readouterr().out == dedent('''\
      MAIN: none () none
      CMD: None NONE
      SUBCMD: {} whisper
      '''.format(SETS_HAVE_NO_ORDER_SO_THIS_GLOBAL_LETS_US_TEST_FOR_THEIR_STR))
    subcmd.search('none -f subcmd cmd -f none subcmd sets sets -f WHISPER')
    assert capsys.readouterr().out == 'SUBCMD: {} whisper\n'.format(
      SETS_HAVE_NO_ORDER_SO_THIS_GLOBAL_LETS_US_TEST_FOR_THEIR_STR
      )


def test_nothing_important_but_satisfy_testcov():
    with pytest.raises(IndexError):
        subcmd.search('nope')
    
    import sys
    old_argv = sys.argv
    sys.argv = ['']
    with pytest.raises(IndexError):
        subcmd.search(None)
    sys.argv = old_argv
    assert main2(asd_f=1) == 1
