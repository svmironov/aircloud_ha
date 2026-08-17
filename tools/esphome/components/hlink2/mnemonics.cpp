
#include "mnemonics.h"

namespace esphome {
namespace hlink2 {
static const char *const TAG = "hlink2:mnemonics";

Mnemonic Mnemonic::None{
  "None",
  Mnemonic::Dest::None,
  Mnemonic::Mode::None,
};

Mnemonic Mnemonic::IDU_Buzz{ "Buzz", Mnemonic::Dest::IDU, 193449999 };
Mnemonic Mnemonic::IDU_FanS{ "FanS", Mnemonic::Dest::IDU, 193974655 };
Mnemonic Mnemonic::IDU_FanSw{ "FanSw", Mnemonic::Dest::IDU, 193974655 };
Mnemonic Mnemonic::IDU_FilS{ "FilS", Mnemonic::Dest::IDU, 193974655 };
Mnemonic Mnemonic::IDU_FltT{ "FltT", Mnemonic::Dest::IDU, 193466737 };
Mnemonic Mnemonic::IDU_HExT{ "HExT", Mnemonic::Dest::IDU, 193466737 };
Mnemonic Mnemonic::ODU_HExT{ "HExT", Mnemonic::Dest::ODU, 193466737 };
Mnemonic Mnemonic::IDU_Hr{ "Hr", Mnemonic::Dest::IDU, 193466737 };
Mnemonic Mnemonic::IDU_Mode{ "Mode", Mnemonic::Dest::IDU, 193974655 };
Mnemonic Mnemonic::IDU_Modl{ "Modl", Mnemonic::Dest::IDU, 193466737 };
Mnemonic Mnemonic::IDU_OnOf{ "OnOf", Mnemonic::Dest::IDU, 193974655 };
Mnemonic Mnemonic::IDU_Opt1{ "Opt1", Mnemonic::Dest::IDU, 193974655 };
Mnemonic Mnemonic::IDU_Opt2{ "Opt2", Mnemonic::Dest::IDU, 193974655 };
Mnemonic Mnemonic::IDU_Opt3{ "Opt3", Mnemonic::Dest::IDU, 193974655 };
Mnemonic Mnemonic::IDU_Opt4{ "Opt4", Mnemonic::Dest::IDU, 193974655 };
Mnemonic Mnemonic::IDU_Pwd{ "Pwd", Mnemonic::Dest::IDU, 193449999 };
Mnemonic Mnemonic::IDU_PwrC{ "PwrC", Mnemonic::Dest::IDU, 193466737 };
Mnemonic Mnemonic::IDU_PwrI{ "PwrI", Mnemonic::Dest::IDU, 193466737 };
Mnemonic Mnemonic::IDU_Rair{ "Rair", Mnemonic::Dest::IDU, 193466737 };
Mnemonic Mnemonic::IDU_RlMd{ "RlMd", Mnemonic::Dest::IDU, 193466737 };
Mnemonic Mnemonic::IDU_SetT{ "SetT", Mnemonic::Dest::IDU, 193974655 };
Mnemonic Mnemonic::IDU_SSID{ "SSID", Mnemonic::Dest::IDU, 193449999 };
Mnemonic Mnemonic::ODU_Ta{ "Ta", Mnemonic::Dest::ODU, 193466737 };
Mnemonic Mnemonic::IDU_Time{ "Time", Mnemonic::Dest::IDU, 193466737 };
Mnemonic Mnemonic::IDU_Tr{ "Tr", Mnemonic::Dest::IDU, 193466737 };
Mnemonic Mnemonic::IDU_WSt{ "WSt", Mnemonic::Dest::IDU, 193974655 };
Mnemonic Mnemonic::IDU_WtmS{ "WtmS", Mnemonic::Dest::IDU, 193974655 };


Mnemonic Mnemonic::custom_Mnemonics[]{
  Mnemonic{ "TYPE", Mnemonic::Dest::IDU, 193449999 },
  Mnemonic{ "TPID", Mnemonic::Dest::IDU, 193466737 },
  Mnemonic{ "PwrZ", Mnemonic::Dest::IDU, 193466737 },
  Mnemonic{ "SwrZ", Mnemonic::Dest::IDU, 193466737 },
  Mnemonic{ "ItW", Mnemonic::Dest::IDU, 193466737 },
  Mnemonic{ "Fota", Mnemonic::Dest::IDU, 193466737 },
  Mnemonic{ "Stat", Mnemonic::Dest::IDU, 193466737 },
  Mnemonic{ "ALM", Mnemonic::Dest::IDU, 193466737 },
  Mnemonic{ "Thmo", Mnemonic::Dest::IDU, 193466737 },
  Mnemonic{ "SetTR", Mnemonic::Dest::IDU, 193466737 },
  Mnemonic{ "Hs", Mnemonic::Dest::IDU, 193466737 },
  Mnemonic{ "FanHD", Mnemonic::Dest::IDU, 193466737 },
  Mnemonic{ "CapC", Mnemonic::Dest::IDU, 193466737 },
  Mnemonic{ "MdDtl", Mnemonic::Dest::IDU, 193466737 },
  Mnemonic{ "Maint", Mnemonic::Dest::IDU, 193466737 },
  Mnemonic{ "Comm", Mnemonic::Dest::IDU, 193466737 },
  Mnemonic{ "PinR", Mnemonic::Dest::IDU, 193466737 },
  Mnemonic{ "Opt5", Mnemonic::Dest::IDU, 193466737 },
  Mnemonic{ "Opt6", Mnemonic::Dest::IDU, 193466737 },
  Mnemonic{ "Opt7", Mnemonic::Dest::IDU, 193466737 },
  Mnemonic{ "Opt8", Mnemonic::Dest::IDU, 193466737 },
  Mnemonic{ "Func1", Mnemonic::Dest::IDU, 193466737 },
  Mnemonic{ "Func2", Mnemonic::Dest::IDU, 193466737 },
  Mnemonic{ "Func3", Mnemonic::Dest::IDU, 193466737 },
  Mnemonic{ "Func4", Mnemonic::Dest::IDU, 193466737 },
  Mnemonic{ "Func5", Mnemonic::Dest::IDU, 193466737 },
  Mnemonic{ "Func6", Mnemonic::Dest::IDU, 193466737 },
  Mnemonic{ "Dmd", Mnemonic::Dest::IDU, 193466737 },
  Mnemonic{ "Cinfo", Mnemonic::Dest::IDU, 193466737 },
  Mnemonic{ "Info1", Mnemonic::Dest::IDU, 193466737 },
  Mnemonic{ "Info2", Mnemonic::Dest::IDU, 193466737 },
  Mnemonic{ "Info3", Mnemonic::Dest::IDU, 193466737 },
  Mnemonic{ "Info4", Mnemonic::Dest::IDU, 193466737 },
  Mnemonic{ "Info5", Mnemonic::Dest::IDU, 193466737 },
  Mnemonic{ "H1", Mnemonic::Dest::ODU, 193466737 },

};


Mnemonic* Mnemonic::from_hash(uint32_t hash) {
  switch (hash) {
    case 3299752842:return &IDU_Buzz;
    case 3299630503:return &IDU_FanS;
    case 1513624304:return &IDU_FanSw;
    case 3299622509:return &IDU_FilS;
    case 3299624823:return &IDU_FltT;
    case 3299303836:return &IDU_HExT;
    case 1729731226:return &ODU_HExT;
    case 216003207:return &IDU_Hr;
    case 3299183038:return &IDU_Mode;
    case 3299183031:return &IDU_Modl;
    case 3299383541:return &IDU_OnOf;
    case 3299359271:return &IDU_Opt1;
    case 3299359268:return &IDU_Opt2;
    case 3299359269:return &IDU_Opt3;
    case 3299359266:return &IDU_Opt4;
    case 2833130686:return &IDU_Pwd;
    case 3298998763:return &IDU_PwrC;
    case 3298998753:return &IDU_PwrI;
    case 3299199285:return &IDU_Rair;
    case 3299186890:return &IDU_RlMd;
    case 3299227595:return &IDU_SetT;
    case 3299210352:return &IDU_SSID;
    case 218505742:return &ODU_Ta;
    case 3298836328:return &IDU_Time;
    case 216002843:return &IDU_Tr;
    case 2833132685:return &IDU_WSt;
    case 3299109984:return &IDU_WtmS;
    case 3298886437:return &custom_Mnemonics[0];
    case 3298892372:return &custom_Mnemonics[1];
    case 3298998770:return &custom_Mnemonics[2];
    case 3299245841:return &custom_Mnemonics[3];
    case 2833139447:return &custom_Mnemonics[4];
    case 3299619393:return &custom_Mnemonics[5];
    case 3299245391:return &custom_Mnemonics[6];
    case 2833147357:return &custom_Mnemonics[7];
    case 3298835107:return &custom_Mnemonics[8];
    case 1500328313:return &custom_Mnemonics[9];
    case 216003206:return &custom_Mnemonics[10];
    case 1513624952:return &custom_Mnemonics[11];
    case 3299805772:return &custom_Mnemonics[12];
    case 1498425192:return &custom_Mnemonics[13];
    case 1498229346:return &custom_Mnemonics[14];
    case 3299795473:return &custom_Mnemonics[15];
    case 3298979832:return &custom_Mnemonics[16];
    case 3299359267:return &custom_Mnemonics[17];
    case 3299359264:return &custom_Mnemonics[18];
    case 3299359265:return &custom_Mnemonics[19];
    case 3299359278:return &custom_Mnemonics[20];
    case 1513183698:return &custom_Mnemonics[21];
    case 1513183697:return &custom_Mnemonics[22];
    case 1513183696:return &custom_Mnemonics[23];
    case 1513183703:return &custom_Mnemonics[24];
    case 1513183702:return &custom_Mnemonics[25];
    case 1513183701:return &custom_Mnemonics[26];
    case 2833143280:return &custom_Mnemonics[27];
    case 1519137392:return &custom_Mnemonics[28];
    case 1503079394:return &custom_Mnemonics[29];
    case 1503079393:return &custom_Mnemonics[30];
    case 1503079392:return &custom_Mnemonics[31];
    case 1503079399:return &custom_Mnemonics[32];
    case 1503079398:return &custom_Mnemonics[33];
    case 218505922:return &custom_Mnemonics[34];
    default:return &Mnemonic::None;
  }
}

} // hlink2
} //esphome
