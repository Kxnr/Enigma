import numpy as np
import re
from collections.abc import Iterable

HISTORICAL_ROTORS = {   'I':    ('EKMFLGDQVZNTOWYHXUSPAIBRCJ','Q'), 
                        'II':   ('AJDKSIRUXBLHWTMCQGZNPYFVOE','E'),
                        'III':  ('BDFHJLCPRTXVZNYEIWGAKMUSQO','V'),
                        'IV':   ('ESOVPZJAYQUIRHXLNFTGKDCMWB','J'),
                        'V':    ('VZBRGITYUPSDNHLXAWMJQOFECK','Z'),
                        'VI':   ('JPGVOUMFYQBENHZRDKASXLICTW','ZM'),
                        'VII':  ('NZJHGRCXMYSWBOUFAIVLPEKQDT','ZM'),
                        'VIII': ('FKQHTLXOCBJSPDZRAMEWNIUYGV','ZM'),
                        'BETA': ('LEYJVCNIXWPBQMDRTAKZGFUHOS',None),
                        'GAMMA':('FSOKANUERHMBTIYCWLQPZXVGJD',None),
                        'A':    ('EJMZALYXVBWFCRQUONTSPIKHGD',None),
                        'B':    ('YRUHQSLDPXNGOKMIEBFZCWVJAT',None),
                        'C':    ('FVPJIAOYEDRZXWGCTKUQSBNMHL',None),
                        'BT': ('ENKQAUYWJICOPBLMDXZVFTHRGS',None)}

def helper(x):
    assert isinstance(x, str)
    assert len(x) == 1
    x = x.lower()
    x = ord(x) - 97

    assert x >= 0 and x <=25

    return x

class Rotor(object):
    def __init__(self, cipher=None, notches='A', step=True):
        if cipher is None:
            self.map = np.random.choice(range(26), 26, replace=False)
        else:
            self.setMap(cipher)

        self.setNotches(notches)
        
        self.step = step

        # set by key or machine setup
        self.index = 0
        self.ring = 0

    def encode(self, value):
        if value < 0 or value > 25:
            raise Exception("invalid character")
        
        ind = (value + self.index) % 26
        return (self.map[ind] - self.index + self.ring) % 26
    
    def decode(self, value):
        if value < 0 or value > 25:
            raise Exception("invalid character")
        ind = (value + self.index - self.ring) % 26
        return (np.asscalar(np.where(self.map == ind)[0]) - self.index) % 26

    def turnover(self, override=False):
        if self.step or override:
            self.index += 1
            self.index = self.index % 26

            for i in range(len(self.notches)):
                self.notches[i] = (self.notches[i] - 1) % 26

    def setMap(self, charList):
        if isinstance(charList, str):
            assert len(charList) == 26
            charList = [helper(c) for c in charList]
            self.map = np.array(charList)

        elif isinstance(charList, Iterable):
            assert np.array_equal(sorted(charList), np.array(range(26)))
            self.map = np.array(charList)
    
    def setNotches(self, inds):
        if isinstance(inds, str):
            self.notches = [helper(c) for c in inds]
        elif not inds is None:
            if min(inds) < 0 or max(inds) > 25:
                raise Exception("invalid notch position")
            self.notches = inds
        elif inds is None:
            self.notches = []
        else:
            raise Exception("invalid notches config")

    def setIndex(self, ind):
        if ind < 0 or ind > 25:
            raise Exception("invalid index")

        while self.index != ind:
            self.turnover(override=True)
 
    def setRing(self, ind):
        if ind < 0 or ind > 25:
            raise Exception("invalid index")
        #self.reset()
        self.map = np.array([(self.map[(i-ind) % 26]) % 26 for i in range(len(self.map))], dtype=int)
        self.ring = ind

    def reset(self):
        self.map = np.array([(c-self.ring)%26 for c in self.map], dtype=int)
        self.ring = 0

    def getKey(self):
        ind = chr(self.index + 97)
        notches = ''.join([chr(c + 97) for c in self.notches])

        return ind+notches

