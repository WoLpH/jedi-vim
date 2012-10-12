"""
The Python parts of the Jedi library for VIM. It is mostly about communicating
with VIM.
"""

import vim
import jedi
import jedi.keywords
import traceback  # for exception output
import re

temp_rename = None  # used for jedi#rename

class PythonToVimStr(str):
    """ Vim has a different string implementation of single quotes """
    __slots__ = []
    def __repr__(self):
        return '"%s"' % self.replace('\\', '\\\\').replace('"', r'\"')


def echo_highlight(msg):
    vim.command('echohl WarningMsg | echo "%s" | echohl None' % msg)


def get_script(source=None, column=None):
    jedi.settings.additional_dynamic_modules = \
        [b.name for b in vim.buffers if b.name.endswith('.py')]
    if source is None:
        source = '\n'.join(vim.current.buffer)
    row = vim.current.window.cursor[0]
    if column is None:
        column = vim.current.window.cursor[1]
    buf_path = vim.current.buffer.name
    return jedi.Script(source, row, column, buf_path)


def _goto(is_definition=False, is_related_name=False, no_output=False):
    definitions = []
    script = get_script()
    try:
        if is_related_name:
            definitions = script.related_names()
        elif is_definition:
            definitions = script.get_definition()
        else:
            definitions = script.goto()
    except jedi.NotFoundError:
        echo_highlight("Cannot follow nothing. Put your cursor on a valid name.")
    except Exception:
        # print to stdout, will be in :messages
        echo_highlight("Some different eror, this shouldn't happen.")
        print(traceback.format_exc())
    else:
        if no_output:
            return definitions
        if not definitions:
            echo_highlight("Couldn't find any definitions for this.")
        elif len(definitions) == 1 and not is_related_name:
            # just add some mark to add the current position to the jumplist.
            # this is ugly, because it overrides the mark for '`', so if anyone
            # has a better idea, let me know.
            vim.command('normal! m`')

            d = list(definitions)[0]
            if d.in_builtin_module():
                if isinstance(d.definition, jedi.keywords.Keyword):
                    echo_highlight("Cannot get the definition of Python keywords.")
                else:
                    echo_highlight("Builtin modules cannot be displayed.")
            else:
                if d.module_path != vim.current.buffer.name:
                    if vim.eval('g:jedi#use_tabs_not_buffers') == '1':
                        vim.command('call jedi#tabnew("%s")' % d.module_path)
                    else:
                        vim.command('edit ' + d.module_path)
                vim.current.window.cursor = d.line_nr, d.column
                vim.command('normal! zt')  # cursor at top of screen
        else:
            # multiple solutions
            lst = []
            for d in definitions:
                if d.in_builtin_module():
                    lst.append(dict(text='Builtin ' + d.description))
                else:
                    lst.append(dict(filename=d.module_path, lnum=d.line_nr, col=d.column+1, text=d.description))
            vim.command('call setqflist(%s)' % str(lst))
            vim.command('call <sid>add_goto_window()')
    return definitions


def show_func_def(call_def, completion_lines=0):
    vim.eval('jedi#clear_func_def()')

    if call_def is None:
        return

    row, column = call_def.bracket_start
    if column < 2 or row == 0:
        return  # edge cases, just ignore

    # TODO check if completion menu is above or below
    row_to_replace = row - 1
    line = vim.eval("getline(%s)" % row_to_replace)

    insert_column = column - 2 # because it has stuff at the beginning

    params = [p.get_code().replace('\n', '') for p in call_def.params]
    try:
        params[call_def.index] = '*%s*' % params[call_def.index]
    except (IndexError, TypeError):
        pass

    # This stuff is reaaaaally a hack! I cannot stress enough, that this is a
    # stupid solution. But there is really no other yet. There is no
    # possibility in VIM to draw on the screen, but there will be one
    # (see :help todo Patch to access screen under Python. (Marko Mahni, 2010 Jul 18))
    text = " (%s) " % ', '.join(params)
    text = ' ' * (insert_column - len(line)) + text
    end_column = insert_column + len(text) - 2  # -2 because of bold symbols
    # replace line before with cursor
    e = vim.eval('g:jedi#function_definition_escape')
    regex = "xjedi=%sx%sxjedix".replace('x', e)

    prefix, replace = line[:insert_column], line[insert_column:end_column]
    # check the replace stuff for strings, to append them (don't want to break the syntax)
    regex_quotes = '\\\\*["\']+'
    add = ''.join(re.findall(regex_quotes, replace))  # add are all the strings
    if add:
        a = re.search(regex_quotes + '$', prefix)
        add = ('' if a is None else a.group(0)) + add

    tup = '%s, %s' % (len(add), replace)
    repl = ("%s" + regex + "%s") % (prefix, tup, text, add + line[end_column:])

    vim.eval('setline(%s, %s)' % (row_to_replace, repr(PythonToVimStr(repl))))