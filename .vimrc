set nocompatible        " vi? we don't need no stinking vi!
set nobackup            " don't keep a backup file
set nowritebackup       " seriously, no backup file
set laststatus=2        " always show status line
set shortmess=atI       " always show short messages
set showcmd             " display incomplete commands
set encoding=utf-8      " you don't use utf-8? ಠ_ಠ
let &termencoding = &encoding
set ignorecase          " ignore case when searching
set smartcase           " don't ignore case if pattern contains uppercase
set incsearch           " do incremental searching
set hlsearch            " highlight matches
set ttyfast
set term=builtin_xterm  " treat terminal as a plain xterm
" disable Background Color Erase (BCE)
" helps with tmux/screen redraw issues
set t_ut=
" disable alt buffer (raw) mode in terminal
" this keeps the screen form clearing on exit
set t_ti=
set t_te=
set visualbell          " don't beep, flash
set t_vb=
set noerrorbells        " don't beep damn it
set backspace=indent,eol,start  " backspace over everything in insert mode
set scrolloff=7         " keep 7 lines of context before/after cursor
set sidescrolloff=7     " keep 7 columns when scrolling side to side
set sidescroll=1        " don't snap cursor to mid screen
set whichwrap=<,>,h,l   " let cursors movement wrap to next/previous line
set nostartofline       " don't jump from column to column when changing lines
set hidden              " Allow hiding dirty buffers
set report=0            " tell me when anything changes
set pastetoggle=<C-P>   " easy paste switch
set noicon              " don't modify icon text of the window
set notitle             " don't modify title of the window
set lazyredraw          " don't redraw during macros
syntax enable           " enable syntax highlighting
color desert            " set color scheme
set background=dark     " on a dark background
