#pragma once

#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <string_view>

#include "esphome/core/log.h"
#include "main.h"
#include "tools.h"
#include "buffer.h"
#include "mnemonics.h"


namespace esphome {
namespace hlink2 {


struct Request {
  public:
    static constexpr const char TAG[] = "hlink2:request"; 
    
    Request(Mnemonic& m): mnemonic_(&m) {};
    Request(): Request(Mnemonic::None) {};

    inline Mnemonic* mnemonic() { return this->mnemonic_; }
    inline auto& request() { return this->request_; }
    inline std::string_view view() { return this->request_.view(); }
    inline const char* c_str() { 
      if constexpr (MNEMONIC_BUFFER_NULL_TERMINATED) {
        return this->request_.c_str();
      } else {
        static_assert(MNEMONIC_BUFFER_NULL_TERMINATED, "c_str is invalid if MNEMONIC_BUFFER_NULL_TERMINATED is false");
      } }

    /// return whether request value has been set
    inline bool has_request() { return this->request_.size(); }

    /// remove request value
    inline void clear_request() { 
      ESP_LOGV(TAG, "clear_request: %s", this->mnemonic_->name);
      this->request_.clear();
    }
    

    /// apply request value to mnemonic
    inline void apply_request() {
      ESP_LOGV(TAG, "apply_request: %s", this->mnemonic_->name, this->request_.c_str());
      this->mnemonic_->set_status(this->request_);
    }

    /// set request value from integer
    template<typename TYPE>
    std::enable_if_t<std::is_unsigned<TYPE>::value, bool>
    set_request(TYPE value) {
      auto result = std::to_chars(request_.data(), request_.data() + request_.capacity(), value);
      if (result.ec == std::errc()) {
        request_.resize(result.ptr - request_.data());
        return true;
      }
      request_.clear();
      return false;
    }

    /// set request value from float
    template<typename TYPE>
    std::enable_if_t<std::is_floating_point_v<TYPE>, void>
    set_request(TYPE value, uint8_t precision=MNEMONIC_FLOAT_PRECISION) { 
      size_t len = std::snprintf(request_.data(), request_.capacity(), "%.*f", precision, value);
      request_.resize(len);
    }

    /// set request from char
    void set_request(char value) {
      request_.set(value);
    }

    /// set request from string_view
    bool set_request(std::string_view value, bool raw=true) { // quotes are added if missing
      size_t len;
      if (raw || (value.size() > 1 && value.front() == '"' && value.back() == '"')) {
        return this->request_.set(value);
      } else {
        request_.set('"');
        return this->request_.append(value) && this->request_.append('"');
      }
    };

    /// set request from string
    inline bool set_request(const char *value, bool raw = false) {  // null-terminated string
      return set_request(value ? std::string_view(value) : std::string_view{}, raw);
    };

    CharBuffer<MNEMONIC_BUFFER_SIZE, MNEMONIC_BUFFER_NULL_TERMINATED> request_{};
  protected:
    Mnemonic* mnemonic_{};
};


struct Message: CallbacksHandler {
  public:
    struct Flag {
      Mnemonic::Mode mode;
      Mnemonic::Dest dest;
      const char* raw;

      static const Flag STS_IDU;
      static const Flag STS_ODU;
      static const Flag CMD_IDU;
      static const Flag None;