class Reflector(Rotor):
    def __init__(self, step=False):
        temp = np.random.choice(range(26), (13, 2), replace=False)

        self.map = np.zeros(26, dtype=int)
        for tup in temp:
            self.map[tup[0]] = tup[1]
            self.map[tup[1]] = tup[0]
        
        self.index = 0
        self.ring = 0
        self.notches = []
        
        self.step = step

    def getKey(self):
        return chr(self.index + 97)

class EntryRotor(Rotor):
    # same as others, except is has to map characters to numbers and vice versa
    def __init__(self, step=False):
        super().__init__(step=step)

    def encodeLetter(self, value):
        if not isinstance(value, str) \
            or not value.isalpha() \
            or len(value) > 1:
            raise Exception("entry must be a single character (a-z)")

        value = ord(value) - 97
        return super().encode(value)

    def decodeLetter(self, value):
        # super decode takes care of checking valid value
        value = super().decode(value)
        return chr(value+97) # move to appropriate ASCII range

class Plugboard(object):
    def __init__(self, connections=1):
        self.setPlugs(connections)

    def encodeLetter(self, value):
        if not isinstance(value, str) \
            or not value.isalpha() \
            or len(value) > 1:
            raise Exception("entry must be a single character (a-z)")

        value = ord(value) - 97

        if value < 0 or value > 25:
            raise Exception("invalid character")
        
        return self.map[value]

    def decodeLetter(self, value):
        if value < 0 or value > 25:
            raise Exception("invalid character")

        value = self.map[value]
        return chr(value+97)

    def setPlugs(self, connections):
        self.map = list(range(26))

        if isinstance(connections, str):
            connections = connections.lower().split()
            if len(connections) > 13:
                raise Exception("invalid plugboard config")
            for each in connections:
                if len(each) != 2:
                    raise Exception("invalid plugboard config")
                self.map[helper(each[0])] = helper(each[1])
                self.map[helper(each[1])] = helper(each[0])

        elif isinstance(connections, Iterable):
            if len(connections) > 13:
                raise Exception("invalid plugboard config")
            for each in connections:
                if len(each) != 2:
                    raise Exception("invalid plugboard config")
                self.map[each[0]] = each[1]
                self.map[each[1]] = each[0] 

        elif isinstance(connections, int):
            # fail if more than 13 connections
            if connections > 13:
                raise Exception("invalid plugboard config")

            temp = np.random.choice(range(26), (connections, 2), replace=False)
            
            for tup in temp:
                self.map[tup[0]] = tup[1]
                self.map[tup[1]] = tup[0]

        else:
            raise Exception("invalid plugboard config")

class Machine(object):
    # handles machine level behavior, such as double stepping
    def __init__(self, rotorCount=4, plugboard=0, rotorSeed=0):
        assert rotorCount > 0

        np.random.seed(rotorSeed) 
        # rotors can be directly set with configuration methods

        self.rotorCount = rotorCount
        
        self.rotors = [Rotor() for i in range(rotorCount)]

        self.entry = EntryRotor()
        self.reflector = Reflector()

        # catches errors in plugs
        self.plugboard = Plugboard(plugboard)

        self.allowedChars = re.compile('[^a-z]')

        self.key = ' '.join([r.getKey() for r in self.rotors])

        self.refPos = self.reflector.getKey()

    def advanceRotors(self):
        step = [0]*(self.rotorCount+1)

        notches = []
        for r in reversed(self.rotors):
            notches.append(r.notches)
        notches.append(self.reflector)

        for i in range(len(step)):
            if i == 0:
                step[i] += 1

            # covers double and single stepping
            elif 0 in notches[i-1]:
                step[i] += 1
                step[i-1] += 1          

        for i, each in enumerate(step[:-1]):
            if each:
                self.rotors[self.rotorCount-1-i].turnover()
        
        # TODO: needs step protection, rfelector turnover broken
        
        if step[-1]:
            self.reflector.turnover()

    def encodeString(self, string, key=None):
        if not key is None:
            self.configureMachine(key)
        else:
            self.configureMachine(self.key)

        # clean up input, just in case
        string = string.lower()
        string = self.allowedChars.sub('', string)

        out = ''
        for c in string:
            self.advanceRotors()

            val = c
            
            val = self.plugboard.encodeLetter(val)

            val = self.entry.encode(val)
            for r in reversed(self.rotors):
                val = r.encode(val)

            val = self.reflector.encode(val)

            for r in self.rotors:
                val = r.decode(val)
            
            val = self.entry.decode(val)

            val = self.plugboard.decodeLetter(val)

            out += val

        return out
    
    def configureMachine(self, key=None, ring=None, refPos=None):
        # key: <rotor ind><notch positions> <>...

        if not key is None:
            assert isinstance(key, str)
            if len(key) != self.rotorCount:
                raise Exception("invalid key")

            for i, c in enumerate(key):
                self.rotors[i].setIndex(helper(c))
                self.key = key
        
        if not ring is None:
            assert isinstance(ring, str)
            if len(ring) != self.rotorCount:
                raise Exception("invalid ring setup")

            for i,c in enumerate(ring):
                self.rotors[i].setRing(helper(c))

        if not refPos is None:  
            self.reflector.setIndex(helper(refPos))
            self.refPos = refPos

    def setRotor(self, num, cipher, step=True):
        if num > self.rotorCount:
            raise Exception("invalid rotor")
        
        self.rotors[num-1].setMap(cipher)
        self.rotors[num-1].step = step
    
    def setPlugs(self, plugs):
        self.plugboard.setPlugs(plugs)

    def reset(self):
        self.configureMachine(self.key, self.refPos)

