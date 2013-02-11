import re

class AssemblyObject:
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

    def addwarn(self, warning, *args):
        if len(args) == 3:
            #text, file, lineno
            self.warnings.append((warning, args[0], args[1], args[2]))
        elif len(args) == 2:
            #text, token
            self.warnings.append((warning, args[0], args[1].file,
                                  args[1].lineno))
        elif len(args) == 1:
            #token
            self.warnings.append((warning, args[0].text, args[0].file,
                                  args[0].lineno))
        elif len(args) == 0:
            #global warning
            self.warnings.append((warning, '', None, 0))

    def pass100(self):
        '''Load self.mainfile, create a list of Tokens, handle include Tokens,
store in self.tokens.'''
        def filetotokens(file, passed=[]):
            tokens = []
            eoltoken = re.match(r'(?P<eol>)', '')
            self.lineno = 0
            for line in file.lines:
                line = stripcomments(line)
                self.lineno += 1
                if not line:
                    continue
                tokens.extend([Token(m, file, self.lineno) for m in
                               tokenre.finditer(line)])
                tokens.append(Token(eoltoken, file, self.lineno))
                tmp = tokenre.sub('', line).strip()
                if tmp != '':
                    self.addwarn('unrecognized tokens', tmp, file, lineno)
            index = -1
            while True:
                index += 1
                self.token = tokens[index]
                if self.token.type == 'ppinclude':
                    nexttoken = tokens[index + 1]
                    if nexttoken.type == 'string':
                        tmp = eval(nexttoken.text)
                        nexttoken.handled = True
                        self.token.args.append(nexttoken)
                        if tmp in passed:
                            self.adderror('recursive include', self.token)
                            continue
                        else:
                            tmp = self.getfile(tmp)
                            newtokens = self.filetotokens(tmp, passed + [tmp])
                            


class Token:
    def __init__(self, match, file, lineno):
        self.type = match.lastgroup
        self.text = match.group(match.lastindex)
        self.file = file
        self.lineno = lineno
        self.column = match.start()
        self.handled = False
        self.args = []


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


tokenre = re.compile(r'(?:\A|\s)(?:' +
                     r'(?P<string>(?:[lp]?"(?:[^"\\]|(?:\\.))*"[0nzc]?)|' +
                     r"(?:[lp]?'(?:[^'\\]|(?:\\.))*'[0nzc]?))|" +
                     r'(?P<label>(?::[a-z_.][a-z0-9_.]*)|' +
                     r'(?:[a-z_.][a-z0-9_.]*:))|' +
                     r'(?P<ppreserve>[#.]reserve)|' +
                     r'(?P<ppdefine>[#.]define)|' +
                     r'(?P<ppinclude>[#.]include)|' +
                     r'(?P<ppmacro>[#.]macro)|' +
                     r'(?P<ppendmacro>[#.]endmacro)|' +
                     r'(?P<ppalign>[#.]align)|' +
                     r'(?P<pplongform>[#.]longform)|' +
                     r'(?P<ppshortform>[#.]shortform)|' +
                     r'(?P<ppbinfooter>[#.]binfooter)|' +
                     r'(?P<ppendfooter>[#.]endfooter)|' +
                     r'(?P<dat>[#.]?dat)|' +
                     r'(?P<opcode>[a-z]{3})|' +
                     r'(?P<comma>,)|' +
                     r'(?P<expression>(?:-\s*)?(?:[a-z_.][a-z0-9_.]*|[0-9]+|' +
                     r'0x[0-9a-f]+)(?:\s*(?:\*|\+|\-|\/|\^|' +
                     r'\&|\||\=\=|\!\=|\<\=|\>\=|\<|\>|\>\>|\<\<|\%|' +
                     r'and|or)\s*(?:-\s*)?(?:[a-z_.][a-z0-9_.]*|' +
                     r'[0-9]+|0x[0-9a-f]+))*)' +
                     r')(?=\s|\Z)', re.IGNORECASE)

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
