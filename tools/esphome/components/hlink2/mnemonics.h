#pragma once

#include <charconv>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <string_view>
#include <type_traits>

#include "main.h"
#include "tools.h"

namespace esphome {
namespace hlink2 {

// avoid static_cast for enum class
template<typename TYPE>
typename std::enable_if_t<std::is_enum_v<TYPE>, TYPE>
operator&(TYPE Lhs, TYPE Rhs) {
  return static_cast<TYPE>(
    static_cast<std::underlying_type_t<TYPE>>(Lhs) &
    static_cast<std::underlying_type_t<TYPE>>(Rhs)
  );
}

struct Mnemonic: CallbacksHandler {
public:
  static constexpr const char TAG[] = "hlink2:mnemonic";
  
  enum class Dest: uint32_t {
    None = 0,
    IDU = hasher("IDU"),
    ODU = hasher("ODU"),
  };

  static constexpr const char* DestToString(Dest d) { 
    switch (d) {
      case Dest::IDU: return "IDU";
      case Dest::ODU: return "ODU";
      default: return "None";
    }
  }

  enum class Mode: uint32_t {
    None = 0,
    STS = hasher("STS"),
    CMD = hasher("CMD"),
  };

  static constexpr const char* ModeToString(Dest m) { 
    switch (m) {
      case Dest::IDU: return "STS";
      case Dest::ODU: return "CMD";
      default: return "None";
    }
  }

private:
    CharBuffer<MNEMONIC_BUFFER_SIZE, MNEMONIC_BUFFER_NULL_TERMINATED> status_{};
    Mode mode_{0};

public:
  template<typename MODE_TYPE>
  Mnemonic(const char* n, const Dest d, const MODE_TYPE m = Mode::None): 
    name(n), dest(d), mode_(static_cast<Mode>(m)){};
  
  const char* name;
  const Dest dest;

  std::string_view status() {return this->status_.view();};

  static Mnemonic IDU_Buzz;
  static Mnemonic IDU_FanS;
  static Mnemonic IDU_FanSw;
  static Mnemonic IDU_FilS;
  static Mnemonic IDU_FltT;
  static Mnemonic IDU_HExT;
  static Mnemonic ODU_HExT;
  static Mnemonic IDU_Hr;
  static Mnemonic IDU_Mode;
  static Mnemonic IDU_Modl;
  static Mnemonic IDU_OnOf;
  static Mnemonic IDU_Opt1;
  static Mnemonic IDU_Opt2;
  static Mnemonic IDU_Opt3;
  static Mnemonic IDU_Opt4;
  static Mnemonic IDU_Pwd;
  static Mnemonic IDU_PwrC;
  static Mnemonic IDU_PwrI;
  static Mnemonic IDU_Rair;
  static Mnemonic IDU_RlMd;
  static Mnemonic IDU_RmCt;
  static Mnemonic IDU_SetT;
  static Mnemonic IDU_SSID;
  static Mnemonic ODU_Ta;
  static Mnemonic IDU_Time;
  static Mnemonic IDU_Tr;
  static Mnemonic IDU_WSt;
  static Mnemonic IDU_WtmS;
  static Mnemonic None;
  static Mnemonic custom_Mnemonics[];

  /// return a mnemonic from its hash (ie: hasher("<DEST>_<NAME>"))
  static Mnemonic* from_hash(uint32_t hash);

  /// return a mnemonic from its name hash, given its DEST
  static inline Mnemonic* from_hash(std::string_view sv, const Dest dest) {
    return from_hash(hasher(sv, static_cast<uint32_t>(dest)));
  }

  /// return mnemonic mode
  inline Mnemonic::Mode& mode() {return this->mode_;};

  /// return whether the mnemonic handles the supplied mode
  inline bool match_mode(Mode m) {
    using TYPE = std::underlying_type_t<Mnemonic::Mode>;
    return (static_cast<TYPE>(this->mode_) & static_cast<TYPE>(m)) == static_cast<TYPE>(m);
  };

  /// return mnemonic capacity (ie. buffer length)
  inline size_t capacity() { return this->status_.capacity(); }

  /* ------- STATUS -------- */
  /// set mnemonic status
  void set_status(std::string_view sv) {
    this->status_.set(sv);
  }

  void set_status(uint8_t c) {
    this->status_.set(c); 
  }

  template<typename TYPE>
  TYPE get_status(TYPE default_value = TYPE{}) {
    if (status_.empty()) return default_value;

    if constexpr (std::is_same_v<TYPE, bool>) {
      return status_[0] != '0';
    }

    if constexpr (std::is_same_v<TYPE, uint8_t> || std::is_same_v<TYPE, uint16_t> || std::is_same_v<TYPE, uint32_t>) {
      TYPE value;
      auto result = std::from_chars(status_.data(), status_.data() + status_.size(), value);
      if (result.ec == std::errc()) return value;
    }
    else if constexpr (std::is_same_v<TYPE, float>) {
        char* endptr;
        float value = strtof(status_.data(), &endptr);
        if (endptr > status_.data()) return value;
    }
    else if constexpr (std::is_same_v<TYPE, char>) {
      return status_.front();
    }
    else if constexpr (std::is_same_v<TYPE, std::string_view>) {
        if (status_.size() > 2 && status_.front() == '"' && status_.back() == '"') {
            return status_.substr(1, status_.size()-2);
        }
        return status();
    }
    else if constexpr (std::is_same_v<TYPE, char*>) {
        return status_;
    }
    return default_value;
  }
};

constexpr Mnemonic::Mode operator|(Mnemonic::Mode a, Mnemonic::Mode b) noexcept {
  using TYPE = std::underlying_type_t<Mnemonic::Mode>;
  return static_cast<Mnemonic::Mode>(static_cast<TYPE>(a) | static_cast<TYPE>(b));
};

} // hlink2
} //esphome
