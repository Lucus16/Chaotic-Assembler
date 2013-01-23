import re

opcodes = {'set': 1, 'add': 2, 'sub': 3, 'mul': 4, 'mli': 5, 'div': 6, \
           'dvi': 7, 'mod': 8, 'mdi': 9, 'and': 10, 'bor': 11, 'xor': 12, \
           'shr': 13, 'asr': 14, 'shl': 15, 'ifb': 16, 'ifc': 17, 'ife': 18, \
           'ifn': 19, 'ifg': 20, 'ifa': 21, 'ifl': 22, 'ifu': 23, 'adx': 26, \
           'sbx': 27, 'sti': 30, 'std': 31, 'jsr': 1*32, 'int': 8*32, \
           'iag': 9*32, 'ias': 10*32, 'rfi': 11*32, 'iaq': 12*32, \
           'hwn': 16*32, 'hwq': 17*32, 'hwi': 18*32}
values = {'a': 0, 'b': 1, 'c': 2, 'x': 3, 'y': 4, 'z': 5, 'i': 6, 'j': 7, \
          '[a]': 8, '[b]': 9, '[c]': 10, '[x]': 11, '[y]': 12, '[z]': 13, \
          '[i]': 14, '[j]': 15, 'push': 24, 'pop': 24, 'peek': 25, \
          'sp': 27, 'pc': 28, 'ex': 29}
reserved = ['a', 'b', 'c', 'x', 'y', 'z', 'i', 'j', 'pc', 'sp', 'ex', \
            'peek', 'pick', 'push', 'pop']
stringre = r'(?:"(?:[^"\\]|(?:\\.))*")|' + r"(?:'(?:[^'\\]|(?:\\.))*')"
#old: r'(?:\"[^\"]*\")|(?:\'[^\']*\')'
labelre = r'[a-zA-Z_.][a-zA-Z_.0-9]*'
namespace = ''
opcodes2 = ['spc', 'set', 'add', 'sub', 'mul', 'mli', 'div', 'dvi', \
            'mod', 'mdi', 'and', 'bor', 'xor', 'shr', 'asr', 'shl', \
            'ifb', 'ifc', 'ife', 'ifn', 'ifg', 'ifa', 'ifl', 'ifu', \
            'nul', 'nul', 'adx', 'sbx', 'nul', 'nul', 'sti', 'std']
spcops = ['nul', 'jsr', 'nul', 'nul', 'nul', 'nul', 'nul', 'nul', \
          'int', 'iag', 'ias', 'rfi', 'iaq', 'nul', 'nul', 'nul', \
          'hwn', 'hwq', 'hwi', 'nul', 'nul', 'nul', 'nul', 'nul', \
          'nul', 'nul', 'nul', 'nul', 'nul', 'nul', 'nul', 'nul']
values2 = ['a', 'b', 'c', 'x', 'y', 'z', 'i', 'j', \
           '[a]', '[b]', '[c]', '[x]', '[y]', '[z]', '[i]', '[j]', \
           '[a+nw]', '[b+nw]', '[c+nw]', '[x+nw]', \
           '[y+nw]', '[z+nw]', '[i+nw]', '[j+nw]', \
           'poppush', 'peek', 'pick nw', 'sp', 'pc', 'ex', '[nw]', 'nw']
values2.extend([str(i) for i in range(-1, 31)])
           
           

def stripcomments(s):
    scl = re.sub(stringre, lambda x: len(x.group(0)) * '-', s).find(';')
    return s.strip() if scl == -1 else s[:scl].strip()

def arglen(arg, a = False):
    #arg is assumed to be .strip().lower()ed
    r = 0
    l = re.findall(r'[^a-zA-Z_.0-9]' + labelre, ' ' + arg)
    for i in l:
        if i[1:].lower() not in reserved:
            return 1
    #when a define key is found, the length will be set to one, even if
    #that key would have evaluated between -1 and 30, as it should be.

    #We know there is no label or define now.
    if re.search(r'(?:0x[0-9a-fA-F]+)|(?:-?[0-9]+)', arg):
        if a:
            match = re.match(r'(?:0x[0-9a-fA-F]+)|(?:-?[0-9]+)', arg)
            if match and len(match.group(0)) == len(arg):
                n = int(arg, 0)
                while n < 0:
                    n += 65536
                if n <= 30 or n == 65535:
                    return 0
    else:
        return 0
    return 1

