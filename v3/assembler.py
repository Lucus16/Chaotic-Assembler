#import disassembler
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

class Source:
    def __init__(self, file, line, column):
        self.file = file
        self.line = line
        self.col = column

    def __repr__(self):
        return 'Source(' + repr(self.file) + ', ' + repr(self.line) + ', ' + \
               repr(self.col) + ')'

    def __str__(self):
        return self.file.filepath + ' ln' + str(self.line) + ' col' + \
               str(self.col)


class Token:
    def __init__(self, text, tokentype, source):
        self.text = text
        self.type = tokentype
        self.source = source

    def __repr__(self):
        return 'Token(' + repr(self.text) + ', ' + repr(self.type) + ', ' + \
               repr(self.source) + ')'


class Line:
    def __init__(self, text, source):
        self.text = text
        self.source = source

    def __repr__(self):
        return 'Line(' + repr(self.text) + ', ' + repr(self.source) + ')'


class Error:
    def __init__(self, text, token):
        self.text = text
        self.token = token

    def __repr__(self):
        return 'Error(' + repr(self.text) + ', ' + repr(self.token) + ')'

    def __str__(self):
        return 'Error: ' + str(self.token.source) + ': ' + self.text + \
               ': ' + self.token.text


class Warning:
    def __init__(self, text, token):
        self.text = text
        self.token = token

    def __repr__(self):
        return 'Warning(' + repr(self.text) + ', ' + repr(self.token) + ')'


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
        self.line = line.text
        self.src = line.source
        self.pos = 0
        self.end = len(self.line)
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
                self.pos = self.end
                return Line(self.line[self.history[-1]:],
                        Source(self.src.file, self.src.line,
                               self.src.col + self.history[-1]))
            self.pos = match.end()
            if self.names[match.lastindex] != None:
                return Token(match.group(), self.names[match.lastindex],
                    Source(self.src.file, self.src.line,
                           self.src.col + self.history[-1]))
            else:
                self.history[-1] = self.pos

    def isempty(self):
        return self.pos >= self.end


class AssemblerData:
    def __init__(self):
        self.success = False
        self.errors = []
        self.warnings = []

    def __str__(self):
        return 'Success: ' + str(self.success) + '\n' + \
               'There were ' + str(len(self.warnings)) + ' warnings:\n' + \
               '\n'.join([str(x) for x in self.warnings]) + \
               'There were ' + str(len(self.errors)) + ' errors:\n' + \
               '\n'.join([str(x) for x in self.errors])


class Assembler:
    def __init__(self, mainfile=None):
        self.files = {}
        
        if mainfile != None:
            assert isinstance(mainfile, str)
            self.mainfile = mainfile
            self.statements = self.process(self.load(self.mainfile))

    def assemble(self, file):
        ad = AssemblerData()
        #load file, get lines
        try:
            lines = self.load(file)
        except IOError:
            ad.success = False
            ad.errors.append(Error('File IO error', Token(file,
                'file', Source('__main__', 1, 0))))
            return ad
        ad.lines = lines
        #lex lines, get tokens
        tokens = []
        for line in lines:
            tmptokens = self.lex(line)
            if isinstance(tmptokens[-1], Line):
                tokens.extend(tmptokens[:-1])
                ad.errors.append(Error('Could not tokenize', tmptokens[-1]))
            else:
                tokens.extend(tmptokens)
        ad.tokens = tokens
        #parse tokens, get statements
        statements = [DummyStatement()]
        for token in tokens:
            if token.type in ['label', 'preprocessor', 'basic', 'advanced',
                              'data']:
                statements.append(Statement.new(token))
            else:
                statements[-1].addarg(token)
        for x in statements[0].args:
            ad.errors.append(Error('Argument before statement', x))
        statements = statements[1:]
        #load, lex, parse and expand includes
        #get macros and defines
        #set positions and get lengths
        pos = 0
        for statement in statements:
            statement.setposition(pos)
            pos += statement.getlength()
        #get words
        words = []
        for statement in statements:
            words.extend(statement.getwords())
        #get warnings and errors
        for statement in statements:
            ad.errors.extend(statement.errors)
            ad.warnings.extend(statement.warnings)
        #finish AssemblerData object and return it.
        ad.words = words
        return ad

    def load(self, file):
        file = self.getfile(file)
        lines = file.lines
        out = []
        for i in range(len(lines)):
            lines[i] = lines[i].rstrip()
            tmp = len(lines[i])
            lines[i] = lines[i].lstrip()
            if lines[i]:
                out.append(Line(lines[i], Source(file, i + 1,
                    tmp - len(lines[i]) + 1)))
        return out

    def getfile(self, file):
        if file not in self.files:
            self.files[file] = DasmFile(file)
        return self.files[file]

    def adderr(*args):
        self.errors.append(Error(*args))

    def addwarn(*args):
        self.warnings.append(Warn(*args))

    def lex(self, line):
        lex = Lexer(rules, re.IGNORECASE).lex(line)
        return list(lex)

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
        assert isinstance(file, str) or file is None
        assert isinstance(lines, list) or lines is None
        
        self.filepath = file
        if lines != None:
            self.lines = lines
        elif file != None:
            self.path, self.name, self.ext = splitpath(file)
            self.filename = self.name + self.ext
            with open(file, 'r') as f:
                self.lines = [x.rstrip() for x in f.readlines()]

    def __repr__(self):
        return 'DasmFile(' + repr(self.filepath) + ')'

    def __str__(self):
        return '\n'.join(self.lines)


