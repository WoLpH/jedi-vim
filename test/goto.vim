let mapleader = '\'
source plugin/jedi.vim
source test/utils.vim

describe 'goto_simple'
    before
        new  " open a new split
        set filetype=python
        put =[
        \   'def a(): pass',
        \   'b = a',
        \   'c = b',
        \ ]
        normal! ggdd
        normal! G$
        Expect line('.') == 3
    end

    after
        bd!
    end

    it 'goto_definitions'
        silent normal \d
        Expect line('.') == 1
        "Expect col('.') == 5  " not working yet.
    end

    it 'goto_assignments'
        silent normal \g
        Expect line('.') == 2
        Expect col('.') == 1

        " cursor before `=` means that it stays there.
        silent normal \g
        Expect line('.') == 2
        Expect col('.') == 1

        " going to the last line changes it.
        normal! $
        silent normal \g
        Expect line('.') == 1
        Expect col('.') == 5
    end
end


describe 'goto_with_tabs'
    before
        set filetype=python
    end

    after
        bd!
        bd!
    end

    it 'follow_import'
        put = ['import subprocess', 'subprocess']
        silent normal G\g
        Expect getline('.') == 'import subprocess'
        Expect line('.') == 2
        Expect col('.') == 8

        silent normal G\d
        Expect g:current_buffer_is_module('subprocess') == 1
        Expect line('.') == 1
        Expect col('.') == 1
        Expect tabpagenr('$') == 2
        tabprevious
        Expect bufname('%') == ''
    end

    it 'multi_definitions'
        put = ['import tokenize']
        silent normal G$\d
        Expect g:current_buffer_is_module('tokenize') == 0
        Expect g:current_buffer_is_module('token') == 0
        execute "normal \<CR>"
        Expect tabpagenr('$') == 2
        Expect g:current_buffer_is_module('token') == 1

        bd
        silent normal G$\d
        execute "normal j\<CR>"
        Expect tabpagenr('$') == 2
        Expect g:current_buffer_is_module('tokenize') == 1
    end
end


describe 'goto_with_buffers'
    before
        set filetype=python
        let g:jedi#use_tabs_not_buffers = 0
    end

    after
        bd!
        bd!
        set nohidden
    end

    it 'no_new_tabs'
        put = ['import os']
        normal G$
        call jedi#goto_assignments()
        python jedi_vim.goto()
        Expect g:current_buffer_is_module('os') == 0
        " Without hidden, it's not possible to open a new buffer, when the old
        " one is not saved.
        set hidden
        call jedi#goto_assignments()
        Expect g:current_buffer_is_module('os') == 1
        Expect tabpagenr('$') == 1
        Expect line('.') == 1
        Expect col('.') == 1
    end

    it 'multi_definitions'
        set hidden
        put = ['import tokenize']
        silent normal G$\d
        Expect g:current_buffer_is_module('tokenize') == 0
        Expect g:current_buffer_is_module('token') == 0
        execute "normal \<CR>"
        Expect tabpagenr('$') == 1
        Expect g:current_buffer_is_module('token') == 1

        bd
        silent normal G$\d
        execute "normal j\<CR>"
        Expect tabpagenr('$') == 1
        Expect g:current_buffer_is_module('tokenize') == 1
    end
end

" vim: et:ts=4:sw=4
