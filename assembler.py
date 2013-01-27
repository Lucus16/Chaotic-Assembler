import re
import optparse

class assembler:
    #TOOLS
    
    def readfile(self, file):
        try:
            with open(file, 'r') as f:
                return f.readlines()
        except IOError:
            return None

    def writefile(self, file, lines):
        try:
            with open(file, 'w') as f:
                for line in lines:
                    print(line, end='')
            return True
        except IOError:
            return False

    def readbin(self, file, le = True):
        try:
            with open(file, 'rb') as f:
                b = list(f.read())
        except IOError:
            return None
        r = []
        for i in range(len(b) // 2):
            r.append((b[2 * i], b[2 * i + 1]))
        if le:
            return [a * 256 + b for a, b in r]
        else:
            return [a * 256 + b for b, a in r]

    def writebin(self, file, binary, le = True):
        r = []
        if le:
            for i in binary:
                r.append(i >> 8 & 255)
                r.append(i & 255)
        else:
            for i in binary:
                r.append(i & 255)
                r.append(i >> 8 & 255)
        try:
            with open(file, 'wb') as f:
                f.write(bytes(r))
            return True
        except IOError:
            return False

    def stripcomments(self, s):
        scl = re.sub(self.stringre,
                     lambda x: len(x.group(0)) * '-', s).find(';')
        return s.strip() if scl == -1 else s[:scl].strip()

    def adderr(self, error):
        self.errors.append((error, self.file, self.lineno))

    def addwarn(self, warning):
        self.warnings.append((warning, self.file, self.lineno))

    def adddefine(self, key, expression):
        key = key.lower()
        if key in self.defines or key in self.labels:
            return False
        self.defines[key] = expression.lower()
        self.definelocs[key] = (self.file, self.lineno)
        return True
        
    def addlabel(self, label):
        label = label.lower()
        if label[0] == '.':
            label = self.namespace + label
        else:
            self.namespace = label
        if label not in self.labels and label not in self.defines:
            self.labels[label] = self.wordno
            self.labellocs[label] = (self.file, self.lineno)
            return True
        else:
            self.adderr('Label or define already exists: ' + label)
            return False
    
    def stringtodat(self, string):
        # "" two chars per word
        # '' one char per word
        # l'' p'' length-prefixed
        # ''0 ''n ''z ''c null-terminated
        # returns a string with a list of numbers
        # TODO: Add escape characters
        lenpf = False
        nterm = False
        o = string
        if string in ['""', "''"]:
            self.addwarn('Empty string did not produce any result')
            return ''
        if string[0] in 'lp':
            lenpf = True
            string = string[1:]
        if string[-1] in '0nzc':
            nterm = True
            string = string[:-1]
        if string[0] not in '"\'' or string[0] != string[-1]:
            self.adderr('String format unknown: ' + o)
            return ''
        r = [ord(i) for i in string[1:-1]]
        l = len(r)
        if nterm:
            r.append(0)
        if string[0] == '"':
            #two chars per word
            s = []
            if len(r) % 2 == 1:
                r.append(0)
            for i in range(len(r) // 2):
                s.append((r[2 * i] << 8) + r[2 * i + 1])
            if lenpf:
                s = [l] + s
            return str(s)[1:-1]
        else:
            #one char per word
            if lenpf:
                r = [l] + r
            return str(r)[1:-1]
        
    
    def printreport(self):
        if not self.errors and not self.warnings:
            print('Assembly successful!')
        elif not self.errors:
            for w in self.warnings:
                print(w[1] + ' line ' + str(w[2]) + ': ' + w[0])
            print('\nAssembly successful, but there were ' +
                  str(len(self.warnings)) + ' warnings.')
        else:
            for e in self.errors:
                print(e[1] + ' line ' + str(e[2]) + ': ' + e[0])
            print('\nAssembly failed, there were ' + str(len(self.errors)) +
                  ' errors.')

    def printlines(self):
        b = [print(i[0]) for i in self.lines]

    def argval(self, arg, a = False):
        regs = list('abcxyzij')
        specs = ['sp', 'pc', 'ex']
        if arg in regs:
            return (regs.index(arg),)
        m = re.match(r'\[[ \t]*([abcxyzij])[ \t]*\]$', arg)
        if m:
            return (regs.index(m.group(1)) + 8,)
        m = re.match(r'\[[ \t]*([abcxyzij])[ \t]*([+-])(.*)\]$', arg)
        if m:
            tmp = self.parse(m.group(3))
            if tmp == None:
                return (regs.index(m.group(1)) + 16, 0)
            else:
                if m.group(2) == '+':
                    return (regs.index(m.group(1)) + 16, int(tmp))
                else:
                    return (regs.index(m.group(1)) + 16, (65536 - int(tmp)) % 65536)
        if a:
            m = re.match(r'(?:pop)|(?:\[[ \t]*sp[ \t]*\+\+[ \t]*\])', arg)
        else:
            m = re.match(r'(?:push)|(?:\[[ \t]*--[ \t]*sp[ \t]*\])', arg)
        if m:
            return (24,)
        m = re.match(r'(?:\[[ \t]*sp[ \t]*\])|(?:peek)', arg)
        if m:
            return (25,)
        m = re.match(r'\[[ \t]*sp[ \t]*([+-])(.*)\]', arg)
        if m:
            tmp = self.parse(m.group(2))
            if tmp == None:
                return (26, 0)
            else:
                if m.group(1) == '+':
                    return (26, int(tmp))
                else:
                    return (26, (65536 - int(tmp)) % 65536)
        m = re.match(r'pick[ \t](.*)', arg)
        if m:
            tmp = self.parse(m.group(1))
            if tmp == None:
                return (26, 0)
            else:
                return (26, int(tmp))
        if arg in specs:
            return (27 + specs.index(arg),)
        m = re.match(r'\[(.*)\]', arg)
        if m:
            tmp = self.parse(m.group(1))
            if tmp == None:
                return (30, 0)
            else:
                return (30, int(tmp))
        tmp = self.parse(arg)
        m = self.keyre.search(' ' + arg)
        if tmp == None:
            return (31, 0)
        else:
            tmp = int(tmp)
            if a and (tmp <= 30 or tmp == 65535) and not m:
                return ((tmp + 33) % 65536,)
            else:
                return (31, tmp)
        return (-1,)
    
    def arglen(self, arg, a = False):
        #arg is assumed to be .strip().lower()ed
        r = 0
        l = self.keyre.findall(' ' + arg)
        for i in l:
            if i not in self.reserved:
                return 1
        #when a define key is found, the length will be set to one, even if
        #that key would have evaluated between -1 and 30, as it should be.

        #We know there is no label or define now.
        if re.search(r'(?:0x[0-9a-fA-F]+)|(?:-?[0-9]+)', arg):
            if a and self.numm.match(arg):
                n = int(arg, 0)
                while n < 0:
                    n += 65536
                if n <= 30 or n == 65535:
                    return 0
        else:
            return 0
        return 1

    def codelen(self, code, errs = False):
        if code == 'sti':
            return (1, 'sti a, a')
        if code == 'std':
            return (1, 'std a, a')
        if code == 'rfi':
            return (1, 'rfi a')
        op = code[:3]
        if len(code) < 4:
            if op in self.opcodes:
                if errs: self.adderr('Expected two arguments: ' + code)
                return None
            if op in self.spcops:
                if errs: self.adderr('Expected one argument: ' + code)
                return None
            if op == 'dat':
                if errs: self.addwarn('Empty dat statement.')
                return None
            if errs: self.adderr('Could not understand: ' + code)
            return None
        if code[3] not in ' \t':
            if errs: self.adderr('Could not understand: ' + code)
            return None
        if op == 'dat':
            return (code.count(',') + 1, 'dat ' +
                    ', '.join([s.strip() for s in code[4:].split(',')]))
        if op == 'nul':
            if errs: self.adderr('Could not understand: ' + code)
            return None
        if op in self.opcodes:
            #basic opcode
            if code.count(',') > 1:
                if errs: self.adderr('Expected two arguments: ' + code)
                return None
            comma = code.find(',')
            if comma == -1:
                if errs: self.adderr('Expected two arguments: ' + code)
                return None
            argb = code[4:comma].strip()
            arga = code[comma + 1:].strip()
            if argb == '' or arga == '':
                if errs: self.adderr('Expected two arguments: ' + code)
                return None
            return (1 + self.arglen(argb) + self.arglen(arga, True),
                    op + ' ' + argb + ', ' + arga)
        if op in self.spcops:
            #advanced opcode
            if code.count(',') > 0:
                if errs: self.adderr('Expected one argument: ' + code)
                return None
            arga = code[4:].strip()
            if arga == '':
                if errs: self.adderr('Expected one argument: ' + code)
                return None
            return (1 + self.arglen(arga, True), op + ' ' + arga)
        if errs: self.adderr('Could not understand: ' + code)
        return None

    def reset(self):
        self.namespace = ''
        self.errors = []     #(error, file, lineno)
        self.warnings = []   #(warn, file, lineno)
        self.lines = []      #(line, file, lineno)
        self.defines = {}    #expr or val
        self.labels = {}     #wordno
        self.definelocs = {} #(file, lineno)
        self.labellocs = {}  #(file, lineno)
        self.file = ''
        self.lineno = 0
        self.basefile = ''
        self.words = []

    #CONSTANTS
    opcodes = ['spc', 'set', 'add', 'sub', 'mul', 'mli', 'div', 'dvi',
               'mod', 'mdi', 'and', 'bor', 'xor', 'shr', 'asr', 'shl',
               'ifb', 'ifc', 'ife', 'ifn', 'ifg', 'ifa', 'ifl', 'ifu',
               'nul', 'nul', 'adx', 'sbx', 'nul', 'nul', 'sti', 'std']
    spcops = ['nul', 'jsr', 'nul', 'nul', 'nul', 'nul', 'nul', 'nul',
              'int', 'iag', 'ias', 'rfi', 'iaq', 'nul', 'nul', 'nul',
              'hwn', 'hwq', 'hwi', 'nul', 'nul', 'nul', 'nul', 'nul',
              'nul', 'nul', 'nul', 'nul', 'nul', 'nul', 'nul', 'nul']
    values = ['a', 'b', 'c', 'x', 'y', 'z', 'i', 'j',
              '[a]', '[b]', '[c]', '[x]', '[y]', '[z]', '[i]', '[j]',
              '[a+nw]', '[b+nw]', '[c+nw]', '[x+nw]',
              '[y+nw]', '[z+nw]', '[i+nw]', '[j+nw]',
              'poppush', 'peek', 'pick nw', 'sp', 'pc', 'ex', '[nw]', 'nw'] + \
              [str(i) for i in range(-1, 31)]
    reserved = ['a', 'b', 'c', 'x', 'y', 'z', 'i', 'j', 'pc', 'sp', 'ex',
                'peek', 'pick', 'push', 'pop']
    LE = True
    BE = False

    #REGULAR EXPRESSIONS
    numm = re.compile(r'(?:(?:0x[0-9a-f]+)|(?:-?[0-9]+))\Z')
    stringre = re.compile(r'(?:"(?:[^"\\]|(?:\\.))*")|' +
                          r"(?:'(?:[^'\\]|(?:\\.))*')")
    stringm = re.compile(r'(?:"(?:[^"\\]|(?:\\.))*")|' +
                         r"(?:'(?:[^'\\]|(?:\\.))*')\Z")
    strpre = re.compile(r'(?:[lp]?"(?:[^"\\]|(?:\\.))*"[0nzc]?)|' +
                          r"(?:[lp]?'(?:[^'\\]|(?:\\.))*'[0nzc]?)")
    strpm = re.compile(r'(?:[lp]?"(?:[^"\\]|(?:\\.))*"[0nzc]?)|' +
                         r"(?:[lp]?'(?:[^'\\]|(?:\\.))*'[0nzc]?)\Z")
    localre = re.compile(r'(?<=[^A-Za-z0-9_.])\.[A-Za-z_.][A-Za-z0-9_.]*' +
                         r'(?=[^A-Za-z0-9_.]|\Z)')
    keyre = re.compile(r'(?<=[^A-Za-z0-9_.])[A-Za-z_.][A-Za-z0-9_.]*' +
                       r'(?=[^A-Za-z0-9_.]|\Z)')
    keym = re.compile(r'[A-Za-z_.][A-Za-z0-9_.]*\Z')
    labelm = re.compile(r'(?:(:[A-Za-z_.][A-Za-z0-9_.]*)(?:(?:[\s]+(.*))|\Z))')
    label2m = re.compile(r'(?:([A-Za-z_.][A-Za-z0-9_.]*:)(?:(?:[\s]+(.*))|\Z))')
    wsre = re.compile(r'[\s]+')
    datm = re.compile(r'(?:((?::[A-Za-z_.][A-Za-z0-9_.]*)|' +
                      r'(?:[A-Za-z_.][A-Za-z0-9_.]*:))[\s]+)?\.?dat[\s]')
    notwsre = re.compile(r'[^\s]+')
    definem = re.compile(r'[.#]define[\s]')
    reservem = re.compile(r'[.#]reserve[\s]')
    includem = re.compile(r'[.#]include[\s]')
    
    
    def __init__(self, file = None, verbose = False):
        self.reset()
        self.verbose = verbose
        if file:
            if verbose:
                print('assembler.py is assembling: ' + file + '\n')
            self.basefile = file
            self.file = file
            self.lines = self.loadfile()
            if self.lines == 'empty':
                print('Assembly failed, the file is empty.')
            else:
                self.checkdefines(False)
                self.getlabels()
                self.checkdefines()
                self.assemble()
                if verbose:
                    self.printreport()

    def loadfile(self):
        lines = self.readfile(self.file)
        if lines == None:
            return None
        if lines == []:
            return 'empty'
        r = []
        toskip = 0
        self.lineno = 0
        for line in lines:
            self.lineno += 1
            line = self.stripcomments(line)
            if toskip:
                toskip -= 1
                continue
            if not line:
                continue
            while line[-1] == '\\' and self.lineno + toskip < len(lines):
                line = line[:-1] + self.stripcomments(lines[self.lineno +
                                                            toskip])
                toskip += 1
            
            if self.includem.match(line):
                newfile = self.stringre.search(line, 9)
                if line[9:].strip() == '':
                    self.adderr('Missing argument: ' + line)
                    continue
                elif not newfile:
                    self.adderr('String expected: ' + line)
                    continue
                newfile = newfile.group(0)
                file = self.file
                lineno = self.lineno
                folder = max(file.rfind('/'), file.rfind('\\'))
                folder = file[:folder + 1] if folder >= 0 else ''
                self.file = folder + newfile[1:-1]
                newr = self.loadfile()
                self.lineno = lineno
                self.file = file
                if newr == None:
                    self.adderr('File could not be accessed: ' + newfile)
                    continue
                elif newr == 'empty':
                    self.addwarn('File is empty: ' + newfile)
                    continue
                else:
                    r.extend(newr)
                    continue
            elif self.definem.match(line):
                args = self.notwsre.findall(line, 8)
                if len(args) == 0:
                    self.adderr('Missing arguments: ' + line)
                elif (not self.keym.match(args[0])) or args[0] in self.reserved:
                    self.adderr('Invalid key: ' + args[0])
                elif len(args) == 1:
                    self.adderr('Value or expression expected: ' + line)
                elif not self.adddefine(args[0], ' '.join(args[1:])):
                    self.adderr('Duplicate key: ' + args[0])
                continue
            m = self.datm.match(line)
            if m: #.dat
                e = m.group(1) + ' ' if m.group(1) else ''
                line = self.strpre.sub(lambda x: self.stringtodat(x.group(0)),
                                       line)
                line = e + 'dat ' + line[len(m.group(0)):]
            r.append([line.lower(), self.file, self.lineno])
        return r

    def checkdefines(self, unknownerrs = True):
        for key in self.defines:
            self.file, self.lineno = self.definelocs[key]
            tmp = self.parse(key, [], unknownerrs)
            if tmp != None and not unknownerrs:
                reg = re.compile(r'(?<=[^A-Za-z0-9_.])' + key +
                                 r'(?=[^A-Za-z0-9_.]|\Z)')
                rep = str(self.defines[key])
                for i in range(len(self.lines)):
                    self.lines[i][0] = reg.sub(rep, ' ' + self.lines[i][0])[1:]

    def getlabels(self):
        i = -1
        lines = []
        self.wordno = 0
        for line, self.file, self.lineno in self.lines:
            i += 1
            while True:
                line = line.strip()
                if not line:
                    break
                match = self.labelm.match(line)
                if not match:
                    match = self.label2m.match(line)
                if match:
                    if match.group(1)[0] == ':':
                        self.addlabel(match.group(1)[1:])
                    else:
                        self.addlabel(match.group(1)[:-1])
                    if match.group(2):
                        line = match.group(2)
                        continue
                    else:
                        line = ''
                        break
                if self.reservem.match(line):
                    tmp = self.parse(line[9:], [], False)
                    if tmp and tmp > 0:
                        line = 'dat 0' + ', 0' * (tmp - 1)
                        self.wordno += tmp
                        break
                    elif tmp and tmp == 0:
                        addwarn('Redundant statement: .reserve 0')
                        line = ''
                        break
                    elif tmp:
                        adderr("Can't reserve a negative amount: " + tmp)
                        line = ''
                        break
                    else:
                        adderr('Could not solve expression: ' + line[9:])
                        line = ''
                        break
                #add namespace to lines
                line = self.localre.sub(lambda m: self.namespace + m.group(0),
                                        ' ' + line)[1:]
                tmp = self.codelen(line, True)
                if tmp:
                    self.wordno += tmp[0]
                    line = tmp[1]
                else:
                    line = ''
                break
            if line:
                lines.append([line, self.file, self.lineno])
        self.lines = lines
    
    def parse(self, expr, tried = [], unknownerrs = True):
        keys = self.keyre.findall(' ' + expr)
        if not keys:
            try:
                r = eval(expr)
            except (TypeError, SyntaxError, NameError):
                self.adderr('Failed to parse: ' + expr)
                return None
            return r
        for key in keys:
            if key in self.reserved:
                self.adderr('Invalid key: ' + key)
                return None
            if key in tried:
                self.adderr('Recursive defenition detected: ' + key)
                return None
            if key in self.labels:
                expr = re.sub(r'(?<=[^A-Za-z0-9_.])' + key +
                       r'(?=[^A-Za-z0-9_.])', str(self.labels[key]),
                       ' ' + expr + ' ')[1:-1]
                continue
            elif key in self.defines:
                if type(self.defines[key]) != type(3):
                    tried.append(key)
                    tmp = self.parse(self.defines[key], tried, unknownerrs)
                    if tmp == None:
                        return None
                    else:
                        self.defines[key] = tmp
                expr = re.sub(r'(?<=[^A-Za-z0-9_.])' + key +
                              r'(?=[^A-Za-z0-9_.])', str(self.defines[key]),
                              ' ' + expr + ' ')[1:-1]
                continue
            else:
                if unknownerrs:
                    self.adderr('Unknown label detected: ' + key)
                return None
        try:
            r = eval(expr)
        except (TypeError, SyntaxError, NameError):
            self.adderr('Failed to parse: ' + expr)
            return None
        return r

    def assemble(self):
        #ASSUME:
        #opc argb, arga
        #dat arg, arg, arg, arg, ...
        for line, self.file, self.lineno in self.lines:
            op = line[:3]
            if op == 'dat':
                args = line[4:].split(', ')
                for arg in args:
                    tmp = self.parse(arg)
                    if tmp == None:
                        self.words.append(0)
                    else:
                        self.words.append(tmp)
                continue
            comma = line.find(', ')
            if comma == -1:
                arga = line[4:]
                argb = ''
            else:
                argb = line[4:comma]
                arga = line[comma + 2:]
            if op in self.opcodes:
                o = self.opcodes.index(op)
                b, a = self.argval(argb), self.argval(arga, True)
                self.words.append(o + 32 * b[0] + 1024 * a[0])
                if len(a) == 2:
                    self.words.append(a[1])
                if len(b) == 2:
                    self.words.append(b[1])
            if op in self.spcops:
                o = self.spcops.index(op)
                a = self.argval(arga, True)
                self.words.append(32 * o + 1024 * a[0])
                if len(a) == 2:
                    self.words.append(a[1])



if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-q', '--quiet', help = "don't print errors, warnings or \
status messages")
    options, args = parser.parse_args()

    if len(args) < 2:
        infile = input('Enter input file: ')
        outfile = input('Enter output file: ')
    else:
        infile = args[0]
        outfile = args[1]
    
    a = assembler(infile, not options.quiet)
    if a.writebin(outfile, a.words, False):
        print('Binary stored in: ' + outfile)
    else:
        print('Unable to access: ' + outfile)