class TextFile:
    def __init__(self, filepath=None, lines=None):
        assert isinstance(filepath, str) or file is None
        assert isinstance(lines, list) or lines is None

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
    (r'[#.]?data?', 'data'),
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

#Main types are label, preprocessor, basic, advanced, data

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
#5: Get all warnings and errors

class Statement:
    def __init__(self, text, source):
        self.text = text
        self.source = source
        self.args = []
        self.errors = []
        self.warnings = []

    def addarg(self, arg):
        self.args.append(arg)

    def setposition(self, position):
        self.position = position

    def getlength(self):
        raise NotImplementedError

    def getwords(self):
        raise NotImplementedError

    def __repr__(self):
        return 'Statement(' + repr(self.text) + ', ' + repr(self.source) + \
               ', args=[' + ', '.join([repr(x) for x in self.args]) + '])'

    def new(token): #no self, call as Statement.new()
        text = token.text
        type_ = token.type
        source = token.source
        if type_ == 'basic' or type_ == 'advanced':
            return Instruction(text, source)
        if type_ == 'data':
            return Data(text, source)
        if type_ == 'label':
            return Label(text, source)
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


class Label(Statement):
    def __init__(self, text, source):
        self.text = text
        self.source = source
        self.args = []
        self.errors = []
        self.warnings = []

    def addarg(self, token):
        self.errors.append(Error('Label statement does not accept arguments',
                                 token))

    def setposition(self, pos):
        self.pos = pos

    def getlength(self):
        return 0

    def getwords(self):
        return []


class Data(Statement):
    def __init__(self, text, source):
        self.text = text
        self.source = source
        self.args = []
        self.errors = []
        self.warnings = []

    def addarg(self, token):
        self.args.append(token)

    def setposition(self, pos):
        self.pos = pos

    def getlength(self):
        try:
            return self.len
        except AttributeError:
            self.len = len([x for x in self.args if x.type == ',']) + 1
            return self.len

    def getwords(self):
        try:
            return self.words
        except AttributeError:
            self.words = []
            args = [[]]
            for arg in self.args:
                if arg.type == ',':
                    args.append([])
                else:
                    args[-1].append(arg)
                    
            #old
            self.words = []
            argstr = ''.join([x.text for x in self.args])
            args = argstr.split(',')
            for x in args:
                self.words.append(int(x, 0))
            assert len(self.words) == self.len
            return self.words


class Instruction(Statement):
    def addarg(self, token):
        pass

    def somefn(self, lex):
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


class DummyStatement(Statement):
    def __init__(self):
        self.text = 'Dummy'
        self.source = None
        self.args = []


