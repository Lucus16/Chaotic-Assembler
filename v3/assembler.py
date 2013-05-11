import disassembler
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
    def __init__(self, rules, flags=0):
        self.rules = rules
        self.names = [''] + [x[-1] for x in rules]
        self.regex = re.compile('|'.join('(' + x[0] + ')' for x in rules),
                                flags)
        assert not self.regex.match(''), \
               'One of the provided rules matches the empty string.'

    def __iter__(self):
        return self

    def lex(self, line):
        self.history = []
        self.line = line
        self.pos = 0
        self.end = len(line)
        return self

    def back(self, number=1):
        self.pos = self.history[-number]
        self.history = self.history[:-number]
        return self

    def __next__(self):
        if self.pos >= self.end:
            raise StopIteration
        self.history.append(self.pos)
        while True:
            match = self.regex.match(self.line, self.pos)
            if match == None:
                tmp = self.line[self.pos:]
                self.pos = self.end
                return tmp
            self.pos = match.end()
            if self.names[match.lastindex] != None:
                return (match.group(), self.names[match.lastindex])

    def isempty(self):
        return self.pos >= self.end

class Assembler:
    def __init__(self, mainfile=None):
        self.files = {}
        self.errors = []
        self.warnings = []
        
        if mainfile != None:
            assert isinstance(mainfile, str)
            self.mainfile = mainfile
            self.statements = self.process(self.load(self.mainfile))

    def load(self, file):
        lines = self.getfile(file).lines
        

    def getfile(self, file):
        if file not in self.files:
            self.files[file] = DasmFile(file)
        return self.files[file]

    def adderr(*args):
        self.warnings.append(Error(*args))

    def addwarn(*args):
        self.errors.append(Warn(*args))

    def parse(self, file):
        file = self.getfile(file) #May raise IOError
        lex = Lexer(rules)
        stmts = []
        lineno = 0
        
        for line in file.lines:
            lineno += 1
            lex.lex(stripcomments(line))
            while not lex.isempty():
                token = next(lex, None)
                if token[1] in ['basic', 'advanced', 'label', 'preprocessor',
                                'data']:
                    stmts.append(Statement.new(token, file, lineno))
                else:
                    stmts[-1].addarg(lex.back(1))
        
        stmts2 = []
        for stmt in stmts:
            if isinstance(stmt, Include):
                stmts2.extend(self.parse(stmt.args[0]))
            else:
                stmts2.append(stmt)
        return stmts2


class DasmFile:
    def __init__(self, file=None, lines=None):
        assert isinstance(file, (None, str))
        assert isinstance(lines, (None, list))
        
        self.filepath = file
        if lines != None:
            self.lines = lines
        elif file != None:
            self.path, self.name, self.ext = splitpath(file)
            self.filename = self.name + self.ext
            with open(file, 'r') as f:
                self.lines = [x.rstrip() for x in f.readlines()]


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
    'align',
    'longform',
    'shortform',
    'relocate',
    'endrelocate',
    ]
rules = [
    (r'\s+', None),
    (r'(?:[lp]?"(?:[^"\\]|(?:\\.))*"(?:[0nzc]\b)?)|' +
     r"(?:[lp]?'(?:[^'\\]|(?:\\.))*'(?:[0nzc]\b)?)", 'string'),
    (r'(?::[a-z_.][a-z0-9_.]*)|(?:[a-z_.][a-z0-9_.]*:)', 'label'),
    (r'[#.](?:' + '|'.join(ppcommands) + ')', 'preprocessor'),
    (r'[#.]?dat', 'data'),
    (r'(?:set|add|sub|mul|div|mod|mli|dvi|mdi|and|bor|xor|shl|shr|asr|' +
     r'ife|ifn|ifb|ifc|ifg|ifl|ifa|ifu|adx|sbx|sti|std)\b', 'basic'),
    (r'(?:jsr|hwn|hwq|hwi|ias|iag|iaq|int|rfi)\b', 'advanced'),
    (r'(?:a|b|c|x|y|z|i|j)\b', 'register'),
    ('(?:pc)\b', 'pc'),
    ('(?:sp)\b', 'pc'),
    ('(?:ex)\b', 'ex'),
    ('(?:push)\b', 'push'),
    ('(?:pop)\b', 'pop'),
    ('(?:peek)\b', 'peek'),
    ('(?:pick)\b', 'pick'),
    (r'[a-z_.][a-z0-9_.]*', 'identifier'),
    (r'(?:0b[0-1]+)|(?:0x[0-9a-f]+)|(?:[0-9]+)', 'integer'),
    (r'\=\=|\<\=|\>\=|\<\<|\>\>|\!\=|\&\&|\|\||' +
     r'\||\!|\~|\^|\&|\%|\*|\/|\-|\+', 'operator'),
    ] + [('\\' + c, c) for c in ',$()[]{}']