      inline constexpr bool match(Flag& f) const {return this->mode == f.mode && this->dest == f.dest;}
      inline constexpr bool match_mode(Mnemonic::Mode m) const {return this->mode == m;}
      inline constexpr bool match_dest(Mnemonic::Dest d) const {return this->dest == d;};
      static constexpr const Message::Flag* from_hash(uint32_t hash) {
        switch (hash){
          case hasher("STS_IDU"): return &Message::Flag::STS_IDU;
          case hasher("STS_ODU"): return &Message::Flag::STS_ODU;
          case hasher("CMD_IDU"): return &Message::Flag::CMD_IDU;
          default: return &Message::Flag::None;
        }
      }
      static constexpr const inline Flag* from_raw(std::string_view sv) {return Flag::from_hash(hasher(sv));}
      static constexpr const Message::Flag* flag(Mnemonic::Mode m, Mnemonic::Dest d) {
        switch (m) {
          case Mnemonic::Mode::STS:
            switch (d) {
              case Mnemonic::Dest::IDU: return &Message::Flag::STS_IDU;
              case Mnemonic::Dest::ODU: return &Message::Flag::STS_ODU;
              case Mnemonic::Dest::None: return &Message::Flag::None;
            }
          case Mnemonic::Mode::CMD:
            switch (d) {
              case Mnemonic::Dest::IDU: return &Message::Flag::CMD_IDU;
              case Mnemonic::Dest::ODU:
              case Mnemonic::Dest::None:
                return &Message::Flag::None;
            }
          default:
            return &Message::Flag::None;
        }
      } 
    };
    
    enum class QoS: uint8_t {
      QOS_LOW = 1,
      QOS_MEDIUM = 2,
      QOS_HIGH = 3
    };

    static constexpr const char* QoSToString(QoS qos) { 
      switch (qos) {
        case QoS::QOS_LOW: return "QOS_LOW";
        case QoS::QOS_MEDIUM: return "QOS_MEDIUM";
        case QoS::QOS_HIGH: return "QOS_HIGH";
        default: return "None";
      }
    }
    
    enum class State: uint8_t {
      INITIALIZED,
      SCHEDULED,
      FORMATTED,
      SENT,
      RECEIVED,
      PARSED,
      PROCESSED,
      EXPIRED,
      INVALID
    };
  
    static constexpr const char* StateName[] = {
      "INITIALIZED", "SCHEDULED", "FORMATTED", "SENT",
      "RECEIVED", "PARSED", "PROCESSED", "EXPIRED", "INVALID"
    };

    enum class Response: uint8_t {
      VALID = 0,    // all supplied mnemonics are valid
      INVALID = 1,  // all supplied mnemonics are invalid
      EMPTY = 2,    // no requested mnemonic is available
      PARTIAL = 3,  // some supplied mnemonics are invalid
      NONE = 4
    };

    enum class ResponsePolicy: uint8_t {
      VALID_OR_PARTIAL,
      ANY_CHECKSUMMED,
      TRACK_CHECKSUMMED,
    };

    Message(const Message&) = delete;
    Message& operator=(const Message&) = delete;
    Message(Message&&) noexcept = default;
    Message& operator=(Message&&) noexcept = default;

  template<typename TYPE = QoS>
  Message(
    const Message::Flag &flag = Flag::None, TYPE&& qos = QoS::QOS_LOW, uint32_t timer = 0, bool ephemeral = false
  ): flag(&flag), qos(static_cast<QoS>(std::forward<TYPE>(qos))), interval_(timer), ephemeral_(ephemeral) {};

  template<typename TYPE = QoS>
  Message(
    std::string_view flag, TYPE&& qos = QoS::QOS_LOW, uint32_t timer = 0, bool ephemeral = false
  ): Message(*Flag::from_raw(flag), qos, timer, ephemeral) {};

  const Flag* flag;
  QoS qos;
  std::optional<Response> response;

  RingVector<Request, MESSAGE_MNEMONICS_CAPACITY> requests_;
  RingVector<Mnemonic*, MESSAGE_MNEMONICS_CAPACITY> response_mnemonics;

  inline RingVector<Request, MESSAGE_MNEMONICS_CAPACITY>& requests() { return this->requests_; }

  inline CyclicTimer& interval() { return this->interval_; }

  inline bool ephemeral() { return this->ephemeral_; }
  inline bool persistent() {return !this->ephemeral_; }
  inline void set_response_policy(ResponsePolicy policy) { this->response_policy_ = policy; }
  inline bool accepts_any_checksummed_response() const {
    return this->response_policy_ == ResponsePolicy::ANY_CHECKSUMMED;
  }
  inline bool tracks_checksummed_response() const {
    return this->response_policy_ == ResponsePolicy::TRACK_CHECKSUMMED;
  }

