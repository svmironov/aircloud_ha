import enum
import os
import pathlib
import json
import re
from functools import reduce

MNEMONIC_JSON = pathlib.Path(__file__).with_name('mnemonics.json')
MNEMONIC_CPP = pathlib.Path(__file__).with_name('mnemonics.cpp')

MNEMONICS_LIST = [
    "4Way", "A11", "A12", "ALM", "Buzz", "CapC", "CFq1", "Comm", "CycS", "EVD", "FANCD1",
   "FanHD", "FanO", "FanS", "FANS1", "FanSw", "FanVD", "FilS", "FltT", "Fota", "Func1",
   "Func2", "H1", "H2", "HExT", "HI1", "Hr", "Hs", "iE", "ImOVL", "INVCD1", "INVS1",
   "IsOVL", "ItW", "Maint", "MalC", "MdDtl", "Mode", "Modl", "NeTU", "oE1", "OnOf",
   "Opt1", "Opt2", "Opt3", "Opt4", "OtUT", "PFa1", "PinR", "PrtI", "Pwd", "PwrC",
   "PwrI", "PwrZ", "Rair", "RlMd", "RmCt", "RomN", "RunI", "RunS", "RuSt", "SetT",
    "SetTR", "SSID", "Stas", "Stat", "SwrZ", "Ta", "Td", "Td1", "Tg1", "Thmo", "Time",
    "To", "TPID", "tqOVL", "Tr", "TYPE", "UJ1", "WSt", "WtmS"
 ]


MNEMONIC_CPP_SKELETON = '''
#include "mnemonics.h"

namespace esphome {{
namespace hlink2 {{
static const char *const TAG = "hlink2:mnemonics";

Mnemonic Mnemonic::None{{
  "None",
  Mnemonic::Dest::None,
  Mnemonic::Mode::None,
}};

{builtin_mnemonics}

Mnemonic Mnemonic::custom_Mnemonics[]{{
{custom_mnemonics}
}};


Mnemonic* Mnemonic::from_hash(uint32_t hash) {{
  switch (hash) {{
{cases}
    default:return &Mnemonic::None;
  }}
}}

}} // hlink2
}} //esphome
'''


def _hasher(s, h=5381):
    """DJB2A hash function - identical to C++ function"""
    for c in s:
        h = ((h << 5) + h) ^ ord(c)
    return h & 0xFFFFFFFF


class ClassProperty:
    def __init__(self, func):
        self.func = func

    def __get__(self, instance, owner):
        return self.func(owner)


class Enum(enum.Enum):
    @classmethod
    def get(cls, name):
        if name in cls.__members__:
            return getattr(cls, name)
        else:
            return cls(name)

    @classmethod
    def __iter__(cls):
        # Iterate over all members except the one named 'NONE'
        return (member for member in super().__iter__() if member.name != "NONE")


class _Mnemonics(list):
    _mnemonics: '_Mnemonics[Mnemonic]' = None

    def __new__(cls, *args, **kwargs):
        if cls._mnemonics is None:
            cls._mnemonics = super().__new__(cls)
        return cls._mnemonics

    def __init__(self, *args, **kwargs):
        list.__init__(self, *args, **kwargs)
    
    def __iter__(self):
        # Iterate over all members except the one named 'NONE'
        return (mnemonic for mnemonic in super().__iter__() if mnemonic.name)

    @classmethod
    def find(cls, id=False, *, name='', dest='') -> 'Mnemonic':
        "return a mnemonic from its id if it exists, NONE otherwise"
        if id is False:
            id = f'{dest}_{name}'
        for m in cls._mnemonics:
            if m.id == id:
                return m
        return Mnemonic.NONE

    @classmethod
    def init(cls):
        if MNEMONIC_JSON.is_file(): 
            with open(MNEMONIC_JSON, 'w'):
                pass

    @classmethod
    def load(cls):
        if MNEMONIC_JSON.is_file():
            try:
                with open(MNEMONIC_JSON, 'r') as file:
                    data = json.load(file)
                    if type(data) in (tuple, list):
                        [Mnemonic.load(m) for m in data]
            except Exception as e:
                print("failed to load mnemonics from json")

    @classmethod
    def dump(cls):
        """update mnemonics set and custom header"""
        with open(MNEMONIC_JSON, 'w') as file:
            dump = [m.dump() for m in cls._mnemonics]
            json.dump(dump, file, indent=4)

    @ClassProperty
    def builtins(cls):
        return [m for m in cls._mnemonics if m.builtin is True]

    @ClassProperty
    def customs(cls):
        return [m for m in cls._mnemonics if m.builtin is False]

    def to_code(cls):
        builtin_mnemonics = ''
        custom_mnemonics = ''
        cases = {}
        
        for m in cls.builtins:
            builtin_mnemonics += f'Mnemonic Mnemonic::{m.id}{{ "{m.name}", Mnemonic::Dest::{m.dest.name}, {m.mode} }};\n'
            cases[m.hash] = m.id

        for i, m in enumerate(cls.customs):
            custom_mnemonics += f'  Mnemonic{{ "{m.name}", Mnemonic::Dest::{m.dest.name}, {m.mode} }},\n'
            cases[m.hash] = f'custom_Mnemonics[{i}]'

        cases = '\n'.join([f'    case {h}:return &{cases[h]};' for h in cases])

        with open(MNEMONIC_CPP, 'w') as file:
            file.write(MNEMONIC_CPP_SKELETON.format(
                builtin_mnemonics = builtin_mnemonics,
                custom_mnemonics = custom_mnemonics,
                cases=cases
            ))

    @classmethod
    def index(cls, mnemonic: 'Mnemonic'):
        """return mnemonic index amongst custom mnemonics of the same type"""
        if not mnemonic or mnemonic is Mnemonic.NONE:
            raise ValueError(f'unknow mnemonic')
        if mnemonic.builtin:
            raise ValueError(f'builtin mnemonic ({mnemonic})')
        return cls.customs.index(mnemonic)