def codelen(code):
    op = code[:3].lower()
    if op == 'dat':
        return code.count(',') + 1
    if op not in opcodes:
        return 0
    if opcodes[op] < 32:
        #basic opcode
        comma = code.find(',')
        if comma == -1:
            return 0
        arg1 = code[4:comma].strip().lower()
        arg2 = code[comma + 1:].strip().lower()
        if arg1 == '' or arg2 == '':
            return 0
        return 1 + arglen(arg1) + arglen(arg2, True)
    else:
        #advanced opcode
        arg1 = code[4:].strip()
        if arg1 == '':
            return 0
        return 1 + arglen(arg1, True)
   
def assemble(file, resolve = True):
    global namespace
        
    def argval(arg, a = False):
        if arg == '[cd_on_time+1]':
            pass
        regs = list('abcxyzij')
        specs = ['sp', 'pc', 'ex']
        if arg in regs:
            return (regs.index(arg),)
        m = re.match(r'\[[ \t]*([abcxyzij])[ \t]*\]$', arg)
        if m:
            return (regs.index(m.group(1)) + 8,)
        m = re.match(r'\[[ \t]*([abcxyzij])[ \t]*([+-])(.*)\]$', arg)
        if m:
            tmp = parse(m.group(3))
            if tmp == '#':
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
            tmp = parse(m.group(2))
            if tmp == '#':
                return (26, 0)
            else:
                if m.group(1) == '+':
                    return (26, int(tmp))
                else:
                    return (26, (65536 - int(tmp)) % 65536)
        m = re.match(r'pick[ \t](.*)', arg)
        if m:
            tmp = parse(m.group(1))
            if tmp == '#':
                return (26, 0)
            else:
                return (26, int(tmp))
        if arg in specs:
            return (27 + specs.index(arg),)
        m = re.match(r'\[(.*)\]', arg)
        if m:
            tmp = parse(m.group(1))
            if tmp == '#':
                return (30, 0)
            else:
                return (30, int(tmp))
        tmp = parse(arg)
        m = re.search(r'[^a-zA-Z0-9_.]' + labelre, ' ' + arg + ' ')
        if tmp == '#':
            return (31, 0)
        else:
            tmp = int(tmp)
            if a and (tmp <= 30 or tmp == 65535) and not m:
                return ((tmp + 33) % 65536,)
            else:
                return (31, tmp)
        return (-1,)

    def parse(expr, tried = []):
        #When parsing fails, return '#'
        if '#' in expr:
            adderr('Operator not allowed in expressions: #')
            return '#'
        #TODO: Make sure it doesn't change numbers in labels
        l = re.findall(r'[^a-zA-Z0-9_.]' + labelre, ' ' + expr)
        l = [i[1:] for i in l]
        for i in l:
            if i in tried:
                adderr('Recursive defenition detected: ' + i)
                return '#'
            if i in labels:
                expr = expr.replace(i, str(labels[i]))
            elif i in defines:
                if type(defines[i]) == type(3):
                    expr = expr.replace(i, str(defines[i]))
                else:
                    tmp = parse(defines[i], tried + [i])
                    if tmp == '#':
                        return '#'
                    else:
                        defines[i] = int(tmp)
                        expr = expr.replace(i, str(defines[i]))
            else:
                adderr('Unknown label detected: ' + i)
                return '#'
        try:
            r = eval(expr)
        except (TypeError, SyntaxError, NameError):
            adderr('Failed to parse: ' + expr)
            return '#'
        return str(int(r % 65536))
            
    
    def adderr(s):
        errors.append('Error at ' + file + ' line ' + str(lineno) + ': ' + s)
        
    def addlbl(label):
        global namespace
        label = label.lower()
        if label[0] == '.':
            if (namespace + label) not in labels and \
               (namespace + label) not in defines:
                labels[namespace + label] = wordno
                return True
            else:
                adderr('Label or define already exists: ' + label)
                return False
        else:
            if label not in labels and label not in defines:
                labels[label] = wordno
                namespace = label
                return True
            else:
                adderr('Label or define already exists: ' + label)
                return False

    path = file[:file.rfind('/') + 1]
    with open(file) as f:       #If file can't be accessed, an IOError will
        source = f.readlines()  #be thrown, callers must handle it.
    lineno = 0
    labels = {} #labels[name] = value
    defines = {} #defines[name] = expression
    wordno = 0
    result = []
    errors = []
    toskip = 0      #used to skip over lines that have already been processed
                    #because the line before them ended with \
    
    for line in source:
        lineno += 1
        line = stripcomments(line)
        #handle multi-line expressions
        if toskip:
            toskip -= 1
            continue
        while line[-1:] == '\\':
            try:
                line = stripcomments(line[:-1] + source[lineno + toskip])
                toskip += 1
            except IndexError as e:
                line = line[:-1]
        result.append(['', file, lineno])
        #promote local labels
        while line != '':
            line = line.strip()
            if not line:
                break
            #handle labels
            match = re.match(r':[a-zA-Z_.][a-zA-Z_.0-9]*', line)
            if match:
                addlbl(match.group(0)[1:])
                line = line[len(match.group(0)):]
                continue
            match = re.match(r'[a-zA-Z_.][a-zA-Z_.0-9]*:', line)
            if match:
                addlbl(match.group(0)[:-1])
                line = line[len(match.group(0)):]
                continue
            #handle preprocessor commands
            if line[0] in '.#':
                line = line[1:]
                tmp = re.findall(r'[^ \t]+', line)
                if tmp[0] == 'reserve':
                    value = line[8:].strip()
                    if value == '':
                        adderr('Value expected: ' + line)
                    if re.search(r'[^a-zA-Z0-9_.]' + labelre, ' ' + value):
                        adderr("Can't use labels or defines for reserves: " + \
                               value)
                        break
                    try:
                        tmp = int(eval(value))
                    except (TypeError, SyntaxError):
                        adderr('Failed to parse: ' + value)
                        break
                    if tmp > 0:
                        result[-1][0] += 'dat 0' + (tmp - 1) * ', 0'
                        wordno += tmp
                    break
                if tmp[0] == 'define':
                    if tmp[1] in labels or tmp[1] in defines:
                        adderr('Label or define already exists: ' + tmp[1])
                    else:
                        val = line[8 + len(tmp[1]):].strip()
                        if val:
                            defines[tmp[1]] = line[8 + len(tmp[1]):].strip()
                        else:
                            adderr('Value or expression expected: ' + line)
                    break
                if tmp[0] == 'include':
                    match = re.match(r'(?:\"[^\"]*\")|(?:\'[^\']*\')', \
                                     line[8:].strip())
                    if not match:
                        adderr('Expected string with filename: .' + line)
                        break
                    else:
                        newfile = path + match.group(0)[1:-1]
                        try:
                            nerrs, nres, nlabels, ndefs, nwno = \
                                   assemble(newfile, False)
                        except IOError as e:
                            adderr('File could not be accessed: ' + newfile)
                            break
                        result.extend(nres)
                        errors.extend(nerrs)
                        for i in nlabels:
                            if i in labels or i in defines:
                                adderr('Label or define already exists: ' + i)
                            else:
                                labels[i] = nlabels[i] + wordno
                        for i in ndefs:
                            if i in labels or i in defines:
                                adderr('Label or define already exists: ' + i)
                            else:
                                defines[i] = ndefs[i]
                        wordno += nwno
                        break
                if tmp[0] != 'dat':
                    adderr('Unidentified preprocessor command: .' + line)
                    break
            #handle dats
            match = re.match(r'\.?dat[ \t]+', line)
            if match:
                line = 'dat ' + line[len(match.group(0)):]
                wordno += line.count(',') + 1
                result[-1][0] += line
                break
            line = addns(line, namespace)
            #handle opcodes
            if line.lower() == 'sti':
                result[-1][0] += 'sti a, a'
                wordno += 1
                break
            if line.lower() == 'std':
                result[-1][0] += 'std a, a'
                wordno += 1
                break
            if line.lower() == 'rfi':
                result[-1][0] += 'rfi a'
                break
            op = line[:3].lower()
            if op in opcodes and line[3:4] in ' \t':
                if opcodes[op] < 32:
                    #basic opcode
                    if line.count(',') > 1:
                        adderr('Expected two arguments: ' + line)
                        break
                    comma = line.find(',')
                    if comma == -1:
                        adderr('Expected two arguments: ' + line)
                        break
                    arg1 = line[4:comma].strip().lower()
                    arg2 = line[comma + 1:].strip().lower()
                    if arg1 == '' or arg2 == '':
                        adderr('Expected two arguments: ' + line)
                        break
                    wordno += 1 + arglen(arg1) + arglen(arg2, True)
                    result[-1][0] += op + ' ' + arg1 + ', ' + arg2
                    break
                else:
                    #advanced opcode
                    if line.count(',') > 0:
                        adderr('Expected only one argument: ' + line)
                        break
                    arg1 = line[4:].strip()
                    if arg1 == '':
                        adderr('Expected an argument: ' + line)
                        break
                    wordno += 1 + arglen(arg1, True)
                    result[-1][0] += op + ' ' + arg1
                    break
                
            #cannot identify line
            adderr('Could not be understood: ' + line)
            line = ''
    #RESOLVE EXPRESSIONS
    #unresolvable expressions are left like they were found
    result = [i for i in result if i]
    
    if resolve:
        binary = []
        for line, file, lineno in result:
            op = line[:3].lower()
            if op == 'dat':
                args = line[4:].split(',')
                for arg in args:
                    p = parse(arg)
                    if p == '#':
                        binary.append(0)
                    else:
                        binary.append(int(p))
                continue
            if op in opcodes:
                if opcodes[op] < 32:
                    #basic opcode
                    cl = line.find(',')
                    arg1 = line[4:cl].strip().lower()    #b
                    arg2 = line[cl + 1:].strip().lower() #a
                    b, a = argval(arg1), argval(arg2, True)
                    #TODO: check for failures (a or b is (-1,))
                    binary.append(opcodes[op] + 32 * b[0] + 1024 * a[0])
                    if len(a) > 1:
                        binary.append(a[1])
                    if len(b) > 1:
                        binary.append(b[1])
                else:
                    #advanced opcode
                    arg = line[4:].strip().lower()
                    a = argval(arg, True)
                    #TODO: check for failures (a or b is (-1,))
                    binary.append(opcodes[op] + 1024 * a[0])
                    if len(a) > 1:
                        binary.append(a[1])
        return(errors, binary, result, labels, defines, wordno)
    return (errors, result, labels, defines, wordno)