if __name__ == '__main__':
    enigma = Machine(rotorCount=4)
    
    '''
    key = 'akio'

    s = input("type what you would like to encode: ")
    coded = enigma.encodeString(s, key=key)
    decoded = enigma.encodeString(coded, key=key)

    print()
    print("###### Message ######")
    print(s)
    print()

    print("###### Coded ######")
    print(coded)
    print()

    print("###### Decoded ######")
    print(decoded)
    '''

    '''
    # https://enigma.hoerenberg.com/index.php?cat=M4%20Project%202006&page=Rasch%20Message

    plugs = 'BQ CR DI EJ KW MT OS PX UZ GH'
    ring = 'ZZDG'
    key = 'NAQL'
    rotors = [HISTORICAL_ROTORS['BETA'], HISTORICAL_ROTORS['VI'], HISTORICAL_ROTORS['I'], HISTORICAL_ROTORS['III']]
    rotors = [Rotor(*r) for r in rotors]
    reflector = HISTORICAL_ROTORS['BT']

    enigma.reflector.setMap(reflector[0])
    enigma.key = key
    enigma.setPlugs(plugs)
    enigma.entry.setMap(range(26))

    enigma.rotors = rotors
    enigma.rotors[0].step = False
    enigma.configureMachine(ring=ring)

    message = 'HCEYZTCSOPUPPZDICQRDLWXXFACTTJMBRDVCJJMMZRPYIKHZAWGLYXWTMJPQUEFSZBOTVRLALZXWVXTSLFFFAUDQFBWRRYAPSBOWJMKLDUYUPFUQDOWVHAHCDWAUARSWTKOFVOYFPUFHVZFDGGPOOVGRMBPXXZCANKMONFHXPCKHJZBUMXJWXKAUODXZUCVCXPFT'

    dec = enigma.encodeString(message, key)
    actual  ='BOOTKLARXBEIJSCHNOORBETWAZWOSIBENXNOVXSECHSNULCBMXPROVIANTBISZWONULXDEZXBENOETIGEGLMESERYNOCHVIEFKLHRXSTEHEMARQUBRUNOBRUNFZWOFUHFXLAGWWIEJKCHAEFERJXNNTWWWFUNFYEINSFUNFMBSTEIGENDYGUTESIWXDVVVJRASCH'.lower()

    assert dec == actual
    '''

    '''
    ring = 'DDD'
    key = 'AAA'
    rotors = [HISTORICAL_ROTORS['I'], HISTORICAL_ROTORS['II'], HISTORICAL_ROTORS['III']]
    rotors = [Rotor(*r) for r in rotors]
    reflector = HISTORICAL_ROTORS['B']

    enigma.reflector.setMap(reflector[0])
    enigma.key = key
    enigma.setPlugs(0)
    enigma.entry.setMap(range(26))

    enigma.rotors = rotors
    enigma.configureMachine(ring=ring)
    print(enigma.encodeString('AAAAA', key))
    '''