  /// return message state, handling expiration conditions
  State state ();
  inline State raw_state() const { return this->state_.value; }
  inline void start_transaction_timeout() {
    if (!this->transaction_started_) {
      this->state_.timer.restart();
      this->transaction_started_ = true;
    }
  }

  /// set message state
  Message::State set_state(const Message::State &state);


  /// return request mnmenics count
  inline size_t size() const { return this->requests_.size(); };
  inline bool empty() const { return !this->requests_.size(); }

  // MNEMONICS

  /// add a new mnemonic to the message (check if already present)
  Request* add(Mnemonic& m);
  

  /// return whether the message has a mnemonic
  bool has(Mnemonic& m);

  // BUFFERS
  IOBuffer* request_buffer() {return &this->request_buffer_;}

  // ACTIONS

  /// initialize message
  void initialize();
  void initialize(uint32_t delay);

  inline void reinitialize() { if (this->persistent()) initialize(); }

  /// schedule message, setting attempts and timeout
  void schedule();

  /// format message in the internal buffer
  Message::State format();

  /// parse message from shared buffer
  Message::State parse(IOBuffer &buffer);

  Request* get_request(Mnemonic&);
  Request* get_request(size_t);

  /// return whether message has requests values
  bool has_requests();

  /// clear commands value from request mnemonics
  void clear_requests();


  /// apply commands values to mnemonics, populating response_mnemonics
  void apply_requests();



  /// return message config
  std::string config()  {
    constexpr size_t BUFFER_SIZE = 12 + 9 + 16 + MESSAGE_MNEMONICS_CAPACITY * (MNEMONIC_NAME_SIZE.max + 1) + 2;
    static_assert(BUFFER_SIZE < 256, "config string too long");
    char buffer[BUFFER_SIZE];
    
    switch (this->flag->mode) {
      case Mnemonic::Mode::STS:
        snprintf(buffer, BUFFER_SIZE, "@%p: %s %s %zums [ ", this, this->flag->raw, QoSToString(this->qos), this->interval_.delay());
        break;
      case Mnemonic::Mode::CMD:
        snprintf(buffer, BUFFER_SIZE, "@%p: %s %s [ ", this, this->flag->raw, QoSToString(this->qos));
        break;
      default:
        return std::string("invalid message");
    }

    for (size_t i = 0; i < this->size(); ++i) {
      strlcat(buffer, this->requests_[i].mnemonic()->name, BUFFER_SIZE);
      strlcat(buffer, " ", BUFFER_SIZE);
    }
    strlcat(buffer, "]", BUFFER_SIZE);
    return std::string(buffer);
  }

  protected:
    /// Message status, which may depends on a timer or an attemps counter
    struct {
      State value{State::INITIALIZED};
      CyclicTimer timer{MESSAGE_UPDATE_TIMEOUT};
      uint8_t attempts{0};
    } state_;

    /// TX buffer
    IOBuffer request_buffer_{MESSAGE_HEAD};

    /// update interval
    CyclicTimer interval_;

    /// ephemeral/persistant status
    bool ephemeral_{false};
    bool transaction_started_{false};

    /// Stock RAC registration advances after any framed/checksummed reply,
    /// regardless of Res. Normal climate/status messages keep strict semantics.
    ResponsePolicy response_policy_{ResponsePolicy::VALID_OR_PARTIAL};
};


constexpr Message::Flag Message::Flag::STS_IDU{Mnemonic::Mode::STS, Mnemonic::Dest::IDU, "STS_IDU"};
constexpr Message::Flag Message::Flag::STS_ODU{Mnemonic::Mode::STS, Mnemonic::Dest::ODU, "STS_ODU"};
constexpr Message::Flag Message::Flag::CMD_IDU{Mnemonic::Mode::CMD, Mnemonic::Dest::IDU, "CMD_IDU"};
constexpr Message::Flag Message::Flag::None{Mnemonic::Mode::None, Mnemonic::Dest::None,""};


} // hlink2
} //esphome