def addns(l, ns):
    def promote(m):
        return m.group(1) + ns + m.group(2)
    n = 1
    l = ' ' + l + ' '
    while n != 0 and ns != '':
        l, n = re.subn(r'([^a-zA-Z0-9_.:])(\.' + labelre + '[^a-zA-Z0-9_.:])', \
                       promote, l)
    return l[1:-1]

def disassemble(source, start = 0):
    r = []
    i = start - 1
    while i < len(source) - 1:
        i += 1
        o = i
        op = source[i] & 31
        b = (source[i] >> 5) & 31
        a = (source[i] >> 10) & 63
        sop = opcodes2[op]
        if sop == 'spc':
            sop = spcops[b]
            sa = values2[a]
            if 'nw' in sa:
                i += 1
                sa = sa.replace('nw', str(source[i]))
            if i >= len(source):
                r.append(format(o, '6') + ': ' + sop + ' ' + sa)
                return r
            r.append(format(o, '6') + ': ' + sop + ' ' + sa)
        else:
            sa = values2[a]
            sb = values2[b]
            if sa == 'poppush':
                sa = 'pop'
            if sb == 'poppush':
                sb = 'push'
            if 'nw' in sb:
                i += 1
                if i >= len(source):
                    r.append(format(o, '6') + ': ' + sop + ' ' + sb + ', ' + sa)
                    return r
                sb = sb.replace('nw', str(source[i]))
            if 'nw' in sa:
                i += 1
                if i >= len(source):
                    r.append(format(o, '6') + ': ' + sop + ' ' + sb + ', ' + sa)
                    return r
                sa = sa.replace('nw', str(source[i]))
            r.append(format(o, '6') + ': ' + sop + ' ' + sb + ', ' + sa)
            if i >= len(source):
                return r
        #if o < len(source) - 3:
            #r[-1] += ' '*(32-len(r[-1])) + format(source[o], '5') + ', ' + format(source[o+1], '5') + ', ' + format(source[o+2], '5')
    return r