Mnemonics = _Mnemonics()


class Mnemonic:
    class Dest(Enum):
        IDU = 'IDU'
        ODU = 'ODU'
        NONE = None
    
    class Mode(Enum, enum.IntFlag):
        NONE = 0
        STS = _hasher('STS')
        CMD = _hasher('CMD')

    class Type(Enum):
        INT = 'Int'
        FLOAT = 'Float'
        STR = 'Str'
        RAW = 'Raw'
        NONE = None

    NONE = None

    def __new__(cls, name: str, dest: Dest|str, mode: Mode|int, type_: Type|str, builtin: bool = True):
        if None in (name, dest, mode, type_) or len(name) == 0 :
            if cls.NONE is None:
                cls.NONE = super().__new__(cls)
            return cls.NONE
        return super().__new__(cls)
    
    def __init__(self, name: str, dest: Dest|str = None, mode: Mode|int = 0, type_: Type|str = None, builtin=True):
        self.name = name
        self.dest = Mnemonic.Dest.get(dest)
        self.mode = Mnemonic.Mode.get(mode)
        self.type = Mnemonic.Type.get(type_)
        self.builtin = builtin
    
    def __bool__(self):
        return self is not Mnemonic.NONE

    @classmethod
    def get(cls, name: str, dest: Dest|str, mode: Mode|int, type_: Type|str, builtin: bool = True) -> 'Mnemonic':
        """return a mnemonic matching the arguments, creating it if necessary"""
        
        dest = Mnemonic.Dest.get(dest)
        mode = Mnemonic.Mode.get(mode)
        type_ = Mnemonic.Type.get(type_)

        # check if mnemonic already exist
        for mnemonic in Mnemonics:
            if mnemonic.name == name and mnemonic.dest == dest:
                if mnemonic.mode not in mode:  # allow adding new modes
                    raise ValueError(f'Failed to create mnemonic {dest.name}_{name}: mode mismatch')
                if mnemonic.type != type_: pass
                #    raise ValueError(f'Failed to create mnemonic {dest.name}_{name}: type mismatch')
                if mnemonic.builtin != builtin: pass  # silently return builtin mnemonics
                    # raise ValueError(f'Failed to create mnemonic {dest.name}_{name}: builtin')
                mnemonic.mode |= mode
                return mnemonic
        
        # check hash collision
        for mnemonic in Mnemonics:
            if mnemonic.hash == cls.hasher(Mnemonic.Dest(dest).name + name):
                raise ValueError(f'Hash collision ({mnemonic.name}:{mnemonic.type}/{name}:{type_})')

        Mnemonics.append(Mnemonic(name, dest, mode, type_, builtin))
        return Mnemonics[-1]

    @property
    def id(self):
        return f'{self.dest.name}_{self.name}'

    @property
    def hash(self):
        return self.hasher(f'{self.dest.name}{self.name}')

    @staticmethod
    def hasher(s, h=5381):
        return _hasher(s, h)

    @staticmethod
    def load(data: dict[str:str]) -> 'Mnemonic':
        return Mnemonic.get(
            data['name'],
            Mnemonic.Dest(data['dest']),
            Mnemonic.Mode(data['mode']),
            Mnemonic.Type(data['type']),
            data['builtin']
        )

    def dump(self) -> dict[str:str]:
        return dict(
            name=self.name,
            dest=self.dest.value,
            mode=self.mode,
            type=self.type.value, 
            builtin=self.builtin
        )

Mnemonic.get(None, None, 0b11111111, None)