##values = ['a', 'b', 'c', 'x', 'y', 'z', 'i', 'j', '[a]', '[b]', '[c]', '[x]',
##          '[y]', '[z]', '[i]', '[j]', '[a+n]', '[b+n]', '[c+n]', '[x+n]',
##          '[y+n]', '[z+n]', '[i+n]', '[j+n]', 

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

def getexpr(lex):
    expect = True
    text = ''
    while True:
        token = next(lex, None)
        if token == None:
            if expect:
                #add parsing error
                return text
            else:
                return text
        if expect:
            if token[1] == '(':
                text += token[0]
            elif token[0] in ['+', '-', '~']: #unary operator
                text += token[0]
            elif token[1] in ['string', 'identifier', 'number', '$']:
                text += token[0]
                expect = False
            else:
                lex.back(1)
                #add parsing error
        else:
            if token[1] == ')':
                text += token[0]
            elif token[1] == 'operator':
                text += token[0]
            else:
                lex.back(1)
                return text #done parsing this expression

def getval(lex):
    vals = {'a': 0, 'b': 1, 'c': 2, 'x': 3, 'y': 4, 'z': 5, 'i': 6, 'j': 7,
            'push': 24, 'pop': 24, 'peek': 25, 'sp': 27, 'pc': 28, 'ex': 29}
    text = ''
    token = next(lex, None)
    if token == None:
        return
    elif token[1] in ['register', 'push', 'pop', 'peek', 'sp', 'pc', 'ex']:
        return (token[0], vals[token[0]]) #text, value
    elif token[1] == 'pick':
        pass
    


#0: Lex and Parse mainfile
#1: Find all includes and expand them
#2: Find all macros and definitions
#3: Get all lengths and set all positions
#4: Get all words

class Statement:
    def __init__(self, text, file, lineno):
        self.text = text
        self.file = file
        self.lineno = lineno
        self.args = []

    def addarg(self, arg):
        self.args.append(arg)

    def setposition(self, position):
        self.position = position

    def getlength(self):
        raise NotImplementedError

    def getwords(self):
        raise NotImplementedError

    def new(token, file, lineno): #no self, call as Statement.new()
        text, type_ = token
        if type_ == 'basic' or type_ == 'advanced':
            return Instruction(text, file, lineno)
        if type_ == 'data':
            return Data(text, file, lineno)
        if type_ == 'label':
            return Label(text, file, lineno)
        if type_ == 'preprocessor':
            if text == 'reserve':
                return ppReserve(file, lineno)
            if text == 'define':
                return ppDefine(file, lineno)
            if text == 'include':
                return ppInclude(file, lineno)
            if text == 'macro':
                return ppMacro(file, lineno)
            if text == 'align':
                return ppAlign(file, lineno)
            if text == 'falealign':
                return ppFakealign(file, lineno)
            if text == 'relocate':
                return ppRelocate(file, lineno)
            if text == 'endrelocate':
                return ppEndrelocate(file, lineno)
            if text == 'longform':
                return ppLongform(file, lineno)
            if text == 'shortform':
                return ppShortform(file, lineno)

class Instruction(Statement):
    def addarg(self, lex):
        vals = {'a': 0, 'b': 1, 'c': 2, 'x': 3, 'y': 4, 'z': 5, 'i': 6, 'j': 7,
                'push': 24, 'pop': 24, 'peek': 25, 'sp': 27, 'pc': 28, 'ex': 29}
        argtext = ''
        token = next(lex, None)
        if token == None:
            return
        elif token[1] in ['register', 'push', 'pop', 'peek', 'sp', 'pc', 'ex']:
            self.args.append((token[0], vals[token[0]])) #text, value
        elif token[1] == 'pick':
            pass