def printdis(source, a = 0):
    for i in disassemble(source, a):
        print(i)

def tobin(l, le = True):
    r = []
    if le:
        for i in l:
            r.append(i >> 8)
            r.append(i & 255)
    else:
        for i in l:
            r.append(i & 255)
            r.append(i >> 8)
    r = bytes(r)
    return r

def frombin(b, le = True):
    b = list(b)
    r = []
    for i in range(len(b) // 2):
        r.append((b[2 * i], b[2 * i + 1]))
    if le:
        r = [a * 256 + b for a, b in r]
    else:
        r = [a * 256 + b for b, a in r]
    return r

def print2(a, b):
    for i in range(min(len(a), len(b))):
        print(format(str(a[i]), '40') + str(b[i]))

try:
    print(assemble('nonsense'))
except IOError as e:
    print('nonsense does not exist.')

errors, binary, result, labels, defines, wordlen = assemble('test/main.dasm')
binary2 = tobin(binary, False)
if errors:
    for e in errors:
        print(e)
else:
    with open('Test.bin', 'wb') as f:
        f.write(binary2)

with open('entropy.bin', 'rb') as f:
    entropy = f.read()
print(len(entropy))
entropy = frombin(entropy, False)
print(len(entropy), len(binary))
e = disassemble(entropy)
b = disassemble(binary)
print2(e, b)
