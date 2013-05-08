#!/usr/bin/env python3.3

import optparse

class disassembler:
    values = ['a', 'b', 'c', 'x', 'y', 'z', 'i', 'j', '[a]', '[b]', '[c]',
              '[x]', '[y]', '[z]', '[i]', '[j]', '[a+n]', '[b+n]', '[c+n]',
              '[x+n]', '[y+n]', '[z+n]', '[i+n]', '[j+n]', 'pop', '[sp]',
              '[sp+n]', 'sp', 'pc', 'ex', '[n]', 'n'] + \
             [str(n) for n in range(-1, 31)]
    opcodes = ['spc', 'set', 'add', 'sub', 'mul', 'mli', 'div', 'dvi',
               'mod', 'mdi', 'and', 'bor', 'xor', 'shr', 'asr', 'shl',
               'ifb', 'ifc', 'ife', 'ifn', 'ifg', 'ifa', 'ifl', 'ifu',
               'nul', 'nul', 'adx', 'sbx', 'nul', 'nul', 'sti', 'std']
    spcops = ['nul', 'jsr', 'nul', 'nul', 'nul', 'nul', 'nul', 'nul',
              'int', 'iag', 'ias', 'rfi', 'iaq', 'nul', 'nul', 'nul',
              'hwn', 'hwq', 'hwi', 'nul', 'nul', 'nul', 'nul', 'nul',
              'nul', 'nul', 'nul', 'nul', 'nul', 'nul', 'nul', 'nul']
    
    def __init__(self, data=None):
        if isinstance(data, str):
            self.words = self.loadfile(data)
        elif isinstance(data, list):
            self.words = data
        elif data != None:
            raise TypeError('Expected string or list')
        self.it = worditer(self.words)

    def loadfile(self, file):
        with open(file, 'rb') as f:
            b = list(f.read())
        return [b[i] * 256 + b[i + 1] for i in range(0, len(b), 2)]

    def hexval(self, val, length=4):
        r = hex(val)
        return '0x' + (length + 2 - len(r)) * '0' + r[2:]

    def getinstruction(self, it=None):
        if it == None:
            it = self.it
        def getarg(val, a=True):
            if a:
                val = val >> 10
            else:
                val = (val >> 5) & 0x1f
                if val == 24: return 'push'
            return self.values[val]
        special = False
        out = ''
        l = 0
        try:
            n = next(it)
            out = self.opcodes[n & 31]
            if out == 'spc':
                out = self.spcops[(n >> 5) & 31]
                if out != 'nul':
                    out += ' ' + getarg(n)
                    special = True
            if out == 'nul':
                out = 'dat ' + self.hexval(n)
            elif not special:
                out += ' ' + getarg(n, False) + ', ' + getarg(n)
            while 'n' in out[4:]:
                i = out.rfind('n')
                out = out[:i] + self.hexval(next(it, 0)) + out[i+1:]
            out += ' ' * (40 - len(out)) + ';' + self.hexval(it.c) + ': '
            lastwords = it.getlastwords()
            l = len(lastwords)
            out += ', '.join([self.hexval(x) for x in lastwords])
        except StopIteration:
            pass
        return (out, l)
    get = getinstruction

    def disassemble(self):
        it = worditer(self.words)
        getnext = lambda: self.getinstruction(it)[0]
        n = getnext()
        out = []
        while n != '':
            if n.startswith('dat'):
                o = n
                t = n[:10]
                c = 0
                while n.startswith(t):
                    c += 1
                    n = getnext()
                if c > 1:
                    out.append('.fill ' + str(c) + ' ' + t[4:])
                else:
                    out.append(o)
            else:
                out.append(n)
                n = getnext()
        return out
    go = disassemble


class worditer:
    def __init__(self, words):
        self.setwords(words)

    def __iter__(self):
        return self

    def __next__(self):
        self.a += 1
        if self.a >= self.l:
            raise StopIteration
        return self.words[self.a]

    def back(self, n=1):
        self.a -= n
        return self

    def setpos(self, pos):
        self.a = self.c = pos
        return self

    def setwords(self, words):
        self.words = words
        self.a = -1
        self.c = 0
        self.l = len(self.words)
        return self

    def getlastwords(self):
        tmp = self.words[self.c:self.a + 1]
        self.c = self.a + 1
        return tmp

if __name__ == '__main__':
    parser = optparse.OptionParser()
    options, args = parser.parse_args()

    if len(args) == 1:
        infile = args[0]
        tmp = infile.rfind('.')
        outfile = (infile[:tmp] if tmp != -1 else infile) + '.dasm'
    elif len(args) == 0:
        infile = input('Enter input file: ')
        outfile = input('Enter output file: ')
        if outfile == '':
            tmp = infile.rfind('.')
            outfile = (infile[:tmp] if tmp != -1 else infile) + '.dasm'
    else:
        infile = args[0]
        outfile = args[1]

    d = disassembler(infile)
    try:
        with open(outfile, 'w') as f:
            for line in d.disassemble():
                f.write(line + '\n')
    except IOError:
        print('Couldn\'t access file: ' + outfile)
