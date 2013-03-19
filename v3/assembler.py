import re

#Keep track of source line for every word
#Generate result words for every source line afterwards

#lex and parse file
#do all includes
#get all definitions
#get all lengths and positions
#give all tokens their position
#get all data

#instruction, preprocessor, data, labeldef

class Lexer:
    '''Do not use (), only (?:)'''
    def __init__(self, rules):
        self.rules = rules
        self.names = [''] + [x[-1] for x in rules]
        self.regex = re.compile('|'.join('(' + x[0] + ')' for x in rules))
        assert not self.regex.match(''), \
               'One of the provided rules matches the empty string.'

    def lex(self, line):
        self.line = line
        self.pos = 0
        self.end = len(line)

    def next(self, ignorews=False):
        tmp = next(self, None)
        while ignorews and tmp and tmp[1] == 'whitespace':
            tmp = next(self, None)
        return tmp

    def __next__(self):
        if self.pos >= self.end:
            raise StopIteration
        match = self.regex.match(self.line, self.pos)
        if match == None:
            tmp = self.line[self.pos:]
            self.pos = self.end
            return (tmp, '')
        self.pos = match.end()
        return (match.group(), self.names[match.lastindex])

class Assembler:
    def __init__(self, mainfile):
        assert isinstance(mainfile, str)

        self.mainfile = mainfile
        self.files = {}
        self.errors = []
        self.warnings = []

    def getfile(self, filepath):
        if filepath not in self.files:
            tmp = TextFile(filepath).read()
            if tmp.success:
                self.files[filepath] = tmp
            else:
                return None
        return self.files[filepath]

    def adderr(*args):
        self.warnings.append(Error(*args))

    def addwarn(*args):
        self.errors.append(Warn(*args))



class TextFile:
    def __init__(self, filepath=None, lines=None):
        assert isinstance(filepath, (None, str))
        assert isinstance(lines, (None, list))

        self.lines = lines
        self.filepath = filepath
        self.success = False
        self.path, self.name, self.ext = splitpath(filepath)
        self.filename = self.name + self.ext

    def read(self):
        try:
            with open(self.filepath, 'r') as f:
                self.lines = f.readlines()
        except IOError:
            self.success = False
            self.lines = None
            return self
        self.success = True
        return self

    def write(self, end='\n'):
        assert isinstance(end, str)
        try:
            with open(self.filepath, 'w') as f:
                for line in self.lines:
                    f.write(line + end)
        except IOError:
            self.success = False
            return self
        self.success = True
        return self



ppcommands = [
    'reserve',
    'define',
    'include',
    'macro',
    'endmacro',
    'align',
    'longform',
    'shortform',
    'relocate',
    'endrelocate',
    ]
rules = [
    (r'\s+', 'whitespace'),
    (r'(?:[lp]?"(?:[^"\\]|(?:\\.))*"[0nzc]?)|' +
     r"(?:[lp]?'(?:[^'\\]|(?:\\.))*'[0nzc]?)", 'string'),
    (r'(?::[a-z_.][a-z0-9_.]*)|(?:[a-z_.][a-z0-9_.]*:)', 'label'),
    (r'[#.](?:' + '|'.join(ppcommands) + ')', 'preprocessor'),
    (r'[#.]?dat', 'data'),
    (r'set|add|sub|mul|div|mod|mli|dvi|mdi|and|bor|xor|shl|shr|asr|' +
     r'ife|ifn|ifb|ifc|ifg|ifl|ifa|ifu|adx|sbx|sti|std', 'basic'),
    (r'jsr|hwn|hwq|hwi|ias|iag|iaq|int|rfi', 'advanced'),
    (r'a|b|c|x|y|z|i|j', 'register'),
    ('pc'),
    ('sp'),
    ('ex'),
    ('push'),
    ('pop'),
    ('peek'),
    ('pick'),
    (r'[a-z_.][a-z0-9_.]*', 'identifier'),
    (r'(?:0x[0-9a-f]+)|(?:[0-9]+)', 'number'),
    (r'\=\=|\<\=|\>\=|\<\<|\>\>|\!\=|\&\&|\|\||' +
     r'\||\!|\~|\^|\&|\%|\*|\/|\-|\+', 'operator'),
    ] + [('\\' + c, c) for c in ',$()[]{}']

def splitpath(filepath):
    sl = max(filepath.find('/'), filepath.find('\\'))
    if sl == -1:
        path = ''
    else:
        path = filepath[:sl + 1]
        filepath = filepath[sl + 1:]
    dl = filepath.rfind('.')
    if dl == -1:
        ext = ''
    else:
        ext = filepath[dl:]
        filepath = filepath[:dl]
    path.replace('\\', '/')
    return path, filepath, ext

def stripcomments(self, s):
    scl = re.sub(self.stringre,
                 lambda x: len(x.group(0)) * '-', s).find(';')
    return s.strip() if scl == -1 else s[:scl].strip()

#TO BE ORDERED

def getnext():
    nxt = next(lexer)
    if isinstance(nxt, str):
        raise LexError, nxt
    return nxt

while True:
    nxt = getnext()
    if nxt[1] in ['opcode', 'preprocessor', 'labeldef', 'data']:
        self.tokens.append(Token.new(nxt))
    else:
        self.tokens[-1].addarg(self.getarg(nxt))
    if getnext() != 'whitespace':
        raise ParseError, 'Whitespace expected.'


#0: Lex and Parse mainfile
#1: Find all includes and expand them
#2: Find all macros and definitions
#3: Get all lengths and set all positions
#4: Get all words

class Statement:
    def __init__(self):
        self.text = ''
        self.args = []

    def addarg(self, arg):
        self.args.append(arg)

    def setposition(self, position):
        self.position = position

    def getlength(self):
        raise NotImplementedError

    def getwords(self):
        raise NotImplementedError

    def new(token):
        pass

class Instruction(Statement):
    def __init__(self, text, assembler):
        self.text = text
        self.lineno = assembler.lineno
        self.file = assembler.file

    def addarg(self):
        pass





